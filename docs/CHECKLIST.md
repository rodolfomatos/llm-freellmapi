# Checklist

Pre-release checks for `llm-freellmapi`.

## Code
- [ ] `make lint` passes
- [ ] `make format-check` passes
- [ ] `make test` passes (mocked HTTP only)
- [ ] No secrets, keys or `.env` files staged
- [ ] `llm_freellmapi.py` remains the only source file

## Packaging
- [ ] `make build` produces wheel + sdist without warnings
- [ ] Wheel contains `llm_freellmapi.py`
- [ ] `[project.entry-points.llm] freellmapi = "llm_freellmapi"`
- [ ] `[project.scripts] llm-freellmapi = "llm_freellmapi:main"`

## Functional
- [ ] `llm plugins` lists `llm-freellmapi`
- [ ] `llm freellmapi configure` writes `~/.config/freellmapi/env` with 0600
- [ ] `llm freellmapi status` reports online with a valid key
- [ ] `llm freellmapi models` lists `auto` and provider models
- [ ] `llm -m freellmapi "Hello"` streams a response
- [ ] `llm chat -m freellmapi` keeps context
- [ ] `llm -m freellmapi -o model <id>` pins a model
- [ ] Missing key raises a clear error
- [ ] Wrong key raises a 401 error pointing to `configure`
- [ ] Server offline raises a connection error pointing to `status`

## Docs
- [ ] README installation paths: pip, pipx, venv, source
- [ ] README documents all options and config precedence
- [ ] CHANGELOG updated
- [ ] VERSION bumped in `pyproject.toml`
