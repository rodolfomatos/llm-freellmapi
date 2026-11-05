# Requirements

## Functional

| ID | Description | Priority |
|----|-------------|----------|
| F1 | Plugin registers a `freellmapi` model with the `llm` CLI | Must |
| F2 | Requests go to the configured FreeLLMAPI `/v1/chat/completions` endpoint | Must |
| F3 | Streaming responses are parsed from SSE and yielded incrementally | Must |
| F4 | Non-streaming responses are supported | Must |
| F5 | System prompts and multi-turn conversations are forwarded | Must |
| F6 | `auto` is the default model id, using FreeLLMAPI's router | Must |
| F7 | `-o model <id>` pins a specific FreeLLMAPI model per request | Must |
| F8 | `llm freellmapi configure` writes `~/.config/freellmapi/env` (0600) | Must |
| F9 | `llm freellmapi models` lists the live catalog (`--available`, `--json`) | Must |
| F10 | `llm freellmapi status` reports server and key validity | Must |
| F11 | Config loads from env vars, `./.env`, global config and `llm keys` | Must |
| F12 | Clear errors for 401, 404, 429, timeout and connection failure | Must |
| F13 | Sampling options (`temperature`, `max_tokens`, `top_p`, penalties) | Should |
| F14 | Base URLs with or without `/v1` are normalised | Should |
| F15 | Standalone `llm-freellmapi` script mirrors the subcommands | Should |

## Non-Functional

| ID | Description | Priority |
|----|-------------|----------|
| NF1 | Dependencies limited to `llm` and `httpx` | Must |
| NF2 | Single Python source file | Must |
| NF3 | No API key written to logs or stdout | Must |
| NF4 | Tests use mocked HTTP only — no network access | Must |
| NF5 | Works on Linux and macOS (Windows via WSL) | Should |
| NF6 | Installation via `pip install llm-freellmapi` and `pipx inject llm` | Must |
| NF7 | Compatible with `llm>=0.36` | Must |
| NF8 | Timeout: 120 s non-streaming, none for streaming | Must |

## Out of Scope

- Running the FreeLLMAPI server
- Provider key management, quota dashboards, or billing
- Local model inference
- Embeddings, image generation and audio endpoints (chat only in v0.1)
- Tool calling and attachments (chat text only in v0.1)
