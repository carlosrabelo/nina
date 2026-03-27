# nina

Assistente pessoal via CLI para gerenciar múltiplas contas Gmail, com recursos de Agenda e vida diária planejados.

## Destaques

- Autentica qualquer número de contas Gmail via Google OAuth — sem necessidade de listar emails manualmente
- Descobre automaticamente as contas autenticadas a partir dos tokens salvos na inicialização
- Lista mensagens não lidas ou pesquisa em todas as contas simultaneamente
- Exibe os cabeçalhos dos emails mais recentes por conta
- Renovação de tokens feita automaticamente — reautenticação apenas quando realmente necessário
- Gerenciamento de contas: adicionar, revogar e verificar status por conta

## Pré-requisitos

- **Python 3.12+**
- **Projeto no Google Cloud** com a Gmail API habilitada e um cliente OAuth 2.0 Desktop — [console.cloud.google.com](https://console.cloud.google.com)

## Instalação

```bash
git clone https://github.com/carlosrabelo/nina.git
cd nina
make setup
```

Copie o template de configuração e defina o caminho das credenciais:

```bash
cp .env.example .env
# Edite o .env: defina GOOGLE_CREDENTIALS_FILE com o caminho do seu credentials.json
```

## Uso

### Autenticar uma conta

Execute uma vez por conta — abre o navegador para você escolher a conta Google:

```bash
make auth
# ou: ./nina.py auth
```

Repita para cada conta que deseja gerenciar com a Nina.

### Verificar status de autenticação

```bash
make status
# ✓  voce@gmail.com
# ✓  trabalho@gmail.com
```

### Exibir cabeçalhos dos emails recentes

```bash
make latest
# ── voce@gmail.com ───────────────────────────────────
#  ● Sex, 27 Mar 2026 10:32:00 -0300
#    From    : alguem@example.com
#    Subject : Reunião amanhã

make latest ACCOUNT=trabalho@gmail.com
```

### Pesquisar mensagens

```bash
./nina.py search "subject:fatura is:unread"
./nina.py search "from:chefe@empresa.com" --account trabalho@gmail.com
```

### Revogar uma conta

```bash
./nina.py revoke voce@gmail.com
```

## Configuração

Crie o `.env` a partir do template:

```bash
cp .env.example .env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `credentials/credentials.json` | Caminho para as credenciais OAuth baixadas do Google Cloud Console |
| `TOKENS_DIR` | `tokens` | Diretório onde os tokens por conta são armazenados após a autenticação |

## Estrutura do Projeto

```
nina.py          # Ponto de entrada CLI
gmail.py         # GmailClient (conta única) + GmailMultiClient (N contas)
auth.py          # Fluxo OAuth, cache de tokens, descoberta automática
errors.py        # NinaError, AuthError, GmailError, ConfigError
make/            # setup.sh, test.sh, lint.sh, auth.sh
credentials/     # credentials.json do Google Cloud Console (ignorado pelo git)
tokens/          # tokens OAuth por conta (ignorados pelo git)
tests/           # suite de testes pytest
```

## Desenvolvimento

```bash
make setup      # Cria o .venv e instala dependências (apenas na primeira vez)
make test       # Executa todos os testes
make lint       # Lint com ruff
make fmt        # Formata o código com ruff
make typecheck  # Verificação de tipos com mypy
```

## Licença

Este projeto está licenciado sob a Licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.
