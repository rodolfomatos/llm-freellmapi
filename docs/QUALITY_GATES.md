# Quality Gates

Every release must pass all gates below. A failing gate blocks the release.

## G1 — Lint
```bash
make lint
```
No ruff errors.

## G2 — Formatting
```bash
make format-check
```
No reformatting required.

## G3 — Tests
```bash
make test
```
All tests pass. The suite must never make real network calls.

## G4 — Packaging
```bash
make build
```
Wheel and sdist build cleanly. Install the wheel in a fresh venv and confirm:

```bash
llm plugins | grep freellmapi
llm freellmapi --help
```

## G5 — End-to-end (manual, requires server)
```bash
export FREELLMAPI_API_KEY="freellmapi-..."
llm freellmapi status
llm -m freellmapi "Reply with exactly: OK"
llm -m freellmapi -o model auto "Reply with exactly: OK"
```

## G6 — Secret hygiene
```bash
git grep -nE "freellmapi-[0-9a-f]{20,}" || echo "no keys"
```
No API keys in tracked files. `~/.config/freellmapi/env` and `.env` stay
untracked.

## G7 — Docs
README commands are executable as written. CHANGELOG reflects the release.
`pyproject.toml` version matches the CHANGELOG heading.
