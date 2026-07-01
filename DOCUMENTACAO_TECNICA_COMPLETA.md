# Documentação Técnica Completa
## Sistema de Gravação Automática — Google Meet
**Versão:** 1.0  
**Preparado por:** Supervisão Comercial  
**Destinatário:** Time de TI  
**Data:** Julho/2026

---

## Contexto

Este documento descreve um sistema desenvolvido pela supervisão comercial que ativa automaticamente a gravação em reuniões do Google Meet dos closers da empresa. O objetivo é que o time de TI entenda o que foi construído e replique o sistema na infraestrutura oficial da empresa.

O protótipo está funcionando em contas pessoais/teste. A replicação deve ser feita em contas da empresa.

---

## O que o sistema faz

- A cada 5 minutos, lê a agenda de cada closer via Google Calendar API
- Para cada reunião futura com link do Google Meet, ativa a gravação automática via Google Meet REST API
- Registra tudo em banco de dados para não reprocessar a mesma reunião
- Roda de graça no GitHub Actions (sem servidor, sem custo)

**Limitação importante:** só detecta reuniões criadas pelo Google Agenda. Salas instantâneas (meet.new) não são detectáveis pela API.

---

## Arquitetura

```
GitHub Actions (cron a cada 5 min)
        ↓
Python script (monitor.py)
        ↓                    ↓
Google Calendar API     Google Meet REST API
(lê agenda)             (ativa gravação)
        ↓
Supabase (registra reuniões já processadas)
```

---

## Pré-requisitos

Antes de começar, o TI precisa ter acesso a:

- [ ] **Google Cloud Console** — para criar projeto, APIs e service account
- [ ] **Google Workspace Admin Console** (admin.google.com) — para conceder delegação de domínio
- [ ] **Conta no Supabase** (supabase.com) — banco de dados gratuito
- [ ] **Conta no GitHub** — para hospedar o código e rodar o GitHub Actions
- [ ] **Lista de emails dos closers** a serem monitorados

---

## Parte 1 — Google Cloud

### 1.1 Criar o projeto

1. Acesse **console.cloud.google.com**
2. Clique no seletor de projeto no topo → **Novo projeto**
3. Nome sugerido: `monitor-gravacao-meet`
4. Anote o **ID do projeto** gerado (será usado nos próximos passos)
5. Clique em **Criar**

### 1.2 Habilitar as APIs necessárias

Com o projeto selecionado:

1. No menu lateral: **APIs e serviços → Biblioteca**
2. Busque e habilite cada uma das APIs abaixo (uma por vez):
   - **Google Meet REST API**
   - **Google Calendar API**

Para cada uma: clique na API → clique em **Ativar**

### 1.3 Configurar a tela de consentimento OAuth

> Necessário para que o Google reconheça o projeto como aplicação autorizada.

1. Menu lateral: **APIs e serviços → Tela de consentimento OAuth**
2. Tipo de usuário: **Interno** (só usuários do domínio da empresa)
3. Clique em **Criar**
4. Preencha:
   - **Nome do app:** `Monitor Gravação Meet`
   - **E-mail de suporte:** email do responsável técnico
   - **Domínio autorizado:** domínio da empresa (ex: `empresa.com`)
5. Clique em **Salvar e continuar** até o final

### 1.4 Criar a conta de serviço (service account)

A conta de serviço é a "identidade" do robô no Google Cloud.

1. Menu lateral: **IAM e administrador → Contas de serviço**
2. Clique em **+ Criar conta de serviço**
3. Preencha:
   - **Nome:** `monitor-gravacao-meet`
   - **ID:** será preenchido automaticamente
   - **Descrição:** `Robô de gravação automática Google Meet`
4. Clique em **Criar e continuar**
5. Na tela de permissões: **não adicione nenhuma** — clique em **Continuar**
6. Clique em **Concluir**

### 1.5 Gerar a chave JSON da service account

1. Na lista de contas de serviço, clique na conta criada
2. Clique na aba **Chaves**
3. Clique em **Adicionar chave → Criar nova chave**
4. Selecione **JSON** → clique em **Criar**
5. Um arquivo `.json` será baixado automaticamente — **guarde com segurança**
6. **Nunca commitar este arquivo no GitHub**

### 1.6 Anotar o Client ID

1. Na mesma tela da conta de serviço, clique na aba **Detalhes**
2. Anote o **ID exclusivo** (número longo, ex: `123456789012345678901`)
3. Este número será usado na configuração do Google Workspace Admin

---

## Parte 2 — Google Workspace Admin Console

Esta é a etapa que permite ao robô acessar agendas e reuniões de todos os closers do domínio.

### 2.1 Conceder Domain-Wide Delegation

