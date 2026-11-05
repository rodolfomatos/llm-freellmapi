# llm-freellmapi

Plugin for [LLM](https://llm.datasette.io/) that connects the `llm` CLI to
[FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) — dozens of free LLM
providers behind one OpenAI-compatible endpoint.

One install, one key, and you can use FreeLLMAPI's router from the terminal:

```bash
llm -m freellmapi "What is the capital of Portugal?"
```

## Requirements

- Python 3.10+
- [`llm`](https://llm.datasette.io/) 0.36+
- A running FreeLLMAPI server with at least one provider key configured
- The **unified API key** from the FreeLLMAPI dashboard (`http://localhost:3001`
  → **Keys**)

If you do not have FreeLLMAPI yet, follow the
[upstream installation guide](https://github.com/tashfeenahmed/freellmapi) or,
on a machine that already has the repository checked out, run:

```bash
cd /opt/freellmapi
make install-systemd   # optional: always-on service
make systemd-start
```

## Install

### From GitHub (works before the PyPI release)

```bash
pip install "git+https://github.com/rodolfomatos/llm-freellmapi.git"
```

With pipx:

```bash
pipx inject llm "git+https://github.com/rodolfomatos/llm-freellmapi.git"
```

### PyPI

```bash
pip install llm-freellmapi
```

### pipx (once published)

```bash
pipx inject llm llm-freellmapi
```

Ubuntu 23.04+ and other PEP 668 systems block system-wide `pip install`; use
`pipx` or a virtual environment.

### Virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install llm llm-freellmapi
```

### From source

```bash
git clone https://github.com/rodolfomatos/llm-freellmapi.git
cd llm-freellmapi
make setup
```

## Configure

```bash
llm freellmapi configure
```

The command prompts for:

| Setting | Default | Where to find it |
|---------|---------|------------------|
| Base URL | `http://localhost:3001/v1` | Your FreeLLMAPI server |
| API key | — | Dashboard → **Keys** (unified key) |
| Model | `auto` | Let FreeLLMAPI's router choose |

It writes `~/.config/freellmapi/env` with `0600` permissions and validates the
connection immediately.

You can also configure non-interactively:

```bash
llm freellmapi configure \
  --base-url http://localhost:3001 \
  --api-key freellmapi-... \
  --model auto
```

Or use the standalone script installed with the plugin:

```bash
llm-freellmapi configure
```

### Alternative: `llm keys`

If you prefer the standard LLM key store:

```bash
llm keys set freellmapi
# paste the unified key when prompted
```

## Usage

```bash
# One-off prompt
llm -m freellmapi "Explain TCP in one paragraph"

# Use FreeLLMAPI as the default model
llm models default freellmapi
llm "Explain TCP in one paragraph"

# Interactive chat
llm chat -m freellmapi

# Pipe input
cat article.txt | llm -m freellmapi "Summarize this"

# Pick a specific model for one request
llm -m freellmapi -o model gpt-4o-mini "Write a haiku about Lisbon"

# Tune sampling options
llm -m freellmapi -o temperature 0.2 -o max_tokens 200 "Be concise"
```

The default model id is `auto`: FreeLLMAPI routes each request to an available
free model and fails over automatically when a provider is rate-limited. Use
`-o model <id>` only when you want to pin a specific provider model.

## Commands

```bash
llm freellmapi configure   # write the endpoint, key and default model
llm freellmapi models      # list models exposed by the server
llm freellmapi models --available   # only models usable right now
llm freellmapi models --json        # raw JSON (scripting)
llm freellmapi status      # check server + key
```

Example:

```text
$ llm freellmapi models
Models available at http://localhost:3001/v1:
  - auto  (freellmapi)
  - gpt-4o-mini  (openai)
  - claude-3-5-haiku  (anthropic)
  ...
Total: 42 model(s)
Use a specific model with: llm -m freellmapi -o model <model-id> ...
```

## Options

| Option | Type | Description |
|--------|------|-------------|
| `model` | string | FreeLLMAPI model id for this request (default `auto`) |
| `temperature` | float | Sampling temperature (0–2) |
| `max_tokens` | int | Maximum tokens to generate |
| `top_p` | float | Nucleus sampling probability mass (0–1) |
| `frequency_penalty` | float | Frequency penalty (-2–2) |
| `presence_penalty` | float | Presence penalty (-2–2) |

## Configuration precedence

Highest priority wins:

1. Process environment variables (`FREELLMAPI_*`)
2. `./.env` in the current directory
3. `~/.config/freellmapi/env`
4. `llm keys` (`llm keys set freellmapi`)

Supported variables:

| Variable | Default |
|----------|---------|
| `FREELLMAPI_BASE_URL` | `http://localhost:3001/v1` |
| `FREELLMAPI_API_KEY` | — |
| `FREELLMAPI_MODEL` | `auto` |

A missing `/v1` suffix is added automatically, so
`http://localhost:3001` and `http://localhost:3001/v1` are equivalent.

## How it works

The plugin registers a single `freellmapi` model with the `llm` CLI. Every
request is sent to `POST /v1/chat/completions` on the configured FreeLLMAPI
server, using the OpenAI chat-completions format. Streaming responses are
parsed from server-sent events and yielded token by token, so `llm`'s normal
streaming, chat, logging and pipe behaviour all work.

No adapter server or extra runtime is required beyond FreeLLMAPI itself.

## Troubleshooting

**`Could not connect to FreeLLMAPI`** — the server is not running or the base
URL is wrong.

```bash
llm freellmapi status
curl -s http://localhost:3001/v1/models -H "Authorization: Bearer $FREELLMAPI_API_KEY"
```

If FreeLLMAPI is installed at `/opt/freellmapi`:

```bash
cd /opt/freellmapi && make systemd-status
```

**`FreeLLMAPI rejected the API key (401)`** — copy the unified key again from
the dashboard's **Keys** page and run `llm freellmapi configure`.

**No models / all providers rate-limited** — FreeLLMAPI needs at least one
provider key enabled in the dashboard, and each free tier has its own limits.

## Development

```bash
git clone https://github.com/rodolfomatos/llm-freellmapi.git
cd llm-freellmapi

make setup        # editable install + test dependencies
make test         # pytest
make lint         # ruff
make check        # plugin registration + config sanity check
make build        # wheel + sdist
```

## Project

- [VISION](docs/VISION.md) — problem, solution, value proposition
- [REQUIREMENTS](docs/REQUIREMENTS.md) — functional and non-functional requirements
- [ROADMAP](docs/ROADMAP.md) — backlog and progress
- [CHANGELOG](CHANGELOG.md) — version history
- [CLAUDE.md](CLAUDE.md) — operational contract for AI agents

## License

MIT — see [LICENSE](LICENSE).
