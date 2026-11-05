# Roadmap

## Backlog

| Item | Impact | Effort | Priority | Status |
|------|--------|--------|----------|--------|
| CI via GitHub Actions (lint + test on push) | Medium | Small | P1 | Done |
| Publish to PyPI | High | Small | P1 | Pending |
| Shell completion for `llm freellmapi` | Low | Small | P2 | Pending |
| `--provider` filter for `llm freellmapi models` | Low | Small | P2 | Pending |
| Tool calling passthrough | Medium | Medium | P2 | Pending |
| Vision/attachments passthrough | Medium | Medium | P2 | Pending |
| Embeddings support | Low | Medium | P3 | Pending |
| Cache `/v1/models` for offline listing | Low | Small | P3 | Pending |

## Done

- [x] Initial plugin (v0.1.0)
- [x] `register_models` / `register_commands` against llm 0.36
- [x] Streaming SSE parser
- [x] `auto` default model and `-o model` override
- [x] Interactive and non-interactive `configure`
- [x] `models` (`--available`, `--json`) and `status` commands
- [x] Config precedence: env → `./.env` → global → `llm keys`
- [x] Base URL normalisation
- [x] Error handling for 401/404/429/timeout/connect
- [x] Mocked test suite
- [x] AES project docs (VISION, REQUIREMENTS, ROADMAP, CLAUDE.md)
- [x] Makefile (setup, test, lint, build, check, doctor)
- [x] GitHub Actions CI (lint, format, tests on 3.10–3.13, wheel build)