1. Acesse **admin.google.com** com a conta de administrador do Workspace
2. No menu lateral: **Segurança → Controles de acesso e dados → Controles de API**
3. Role até **Delegação em todo o domínio**
4. Clique em **Gerenciar delegação em todo o domínio**
5. Clique em **Adicionar novo**
6. Preencha os campos:

**ID do cliente:** cole o número anotado no passo 1.6

**Escopos OAuth:** cole exatamente o texto abaixo (tudo em uma linha):
```
https://www.googleapis.com/auth/calendar.events.readonly,https://www.googleapis.com/auth/meetings.space.settings,https://www.googleapis.com/auth/meetings.space.readonly
```

7. Clique em **Autorizar**

### O que cada escopo permite

| Escopo | O que faz |
|--------|-----------|
| `calendar.events.readonly` | Lê os eventos da agenda (somente leitura) |
| `meetings.space.settings` | Ativa gravação automática na sala do Meet |
| `meetings.space.readonly` | Lê informações da sala (necessário para obter o ID canônico) |

---

## Parte 3 — Supabase (banco de dados)

O Supabase é usado para guardar quais reuniões já foram processadas, evitando que o robô ative a gravação mais de uma vez na mesma sala.

### 3.1 Criar o projeto

1. Acesse **supabase.com** e faça login (ou crie conta da empresa)
2. Clique em **New project**
3. Preencha:
   - **Name:** `monitor-meet-producao`
   - **Database Password:** crie uma senha forte e guarde
   - **Region:** South America (São Paulo)
4. Clique em **Create new project** e aguarde ~2 minutos

### 3.2 Criar a tabela

1. No painel do projeto, clique em **SQL Editor** no menu lateral
2. Cole o código abaixo e clique em **Run**:

```sql
CREATE TABLE gravacoes_meet (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_code text NOT NULL,
  space_name text,
  user_email text NOT NULL,
  titulo_evento text,
  status text NOT NULL,
  mensagem_erro text,
  processado_em timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX idx_gravacoes_meet_codigo_email
  ON gravacoes_meet (meeting_code, user_email);
```

Deve aparecer: **"Success. No rows returned"**

### 3.3 Pegar as credenciais

1. No menu lateral: **Project Settings → API**
2. Copie e guarde:
   - **Project URL** (começa com `https://`)
   - **Secret key** (começa com `sb_secret_`) — não usar a Publishable key

---

## Parte 4 — GitHub

### 4.1 Criar o repositório

1. Acesse **github.com** na conta da empresa
2. Clique em **New repository**
3. Preencha:
   - **Name:** `monitor-meet-producao`
   - **Visibility:** Private
   - **Não inicializar** com README, .gitignore ou license
4. Clique em **Create repository**

### 4.2 Criar os arquivos do projeto

Crie os seguintes arquivos no repositório. O conteúdo de cada um está abaixo.

---

#### Arquivo: `monitor.py`

```python
import os
import sys
import pickle
import base64
import logging
import tempfile
from datetime import datetime, timezone, timedelta

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
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


def get_credentials(email):
    """Retorna credenciais da service account impersonando o email do closer."""
    sa_json_b64 = os.environ.get('SERVICE_ACCOUNT_JSON_BASE64')
    if not sa_json_b64:
        raise ValueError('SERVICE_ACCOUNT_JSON_BASE64 nao configurado')

    import json
    sa_info = json.loads(base64.b64decode(sa_json_b64).decode('utf-8'))

    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=SCOPES
    ).with_subject(email)

    return creds


def get_calendar_events(creds, email):
    now = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()

    creds.refresh(Request())
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


def process_email(supabase, email):
    log.info(f'Verificando agenda de {email}')
    creds = get_credentials(email)

    events = get_calendar_events(creds, email)
    seen_codes = set()
    meet_events = []
    for e in events:
        c = extract_meet_code(e)
        if c and c not in seen_codes:
            seen_codes.add(c)
            meet_events.append((e, c))

    log.info(f'{len(meet_events)} reuniao(oes) unica(s) com Meet para {email}')

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

    emails = [e.strip() for e in emails_str.split(',') if e.strip()]
    if not emails:
        log.error('EMAILS_MONITORADOS esta vazio.')
        sys.exit(1)

    log.info('=== Monitor de Gravacoes Google Meet ===')
    log.info(f'Emails monitorados: {len(emails)} closer(s)')

    supabase = create_client(supabase_url, supabase_key)

    log.info('--- Iniciando ciclo ---')
    for email in emails:
        try:
            process_email(supabase, email)
        except Exception as e:
            log.error(f'Erro geral ao processar {email}: {e}')

    log.info('--- Ciclo concluido ---')


if __name__ == '__main__':
    main()
```

