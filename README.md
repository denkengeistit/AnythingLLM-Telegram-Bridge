# AnythingLLM Telegram Bridge

A lightweight bridge that connects Telegram to [AnythingLLM](https://anythingllm.com/) workspaces. Messages sent to your Telegram bot are forwarded directly to an AnythingLLM workspace agent, and responses are sent back — with markdown-to-Telegram HTML conversion.

## Features

- **Direct forwarding** — no middleware; just a thin pipe between Telegram and AnythingLLM
- **Markdown → Telegram HTML** — code blocks, bold, italic, links, lists
- **Typing indicator** — shows "typing…" while waiting for AnythingLLM
- **Thread continuity** — per-chat thread tracking for multi-turn conversations
- **Access control** — optional user ID allowlist
- **Agent prefix** — automatically prepends `@agent` to activate workspace agent skills
- **Long message splitting** — handles responses >4 000 chars gracefully

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/anythingllm-telegram-bridge.git
cd anythingllm-telegram-bridge

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your tokens

# 4. Run
python telegram_anythingllm_bridge.py
```

## Configuration

All configuration is via environment variables (or a `.env` file):

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | **Yes** | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `ANYTHINGLLM_API_KEY` | **Yes** | — | API key from AnythingLLM → Settings → API Keys |
| `ANYTHINGLLM_BASE_URL` | No | `http://localhost:3001` | AnythingLLM instance URL |
| `ANYTHINGLLM_WORKSPACE` | No | `nanobot` | Workspace slug to chat with |
| `ALLOWED_USER_IDS` | No | `*` (all) | Comma-separated Telegram user IDs or usernames |
| `AGENT_PREFIX` | No | `true` | Prepend `@agent` to activate agent skills |

## Bot Commands

- `/start` — Welcome message
- `/new` — Reset conversation thread
- `/help` — Show help

## Requirements

- Python 3.10+
- A running AnythingLLM instance with API access
- A Telegram bot token

## License

MIT
