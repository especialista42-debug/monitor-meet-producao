# Documentação Técnica Completa
## Sistema de Gravação Automática — Google Meet
**Versão:** 1.0  
**Preparado por:** Supervisão Comercial  
**Destinatário:** Time de TI  
**Data:** Julho/2026

---

## Índice
1. Objetivo do sistema
2. Arquitetura geral
3. O que já está configurado
4. O que o time de TI precisa fazer
5. Migração para conta de serviço (service account)
6. Adicionar os closers ao monitoramento
7. Como validar que está funcionando
8. Manutenção e troubleshooting
9. Referência de credenciais e acessos

---

## 1. Objetivo do sistema

Os closers esquecem de ativar a gravação nas reuniões do Google Meet. Isso prejudica o trabalho dos SDRs que precisam das gravações para análise.

**Solução:** um robô que roda automaticamente a cada 5 minutos, verifica a agenda de cada closer e ativa a gravação automática em toda reunião nova do Google Meet — sem que ninguém precise fazer nada.

**O robô:**
- Lê a agenda dos closers via Google Calendar API
- Identifica reuniões futuras com link do Google Meet
- Ativa a gravação automática via Google Meet REST API
- Registra tudo num banco de dados (Supabase) para não reprocessar a mesma reunião
- Roda de graça no GitHub Actions (execução automática a cada 5 minutos)

---

## 2. Arquitetura geral

```
GitHub Actions (roda a cada 5 min, gratuito)
        ↓
monitor.py (script Python)
        ↓
Google Calendar API          Google Meet REST API
(lê agenda de cada closer)   (ativa gravação)
        ↓
Supabase (banco de dados — registra reuniões processadas)
```

**Fluxo por reunião:**
1. Script lê eventos futuros (próximos 60 dias) da agenda do closer
2. Para cada evento com link do Google Meet:
   - Verifica no Supabase se já foi processado (evita duplicatas)
   - Se não: faz GET na Meet API para obter o ID canônico da sala
   - Faz PATCH na Meet API para ativar `autoRecordingGeneration: ON`
   - Registra no Supabase com status (sucesso ou erro)

---

## 3. O que já está configurado

### 3.1 Projeto no Google Cloud
- **Nome:** `meet-auto-record-test`
- **ID:** `372339982498`
- **APIs habilitadas:** Google Meet REST API, Google Calendar API
- **Conta de serviço criada:**
  - Nome: `monitor-gravacao-meet`
  - Email: `monitor-gravacao-meet@meet-auto-record-test.iam.gserviceaccount.com`
  - Client ID: `116621524327967144081`
  - Chave JSON: baixada e armazenada com a supervisão comercial

### 3.2 Banco de dados (Supabase)
- **Projeto:** `monitor-meet-producao`
- **URL:** `https://wuywqkgnqvcciqychzll.supabase.co`
- **Tabela:** `gravacoes_meet` com os campos:
  - `id` (uuid, chave primária)
  - `meeting_code` (código de 10 letras da sala, ex: `abc-defg-hij`)
  - `space_name` (ID canônico, ex: `spaces/jMGTLqH9uBEB`)
  - `user_email` (email do closer dono da agenda)
  - `titulo_evento` (título do evento no Google Agenda)
  - `status` (`sucesso` ou `erro`)
  - `mensagem_erro` (detalhes em caso de falha)
  - `processado_em` (timestamp automático)
- **Índice único:** `(meeting_code, user_email)` — evita reprocessamento

### 3.3 Código-fonte
- **Repositório GitHub:** `github.com/especialista42-debug/monitor-meet-producao`
- **Arquivo principal:** `monitor.py`
- **Dependências:** `requirements.txt`
- **Execução automática:** `.github/workflows/monitor.yml` (cron a cada 5 minutos)

### 3.4 Estado atual
O sistema está **funcionando em produção** mas com autenticação OAuth pessoal (email da supervisora). Isso significa que por enquanto só monitora a agenda dela. Para monitorar todos os closers, é necessário concluir a migração para service account com domain-wide delegation (descrita nas seções 4 e 5).

---

## 4. O que o time de TI precisa fazer

### Tarefa única: conceder Domain-Wide Delegation no Google Workspace

**O que é:** autorizar a conta de serviço do robô a acessar agendas e configurações de reuniões de qualquer usuário do domínio, sem que cada um precise autorizar individualmente.

**Por que é necessário:** o Google Workspace, por padrão, não permite que sistemas externos acessem dados de usuários. A delegação em todo o domínio é o mecanismo oficial do Google para isso.

**Pré-requisito:** acesso de administrador ao Google Workspace (admin.google.com)

---

### Passo a passo

**Passo 1 — Acessar o Admin Console**
1. Abra o navegador e acesse: **admin.google.com**
2. Entre com a conta de administrador do Google Workspace da empresa

**Passo 2 — Navegar até Delegação em Todo o Domínio**
1. No menu lateral esquerdo, clique em **Segurança**
2. Clique em **Controles de acesso e dados**
3. Clique em **Controles de API**
4. Role a página até encontrar a seção **Delegação em todo o domínio**
5. Clique em **Gerenciar delegação em todo o domínio**

> Se não encontrar o caminho acima, use a barra de pesquisa do Admin Console e busque por "Delegação em todo o domínio"

**Passo 3 — Adicionar a conta de serviço**
1. Clique no botão **Adicionar novo**
2. Uma janela vai abrir com dois campos

**Passo 4 — Preencher o ID do cliente**

No campo **ID do cliente**, cole exatamente o número abaixo:
```
116621524327967144081
```

**Passo 5 — Preencher os escopos OAuth**

