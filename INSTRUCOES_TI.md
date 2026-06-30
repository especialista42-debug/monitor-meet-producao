# Configuração: Robô de Gravação Automática Google Meet

## O que esse robô faz
Verifica automaticamente a agenda dos closers a cada 5 minutos e ativa a gravação em toda reunião nova do Google Meet — sem depender de ninguém lembrar de clicar em "Gravar".

## O que NÃO faz
- Não acessa o conteúdo das reuniões
- Não grava nada diretamente
- Não coleta dados pessoais
- Apenas liga o botão de gravação automática no espaço da reunião

---

## O que o TI precisa fazer (única tarefa)

Conceder **Delegação em Todo o Domínio** para a conta de serviço do robô.

Isso permite que o robô leia a agenda dos colaboradores e configure as reuniões em nome deles, sem precisar que cada um autorize individualmente.

### Passo a passo no Google Admin Console

1. Entrar em **admin.google.com** com a conta de admin do Workspace
2. No menu esquerdo: **Segurança** → **Controles de acesso e dados** → **Controles de API**
3. Na seção **Delegação em todo o domínio**, clicar em **Gerenciar delegação em todo o domínio**
4. Clicar em **Adicionar novo**
5. Preencher os dois campos:

**ID do cliente:**
```
116621524327967144081
```

**Escopos OAuth (copiar tudo de uma vez):**
```
https://www.googleapis.com/auth/calendar.events.readonly,https://www.googleapis.com/auth/meetings.space.settings,https://www.googleapis.com/auth/meetings.space.readonly
```

6. Clicar em **Autorizar**

Pronto. Não precisa mexer em mais nada.

---

## O que cada escopo faz

| Escopo | Para que serve |
|--------|---------------|
| `calendar.events.readonly` | Ler (só ler) os eventos da agenda dos closers |
| `meetings.space.settings` | Ativar gravação automática na reunião |
| `meetings.space.readonly` | Ler informações da sala do Meet |

---

## Depois da configuração

Avisar a Camilli que a delegação foi concluída. Ela cuida do restante.
