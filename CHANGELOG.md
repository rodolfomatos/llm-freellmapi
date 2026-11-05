# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI: lint, format check and tests on Python 3.10–3.13, plus a
  wheel build and install verification.

### Fixed

- `llm freellmapi configure` no longer prompts when any flag is supplied;
  unspecified values fall back to the existing config or defaults.
- `llm freellmapi status` reports "status check failed" instead of claiming
  the server is unreachable when the actual error is a 401.

## [0.1.0] — 2026-11-05

### Added

- `freellmapi` model for the `llm` CLI, backed by FreeLLMAPI's
  OpenAI-compatible `/v1/chat/completions` endpoint.
- Streaming and non-streaming responses.
- Conversation support (system prompts, `llm chat`).
- `llm freellmapi configure` — interactive and non-interactive setup, with
  validation against the running server.
- `llm freellmapi models` — list the catalog, with `--available` and `--json`.
- `llm freellmapi status` — check server reachability and key validity.
- `llm-freellmapi` standalone script (`configure`, `models`, `status`).
- Configuration via `~/.config/freellmapi/env`, `./.env`, environment
  variables or `llm keys set freellmapi`.
- Per-request options: `model`, `temperature`, `max_tokens`, `top_p`,
  `frequency_penalty`, `presence_penalty`.
- Clear error messages for 401, 404, 429, timeouts and connection failures.
- Test suite with mocked HTTP responses.