---

#### Arquivo: `requirements.txt`

```
google-auth==2.29.0
google-auth-oauthlib==1.2.0
requests==2.32.3
supabase==2.31.0
```

---

#### Arquivo: `.github/workflows/monitor.yml`

> Criar a pasta `.github/workflows/` e dentro dela o arquivo `monitor.yml`

```yaml
name: Monitor Gravacoes Meet

on:
  schedule:
    - cron: '*/5 * * * *'
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Instalar dependencias
        run: pip install -r requirements.txt

      - name: Executar monitor
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          EMAILS_MONITORADOS: ${{ secrets.EMAILS_MONITORADOS }}
          SERVICE_ACCOUNT_JSON_BASE64: ${{ secrets.SERVICE_ACCOUNT_JSON_BASE64 }}
        run: python monitor.py
```

---

#### Arquivo: `.gitignore`

```
*.json
*.pickle
.env
__pycache__/
venv/
.DS_Store
```

---

### 4.3 Configurar os Secrets do GitHub Actions

Os secrets são variáveis de ambiente sigilosas que o GitHub injeta no script durante a execução.

1. No repositório, clique em **Settings**
2. No menu lateral: **Secrets and variables → Actions**
3. Clique em **New repository secret** para cada secret abaixo:

| Nome do secret | Valor |
|----------------|-------|
| `SUPABASE_URL` | URL do projeto Supabase (ex: `https://xxxxx.supabase.co`) |
| `SUPABASE_KEY` | Secret key do Supabase (começa com `sb_secret_`) |
| `EMAILS_MONITORADOS` | Emails dos closers separados por vírgula |
| `SERVICE_ACCOUNT_JSON_BASE64` | Conteúdo do arquivo JSON da service account em base64 (ver abaixo) |

#### Como gerar o SERVICE_ACCOUNT_JSON_BASE64

No terminal (Mac/Linux):
```bash
base64 -i caminho/para/service-account.json | tr -d '\n'
```

No Windows (PowerShell):
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("caminho\service-account.json"))
```

Cole o resultado como valor do secret `SERVICE_ACCOUNT_JSON_BASE64`.

---

## Parte 5 — Validar que está funcionando

### 5.1 Disparar o workflow manualmente

1. No repositório GitHub, clique em **Actions**
2. No lado esquerdo, clique em **Monitor Gravacoes Meet**
3. Clique em **Run workflow → Run workflow**
4. Aguarde a execução completar (ícone verde = sucesso, vermelho = erro)

### 5.2 Interpretar o log

Clique na execução → clique em **monitor** → expanda **Executar monitor**

Logs esperados:
```
[OK] Gravacao ativada: Nome da Reunião     ← gravação ativada com sucesso
[SKIP] Nome da Reunião - ja processada     ← já foi processada antes, pulou
[ERRO] Nome da Reunião: mensagem           ← algo deu errado (ver troubleshooting)
```

### 5.3 Verificar no Supabase

1. Acesse o projeto no Supabase
2. Clique em **Table Editor → gravacoes_meet**
3. Cada linha representa uma reunião processada

### 5.4 Teste end-to-end

1. Um closer cria um evento no **Google Agenda** para qualquer data futura, com link do Google Meet
2. Aguarda até 5 minutos
3. Verifica no log do GitHub Actions que aparece `[OK] Gravacao ativada`
4. Entra na reunião e confirma que a gravação inicia automaticamente

---

## Troubleshooting

| Erro no log | Causa provável | Solução |
|-------------|---------------|---------|
| `SERVICE_ACCOUNT_JSON_BASE64 nao configurado` | Secret não foi adicionado | Adicionar o secret no GitHub |
| `401 Unauthorized` | Service account sem permissão ou delegação não configurada | Verificar Parte 2 (domain-wide delegation) |
| `403 Forbidden` | Escopo insuficiente ou delegação com escopos errados | Refazer o passo 2.1 com os escopos corretos |
| `Invalid API key` | Chave do Supabase incorreta | Atualizar secret `SUPABASE_KEY` |
| Workflow não executa automaticamente | Repositório inativo por 60+ dias | Ir em Actions → Enable workflow |

---

## Manutenção

**Adicionar um closer:** editar o secret `EMAILS_MONITORADOS` no GitHub adicionando o email separado por vírgula.

**Remover um closer:** editar o secret `EMAILS_MONITORADOS` removendo o email.

**Ver histórico de reuniões processadas:** Supabase → Table Editor → `gravacoes_meet`.

**Custo:** o sistema roda inteiramente dentro dos planos gratuitos do GitHub Actions e Supabase. O único custo é zero.
