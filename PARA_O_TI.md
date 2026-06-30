# Robô de Gravação Automática — Google Meet
**Documento de contexto e configuração para o TI**
Preparado por: Camilli | Supervisora Comercial

---

## 1. Contexto e objetivo

Os closers da empresa frequentemente esquecem de ativar a gravação nas reuniões do Google Meet. Isso prejudica o trabalho dos SDRs, que precisam das gravações para análise e acompanhamento.

**Solução criada:** um robô que verifica automaticamente a agenda de cada closer a cada 5 minutos e ativa a gravação em toda reunião nova do Google Meet — sem que ninguém precise fazer nada.

---

## 2. O que já foi feito (o robô está funcionando)

A Camilli, com apoio técnico, construiu e colocou em produção o seguinte:

### Código e repositório
- Script Python (`monitor.py`) que lê o Google Agenda e ativa gravação via Google Meet API
- Código hospedado no GitHub: `github.com/especialista42-debug/monitor-meet-producao`

### Banco de dados
- Projeto criado no Supabase com tabela `gravacoes_meet`
- Registra cada reunião processada (código da sala, email do closer, status, data/hora)
- Evita reprocessar a mesma reunião em ciclos futuros

### Execução automática
- GitHub Actions executa o script automaticamente a cada 5 minutos, 24 horas por dia, 7 dias por semana
- Gratuito (dentro do plano free do GitHub)
- Já validado e funcionando com o email da Camilli

### Projeto no Google Cloud
- Projeto: `meet-auto-record-test` (ID: `372339982498`)
- APIs habilitadas: Google Meet REST API e Google Calendar API
- Conta de serviço criada: `monitor-gravacao-meet`
  - Client ID: `116621524327967144081`

---

## 3. O que falta (única tarefa do TI)

O robô atualmente funciona apenas com o email da Camilli, porque usa autenticação pessoal dela. Para monitorar todos os closers da empresa, é necessário conceder **Delegação em Todo o Domínio** à conta de serviço no Google Admin Console.

**O que isso significa:** autorizar o robô a ler agendas e configurar reuniões em nome dos usuários do domínio, sem que cada closer precise autorizar individualmente.

**O que o robô faz com esse acesso:**
- Lê (somente leitura) os eventos futuros da agenda de cada closer
- Ativa gravação automática nas reuniões que têm link do Google Meet
- Registra o resultado no banco de dados

**O que o robô NÃO faz:**
- Não acessa conteúdo de conversas, e-mails ou arquivos
- Não grava nada diretamente — apenas liga o botão de gravação automática
- Não modifica, cria ou deleta eventos na agenda
- Não coleta dados pessoais

---

## 4. Passo a passo: configurar a delegação

**Tempo estimado: 5 minutos**

### Pré-requisito
Acesso de administrador ao Google Workspace da empresa (admin.google.com)

### Passos

**1.** Acesse **admin.google.com** e faça login com a conta de administrador

**2.** No menu lateral esquerdo, clique em **Segurança**

**3.** Clique em **Controles de acesso e dados**

**4.** Clique em **Controles de API**

**5.** Na seção **Delegação em todo o domínio**, clique em **Gerenciar delegação em todo o domínio**

**6.** Clique em **Adicionar novo**

**7.** No campo **ID do cliente**, cole exatamente:
```
116621524327967144081
```

**8.** No campo **Escopos OAuth**, cole exatamente (tudo em uma linha):
```
https://www.googleapis.com/auth/calendar.events.readonly,https://www.googleapis.com/auth/meetings.space.settings,https://www.googleapis.com/auth/meetings.space.readonly
```

**9.** Clique em **Autorizar**

**Pronto.** Não precisa mexer em mais nada.

---

## 5. O que cada escopo autoriza

| Escopo | O que faz |
|--------|-----------|
| `calendar.events.readonly` | Lê os eventos da agenda (somente leitura, não modifica nada) |
| `meetings.space.settings` | Ativa a gravação automática na sala do Meet |
| `meetings.space.readonly` | Lê as informações da sala (necessário para identificar o ID correto) |

---

## 6. Depois da configuração

Avisar a Camilli que a delegação foi concluída. Ela irá:
1. Atualizar o robô para usar a conta de serviço no lugar da autenticação pessoal
2. Adicionar os emails de todos os closers na lista de monitoramento
3. Validar com uma reunião de teste

Qualquer dúvida técnica sobre o projeto, a Camilli pode acionar o suporte que acompanhou o desenvolvimento.

---

## 7. Informações técnicas de referência

| Item | Valor |
|------|-------|
| Projeto Google Cloud | `meet-auto-record-test` |
| ID do projeto | `372339982498` |
| Conta de serviço | `monitor-gravacao-meet` |
| Client ID | `116621524327967144081` |
| Repositório | `github.com/especialista42-debug/monitor-meet-producao` |
| Banco de dados | Supabase — projeto `monitor-meet-producao` |
| Execução | GitHub Actions — a cada 5 minutos |
