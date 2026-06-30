# Monitor de Gravações Google Meet

Robô que verifica a agenda dos closers a cada 5 minutos e ativa automaticamente a gravação em reuniões Google Meet.

## Variáveis de ambiente necessárias

```
SUPABASE_URL=          # URL do projeto Supabase
SUPABASE_KEY=          # Service role key do Supabase
EMAILS_MONITORADOS=    # Lista separada por vírgula (ex: a@empresa.com,b@empresa.com)
INTERVALO_SEGUNDOS=    # Padrão: 300 (5 minutos)
```

## Rodando localmente

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Coloque credentials.json na pasta
python monitor.py
```

## Deploy (Render)

- Build command: `pip install -r requirements.txt`
- Start command: `python monitor.py`
- Adicionar `OAUTH_TOKEN_BASE64` e `OAUTH_CLIENT_SECRETS_BASE64` nas variáveis de ambiente
