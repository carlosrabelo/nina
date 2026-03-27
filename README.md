# nina

Personal assistant CLI for managing multiple Gmail accounts, with Calendar and daily life features planned.

## Highlights

- Authenticate any number of Gmail accounts via Google OAuth — no manual email list required
- Auto-discovers authenticated accounts from saved tokens on startup
- List unread messages or search across all accounts simultaneously
- Show headers of the most recent emails per account
- Token refresh handled automatically — re-auth only when truly needed
- Account management: add, revoke, and check status per account

## Prerequisites

- **Python 3.12+**
- **Google Cloud project** with Gmail API enabled and an OAuth 2.0 Desktop client — [console.cloud.google.com](https://console.cloud.google.com)

## Installation

```bash
git clone https://github.com/carlosrabelo/nina.git
cd nina
make setup
```

Copy the environment template and set the credentials path:

```bash
cp .env.example .env
# Edit .env: set GOOGLE_CREDENTIALS_FILE to your credentials.json path
```

## Usage

### Authenticate an account

Run once per account — opens the browser, you pick the Google account:

```bash
make auth
# or: ./nina.py auth
```

Repeat for each account you want Nina to manage.

### Check authentication status

```bash
make status
# ✓  you@gmail.com
# ✓  work@gmail.com
```

### Show recent email headers

```bash
make latest
# ── you@gmail.com ───────────────────────────────────
#  ● Fri, 27 Mar 2026 10:32:00 -0300
#    From    : someone@example.com
#    Subject : Meeting tomorrow

make latest ACCOUNT=work@gmail.com
```

### Search messages

```bash
./nina.py search "subject:invoice is:unread"
./nina.py search "from:boss@company.com" --account work@gmail.com
```

### Revoke an account

```bash
./nina.py revoke you@gmail.com
```

## Configuration

Create `.env` from the template:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | `credentials/credentials.json` | Path to OAuth client credentials downloaded from Google Cloud Console |
| `TOKENS_DIR` | `tokens` | Directory where per-account tokens are stored after authentication |

## Project Layout

```
nina.py          # CLI entry point
gmail.py         # GmailClient (single account) + GmailMultiClient (N accounts)
auth.py          # OAuth flow, token caching, auto-discovery
errors.py        # NinaError, AuthError, GmailError, ConfigError
make/            # setup.sh, test.sh, lint.sh, auth.sh
credentials/     # credentials.json from Google Cloud Console (git-ignored)
tokens/          # per-account OAuth tokens (git-ignored)
tests/           # pytest test suite
```

## Development

```bash
make setup      # Create .venv and install dependencies (first time only)
make test       # Run all tests
make lint       # Lint with ruff
make fmt        # Format code with ruff
make typecheck  # Type-check with mypy
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