No campo **Escopos OAuth**, cole exatamente o texto abaixo (tudo em uma linha, sem quebra):
```
https://www.googleapis.com/auth/calendar.events.readonly,https://www.googleapis.com/auth/meetings.space.settings,https://www.googleapis.com/auth/meetings.space.readonly
```

**Passo 6 — Salvar**
1. Clique em **Autorizar**
2. A entrada vai aparecer na lista com o Client ID e os escopos

**Passo 7 — Confirmar**
Avisar a supervisora Camilli que a delegação foi concluída. Ela vai coordenar os próximos passos técnicos.

---

### O que cada escopo faz

| Escopo | Permissão | Justificativa |
|--------|-----------|---------------|
| `calendar.events.readonly` | Leitura dos eventos da agenda | Necessário para saber quais reuniões cada closer tem |
| `meetings.space.settings` | Alterar configurações da sala do Meet | Necessário para ativar a gravação automática |
| `meetings.space.readonly` | Leitura das informações da sala | Necessário para resolver o ID canônico da sala antes de alterar |

---

## 5. Migração para conta de serviço (feita pela supervisão com suporte técnico)

Após o TI concluir a delegação, o script precisa ser atualizado para usar a conta de serviço em vez da autenticação OAuth pessoal. Esta etapa é feita pela supervisão comercial com suporte técnico.

**Resumo das mudanças:**
- Adicionar o arquivo JSON da conta de serviço como secret no GitHub (`SERVICE_ACCOUNT_JSON`)
- Atualizar o `monitor.py` para usar `service_account.Credentials` com impersonação por email
- Remover os secrets de OAuth pessoal (`OAUTH_TOKEN_BASE64`, `OAUTH_CLIENT_SECRETS_BASE64`)

**Para referência do TI — como o script vai autenticar após a migração:**
```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_info(
    service_account_json,
    scopes=SCOPES
).with_subject(email_do_closer)
```

---

## 6. Adicionar os closers ao monitoramento

Após a migração para service account, a supervisora adiciona os emails dos closers no GitHub:

1. Acessar o repositório no GitHub
2. Ir em **Settings → Secrets and variables → Actions**
3. Editar o secret `EMAILS_MONITORADOS`
4. Adicionar os emails separados por vírgula:
   ```
   closer1@empresa.com,closer2@empresa.com,closer3@empresa.com
   ```

O robô passa a monitorar todos os emails listados na próxima execução (até 5 minutos).

---

## 7. Como validar que está funcionando

### Verificar execuções no GitHub Actions
1. Acesse `github.com/especialista42-debug/monitor-meet-producao`
2. Clique em **Actions**
3. A lista mostra todas as execuções — deve haver uma nova a cada ~5 minutos
4. Clique em qualquer execução e expanda o passo **"Executar monitor"**
5. O log deve mostrar algo como:
   ```
   [OK] Gravacao ativada: Nome da Reunião
   ```
   ou
   ```
   [SKIP] Nome da Reunião - ja processada
   ```

### Verificar no banco de dados (Supabase)
1. Acessar o projeto Supabase em supabase.com
2. Ir em **Table Editor → gravacoes_meet**
3. Cada linha é uma reunião processada com status `sucesso` ou `erro`

### Testar com uma reunião real
1. Um closer cria um evento no **Google Agenda** com link do Google Meet
2. Aguardar até 5 minutos
3. Verificar no log do GitHub Actions que a reunião foi processada
4. Entrar na reunião e confirmar que a gravação inicia automaticamente

---

## 8. Manutenção e troubleshooting

### O robô parou de funcionar
1. Verificar **Actions** no GitHub — ver se as execuções estão com erro (ícone vermelho)
2. Abrir a execução com erro e ler o log do passo "Executar monitor"
3. Erros comuns:
   - `401 Unauthorized`: token OAuth expirou → refazer autenticação OAuth ou verificar service account
   - `403 Forbidden`: permissão insuficiente → verificar delegação no Admin Console
   - `Invalid API key`: chave do Supabase inválida → atualizar secret `SUPABASE_KEY`

### GitHub Actions parou de disparar automaticamente
- Repositórios públicos com inatividade por mais de 60 dias têm os workflows pausados
- Para reativar: ir em **Actions → Monitor Gravacoes Meet → Enable workflow**

### Adicionar ou remover um closer
- Editar o secret `EMAILS_MONITORADOS` no GitHub (Settings → Secrets and variables → Actions)

### Token OAuth expirou (fase atual, antes da service account)
- O token OAuth tem validade longa mas pode expirar se revogado
- Sintoma: log mostra erro 401
- Solução: refazer a autenticação localmente e atualizar o secret `OAUTH_TOKEN_BASE64`

---

## 9. Referência de credenciais e acessos

| Componente | Onde acessar | Responsável |
|-----------|-------------|-------------|
| Google Cloud Console | console.cloud.google.com | Supervisão Comercial |
| Google Admin Console | admin.google.com | TI |
| Repositório GitHub | github.com/especialista42-debug/monitor-meet-producao | Supervisão Comercial |
| Banco de dados Supabase | supabase.com | Supervisão Comercial |
| JSON da service account | Armazenado com a supervisão | Supervisão Comercial |
| Secrets do GitHub Actions | GitHub → Settings → Secrets | Supervisão Comercial |

---

## Escopos OAuth (para referência rápida)

```
https://www.googleapis.com/auth/calendar.events.readonly
https://www.googleapis.com/auth/meetings.space.settings
https://www.googleapis.com/auth/meetings.space.readonly
```

## Client ID da service account

```
116621524327967144081
```

## Projeto Google Cloud

```
meet-auto-record-test (ID: 372339982498)
```
