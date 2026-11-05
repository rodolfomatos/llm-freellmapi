.PHONY: help setup install dev-install pipx-setup ubuntu-setup configure \
        test lint format format-check pre-commit build check doctor \
        metrics clean

# Variables
PIP ?= python3 -m pip
LLM ?= llm
PYTHON ?= python3
SOURCE = llm_freellmapi.py

help:
	@echo "llm-freellmapi — Makefile"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          Install in editable mode with dev dependencies"
	@echo "  make configure      Interactive setup (base URL, key, model)"
	@echo "  make install        Install package in production mode"
	@echo "  make dev-install    Install package in editable mode"
	@echo ""
	@echo "pipx / Ubuntu (PEP 668):"
	@echo "  make pipx-setup     Inject plugin into the pipx llm venv"
	@echo "  make ubuntu-setup   Show distribution-specific instructions"
	@echo ""
	@echo "Usage:"
	@echo "  make check          Verify plugin registration and configuration"
	@echo ""
	@echo "Quality:"
	@echo "  make test           Run the test suite"
	@echo "  make lint           Run ruff linter"
	@echo "  make format         Run ruff formatter"
	@echo "  make format-check   Verify formatting without changing files"
	@echo "  make pre-commit     Lint + format check + build"
	@echo "  make build          Build wheel and sdist"
	@echo ""
	@echo "Diagnostics:"
	@echo "  make doctor         Check environment, plugin and config"
	@echo "  make metrics        Show project metrics"
	@echo ""
	@echo "Housekeeping:"
	@echo "  make clean          Remove build artifacts"

setup:
	@echo "Setting up development environment..."
	$(PIP) install -e ".[dev]"

install:
	@echo "Installing llm-freellmapi..."
	$(PIP) install .

dev-install:
	@echo "Installing llm-freellmapi in development mode..."
	$(PIP) install -e .

pipx-setup:
	@echo "Injecting plugin into the pipx llm venv..."
	pipx inject llm .

ubuntu-setup:
	@echo "Ubuntu/Debian (PEP 668) blocks system-wide pip installs. Choose one:"
	@echo ""
	@echo "Option 1 — pipx (recommended if llm is installed with pipx):"
	@echo "  pipx install llm"
	@echo "  pipx inject llm llm-freellmapi"
	@echo ""
	@echo "Option 2 — virtual environment:"
	@echo "  python3 -m venv venv"
	@echo "  source venv/bin/activate"
	@echo "  pip install llm llm-freellmapi"
	@echo ""
	@echo "Then run: llm freellmapi configure"

configure:
	@if command -v $(LLM) >/dev/null 2>&1; then \
		$(LLM) freellmapi configure; \
	else \
		$(PYTHON) -m llm_freellmapi; \
	fi

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	@echo "Running ruff linter..."
	ruff check $(SOURCE) tests/

format:
	@echo "Running ruff formatter..."
	ruff format $(SOURCE) tests/

format-check:
	@echo "Checking formatting..."
	ruff format --check $(SOURCE) tests/

pre-commit: lint format-check build

build:
	@echo "Building distribution files..."
	$(PYTHON) -m build

check:
	@echo "--- Installation ---"
	@$(LLM) plugins 2>/dev/null | grep -q freellmapi \
		&& echo "  [OK] Plugin registered in llm" \
		|| echo "  [FAIL] Plugin not found (run: pip install llm-freellmapi)"
	@echo ""
	@echo "--- Configuration ---"
	@if [ -n "$$FREELLMAPI_API_KEY" ]; then \
		echo "  [OK] FREELLMAPI_API_KEY is set"; \
	elif [ -f "$$HOME/.config/freellmapi/env" ]; then \
		echo "  [OK] ~/.config/freellmapi/env exists"; \
	else \
		echo "  [WARN] No config found (run: llm freellmapi configure)"; \
	fi
	@echo ""
	@echo "--- Server ---"
	@$(LLM) freellmapi status 2>/dev/null || echo "  [WARN] Server not reachable"
	@echo ""
	@echo "--- Usage ---"
	@echo '  llm -m freellmapi "Your question"'
	@echo "  llm chat -m freellmapi"
	@echo "  (set as default: llm models default freellmapi)"

doctor:
	@echo "=== Environment ==="
	@echo "Python: $$($(PYTHON) --version 2>&1)"
	@echo "Pip:    $$($(PIP) --version 2>&1 | cut -d' ' -f1-2)"
	@echo "LLM:    $$($(LLM) --version 2>&1)"
	@echo ""
	@echo "=== Installed Packages ==="
	$(PIP) list 2>/dev/null | grep -i -e llm -e httpx -e freellmapi || true
	@echo ""
	@echo "=== Plugin Registration ==="
	@$(LLM) plugins 2>/dev/null | grep -A2 freellmapi || echo "  Plugin not found"
	@echo ""
	@echo "=== Config Files ==="
	@for f in ./.env ~/.config/freellmapi/env; do \
		if [ -f "$$f" ]; then \
			echo "  [OK] $$f"; \
		else \
			echo "  [--] $$f (not found)"; \
		fi; \
	done
	@echo ""
	@echo "=== llm Keys ==="
	@$(LLM) keys list 2>/dev/null | grep freellmapi || echo "  No freellmapi key set"

metrics:
	@echo "--- Project Metrics ---"
	@echo "Source lines: $$(wc -l < $(SOURCE))"
	@echo "  - Functions: $$(grep -c '^def ' $(SOURCE))"
	@echo "  - Classes:   $$(grep -c '^class ' $(SOURCE))"
	@echo ""
	@echo "Tests:      $$(grep -c '^def test_' tests/*.py 2>/dev/null | awk -F: '{s+=$$2} END {print s+0}')"
	@echo "Doc files:  $$(ls docs/*.md 2>/dev/null | wc -l)"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
