import os
import sys
import time
import pickle
import base64
import logging
import tempfile
from datetime import datetime, timezone, timedelta

import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events.readonly',
    'https://www.googleapis.com/auth/meetings.space.settings',
    'https://www.googleapis.com/auth/meetings.space.readonly',
]


def get_credentials():
    creds = None

    token_b64 = os.environ.get('OAUTH_TOKEN_BASE64')
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    elif os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)

    if not creds or not creds.valid:
        secrets_b64 = os.environ.get('OAUTH_CLIENT_SECRETS_BASE64')
        if secrets_b64:
            secrets_data = base64.b64decode(secrets_b64).decode('utf-8')
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(secrets_data)
                secrets_file = f.name
        else:
            secrets_file = 'credentials.json'

        flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
        creds = flow.run_local_server(port=0)
        _save_token(creds)

    return creds


def _save_token(creds):
    with open('token.pickle', 'wb') as f:
        pickle.dump(creds, f)


def get_calendar_events(creds, email):
    now = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()

    url = f'https://www.googleapis.com/calendar/v3/calendars/{email}/events'
    headers = {'Authorization': f'Bearer {creds.token}'}
    params = {
        'timeMin': now,
        'timeMax': end,
        'singleEvents': True,
        'orderBy': 'startTime',
        'maxResults': 250,
    }

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get('items', [])


def extract_meet_code(event):
    conf = event.get('conferenceData', {})
    solution = conf.get('conferenceSolution', {})

    if solution.get('key', {}).get('type') != 'hangoutsMeet':
        return None

    for ep in conf.get('entryPoints', []):
        if ep.get('entryPointType') == 'video':
            uri = ep.get('uri', '')
            code = uri.split('/')[-1].split('?')[0]
            if code:
                return code
    return None


def resolve_space_name(creds, meeting_code):
    url = f'https://meet.googleapis.com/v2/spaces/{meeting_code}'
    headers = {'Authorization': f'Bearer {creds.token}'}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get('name')


def enable_auto_recording(creds, space_name):
    url = f'https://meet.googleapis.com/v2/{space_name}'
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-Type': 'application/json',
    }
    params = {'updateMask': 'config.artifactConfig.recordingConfig.autoRecordingGeneration'}
    body = {'config': {'artifactConfig': {'recordingConfig': {'autoRecordingGeneration': 'ON'}}}}

    resp = requests.patch(url, headers=headers, params=params, json=body)
    resp.raise_for_status()
    return resp.json()


def already_processed(supabase, meeting_code, user_email):
    result = supabase.table('gravacoes_meet').select('id').eq(
        'meeting_code', meeting_code
    ).eq('user_email', user_email).eq('status', 'sucesso').execute()
    return len(result.data) > 0


def register_in_supabase(supabase, data):
    supabase.table('gravacoes_meet').upsert(data, on_conflict='meeting_code,user_email').execute()


def process_email(supabase, creds, email):
    log.info(f'Verificando agenda de {email}')

    events = get_calendar_events(creds, email)
    meet_events_raw = [(e, extract_meet_code(e)) for e in events]
    seen_codes = set()
    meet_events = []
    for e, c in meet_events_raw:
        if c and c not in seen_codes:
            seen_codes.add(c)
            meet_events.append((e, c))

    log.info(f'{len(meet_events)} reuniao(oes) com Meet encontrada(s) para {email}')

    for event, meeting_code in meet_events:
        titulo = event.get('summary', '(sem titulo)')

        try:
            if already_processed(supabase, meeting_code, email):
                log.info(f'[SKIP] {titulo} ({meeting_code}) - ja processada')
                continue

            log.info(f'[PROCESSANDO] {titulo} ({meeting_code})')

            space_name = resolve_space_name(creds, meeting_code)
            log.info(f'  space_name: {space_name}')

            enable_auto_recording(creds, space_name)

            register_in_supabase(supabase, {
                'meeting_code': meeting_code,
                'space_name': space_name,
                'user_email': email,
                'titulo_evento': titulo,
                'status': 'sucesso',
            })

            log.info(f'  [OK] Gravacao ativada: {titulo}')

        except Exception as e:
            log.error(f'  [ERRO] {titulo} ({meeting_code}): {e}')
            try:
                register_in_supabase(supabase, {
                    'meeting_code': meeting_code,
                    'space_name': None,
                    'user_email': email,
                    'titulo_evento': titulo,
                    'status': 'erro',
                    'mensagem_erro': str(e),
                })
            except Exception as e2:
                log.error(f'  [ERRO] Falha ao registrar no Supabase: {e2}')


def main():
    supabase_url = os.environ['SUPABASE_URL']
    supabase_key = os.environ['SUPABASE_KEY']
    emails_str = os.environ.get('EMAILS_MONITORADOS', '')
    intervalo = int(os.environ.get('INTERVALO_SEGUNDOS', '300'))

    emails = [e.strip() for e in emails_str.split(',') if e.strip()]
    if not emails:
        log.error('EMAILS_MONITORADOS esta vazio. Configure a variavel de ambiente.')
        sys.exit(1)

    log.info('=== Monitor de Gravacoes Google Meet ===')
    log.info(f'Emails monitorados: {emails}')
    log.info(f'Intervalo: {intervalo}s')

    supabase = create_client(supabase_url, supabase_key)
    creds = get_credentials()

    while True:
        log.info('--- Iniciando ciclo ---')
        for email in emails:
            try:
                process_email(supabase, creds, email)
            except Exception as e:
                log.error(f'Erro geral ao processar {email}: {e}')

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)

        log.info(f'--- Ciclo concluido. Proximo em {intervalo}s ---')
        time.sleep(intervalo)


if __name__ == '__main__':
    main()
