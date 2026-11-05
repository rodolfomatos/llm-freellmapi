# llm-freellmapi — Operational Contract

## Intent
Single-file Python plugin for the `llm` CLI that calls a FreeLLMAPI server's
OpenAI-compatible endpoint. Users run `llm -m freellmapi "question"` from any
directory.

## Non-Goals
- No adapter server, Docker or Node.js in this repository
- No local model inference
- No multi-file Python architecture unless explicitly requested
- No dependency beyond `llm`, `httpx` and their transitive dependencies

## Critical Files
- `llm_freellmapi.py` — only source file; plugin entry point
- `pyproject.toml` — package metadata and `llm` entry point
- `tests/` — pytest suite (mocked HTTP only, never the network)
- `~/.config/freellmapi/env` — global user config (created by `configure`)

## Never-Do
- Do NOT commit API keys, `~/.config/freellmapi/env` or `.env` files
- Do NOT break the single-model contract (`llm -m freellmapi`)
- Do NOT add a required daemon or adapter to this repo
- Do NOT call the network from the test suite
- Do NOT add `python-dotenv`; the dotenv parser stays local and dependency-free
- Do NOT remove the `auto` default: FreeLLMAPI's router owns model selection
- Do NOT add emojis to source code (CLI output uses `[OK]`, `[WARN]`, `[FAIL]`)

## API Compatibility
The plugin targets `llm>=0.36`:
- Hook: `register_models(register)` (not the removed `register(models)` provider API)
- Hook: `register_commands(cli)`
- Model: `llm.Model` subclass with `model_id`, `can_stream`, `Options`
- Execute: `execute(prompt, stream, response, conversation)`
- Messages: read from `prompt.messages`

## Testing
```bash
make test        # pytest, mocked HTTP
make lint        # ruff check
make build       # wheel + sdist (verifies packaging)
```

End-to-end (requires a running server and a key):
```bash
llm freellmapi status
llm -m freellmapi "Hello"
```

## Config Precedence
1. `os.environ` (`FREELLMAPI_*`)
2. `./.env` (local)
3. `~/.config/freellmapi/env` (global)
4. `llm keys set freellmapi`

## Setup Commands
```bash
make setup       # editable install + dev dependencies
make configure   # interactive — base URL, key, model
make check       # verify registration and server connectivity
```
