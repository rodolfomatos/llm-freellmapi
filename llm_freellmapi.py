"""LLM plugin for FreeLLMAPI.

FreeLLMAPI aggregates dozens of free LLM providers behind a single
OpenAI-compatible endpoint. This plugin lets the `llm` CLI talk to that
endpoint as if it were any other model.

Install:
    llm install llm-freellmapi

Configure:
    llm freellmapi configure

Use:
    llm -m freellmapi "your prompt"
    llm freellmapi models
    llm freellmapi status
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import click
import httpx
import llm
from llm import hookimpl
from pydantic import Field

DEFAULT_BASE_URL = "http://localhost:3001/v1"
DEFAULT_MODEL = "auto"
PLUGIN_NAME = "freellmapi"

CONFIG_DIR = Path.home() / ".config" / "freellmapi"
ENV_FILE = CONFIG_DIR / "env"

ENV_KEYS = (
    "FREELLMAPI_BASE_URL",
    "FREELLMAPI_API_KEY",
    "FREELLMAPI_MODEL",
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _read_env_file(path: Path, config: dict[str, str]) -> None:
    """Merge KEY=VALUE pairs from a dotenv-style file into ``config``."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            config[key] = value


def load_config(env_file: Path | None = None) -> dict[str, str]:
    """Load configuration.

    Precedence (highest wins):
    1. Process environment variables
    2. ``./.env`` in the current directory
    3. ``~/.config/freellmapi/env`` (or ``env_file`` when supplied)
    """
    config: dict[str, str] = {}
    _read_env_file(Path(env_file) if env_file else ENV_FILE, config)

    local_env = Path.cwd() / ".env"
    if local_env != (Path(env_file) if env_file else ENV_FILE):
        _read_env_file(local_env, config)

    for key in ENV_KEYS:
        value = os.environ.get(key)
        if value:
            config[key] = value

    return config


def resolve_api_key(config: dict[str, str]) -> str | None:
    """Return the unified API key from config, env or ``llm keys``."""
    key = config.get("FREELLMAPI_API_KEY")
    if key:
        return key
    return llm.get_key(key_alias=PLUGIN_NAME, env_var="FREELLMAPI_API_KEY")


def normalize_base_url(url: str) -> str:
    """Return a base URL ending in ``/v1`` and without a trailing slash."""
    url = (url or DEFAULT_BASE_URL).strip().rstrip("/")
    if not url:
        url = DEFAULT_BASE_URL
    if not url.endswith("/v1"):
        url += "/v1"
    return url


def save_config(
    base_url: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    env_file: Path | None = None,
) -> Path:
    """Write the configuration file with 0600 permissions."""
    path = Path(env_file) if env_file else ENV_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# FreeLLMAPI configuration — used by llm-freellmapi\n"
        f"FREELLMAPI_BASE_URL={normalize_base_url(base_url)}\n"
        f"FREELLMAPI_API_KEY={api_key}\n"
        f"FREELLMAPI_MODEL={model or DEFAULT_MODEL}\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _http_client(timeout: float = 10.0) -> httpx.Client:
    """Create the HTTP client used for all requests (patched in tests)."""
    return httpx.Client(timeout=timeout)


def _auth_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _error_detail(response: httpx.Response) -> str:
    try:
        if not getattr(response, "is_stream_consumed", True):
            response.read()
        payload = response.json()
    except (ValueError, httpx.HTTPError):
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "")
    if isinstance(error, str):
        return error
    detail = payload.get("detail")
    return str(detail) if detail else ""


def _raise_for_status(exc: httpx.HTTPStatusError, base_url: str) -> None:
    status = exc.response.status_code
    detail = _error_detail(exc.response)
    if status == 401:
        message = (
            "FreeLLMAPI rejected the API key (401). "
            "Run 'llm freellmapi configure' or set FREELLMAPI_API_KEY."
        )
    elif status == 404:
        message = (
            "FreeLLMAPI returned 404. Check FREELLMAPI_BASE_URL "
            f"({base_url}) and the model id."
        )
    elif status == 429:
        message = "FreeLLMAPI is rate limited (429). Try again shortly."
    else:
        message = f"FreeLLMAPI returned HTTP {status}."
    if detail:
        message = f"{message} Server said: {detail}"
    raise llm.ModelError(message) from exc


def _transport_error(exc: Exception, base_url: str) -> llm.ModelError:
    if isinstance(exc, httpx.TimeoutException):
        message = f"FreeLLMAPI timed out while contacting {base_url}."
    else:
        message = (
            f"Could not connect to FreeLLMAPI at {base_url}. "
            "Is the server running? Check with 'llm freellmapi status'."
        )
    return llm.ModelError(message)


def fetch_models(
    config: dict[str, str] | None = None,
    available: bool = False,
) -> list[dict[str, Any]]:
    """Fetch the model catalog from ``/v1/models``."""
    config = load_config() if config is None else config
    base_url = normalize_base_url(config.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL))
    api_key = resolve_api_key(config)
    url = f"{base_url}/models"
    params = {"available": "true"} if available else None

    try:
        with _http_client(timeout=10.0) as client:
            response = client.get(url, headers=_auth_headers(api_key), params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        _raise_for_status(exc, base_url)
        raise  # pragma: no cover - _raise_for_status always raises
    except httpx.HTTPError as exc:
        raise _transport_error(exc, base_url) from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, list) else []


def fetch_status(config: dict[str, str] | None = None) -> dict[str, Any]:
    """Return a small status report for the configured server."""
    config = load_config() if config is None else config
    base_url = normalize_base_url(config.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL))
    api_key = resolve_api_key(config)
    models = fetch_models(config)
    return {
        "base_url": base_url,
        "has_key": bool(api_key),
        "model_count": len(models),
        "models": models,
    }


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


@hookimpl
def register_models(register):
    """Register the FreeLLMAPI model with the llm CLI."""
    register(FreeLLMAPIModel())


@hookimpl
def register_commands(cli):
    """Register ``llm freellmapi ...`` subcommands."""

    @cli.group(name=PLUGIN_NAME)
    def freellmapi_group():
        """FreeLLMAPI commands."""

    @freellmapi_group.command(name="configure")
    @click.option("--base-url", default=None, help="FreeLLMAPI base URL.")
    @click.option("--api-key", default=None, help="Unified FreeLLMAPI API key.")
    @click.option("--model", default=None, help="Default model id (default: auto).")
    def configure_command(base_url, api_key, model):
        """Configure the FreeLLMAPI endpoint and API key."""
        configure(base_url=base_url, api_key=api_key, model=model)

    @freellmapi_group.command(name="models")
    @click.option(
        "--available",
        is_flag=True,
        help="Only show models that can serve a request right now.",
    )
    @click.option("--json", "as_json", is_flag=True, help="Print raw JSON.")
    def models_command(available, as_json):
        """List models exposed by the FreeLLMAPI server."""
        list_models(available=available, as_json=as_json)

    @freellmapi_group.command(name="status")
    def status_command():
        """Check whether the FreeLLMAPI server is reachable."""
        check_status()


# ---------------------------------------------------------------------------
# Commands (also used by the standalone llm-freellmapi script)
# ---------------------------------------------------------------------------


def configure(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    """Interactively (or non-interactively) write the config file."""
    existing = load_config()
    interactive = base_url is None and api_key is None and model is None

    if base_url is None:
        base_url = (
            click.prompt(
                "FreeLLMAPI base URL",
                default=existing.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL),
            )
            if interactive
            else existing.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL)
        )

    if api_key is None:
        api_key = (
            click.prompt(
                "Unified API key (dashboard > Keys)",
                default=existing.get("FREELLMAPI_API_KEY", ""),
                hide_input=True,
                show_default=False,
            )
            if interactive
            else existing.get("FREELLMAPI_API_KEY", "")
        )

    if model is None:
        model = (
            click.prompt(
                "Default model id",
                default=existing.get("FREELLMAPI_MODEL", DEFAULT_MODEL),
            )
            if interactive
            else existing.get("FREELLMAPI_MODEL", DEFAULT_MODEL)
        )

    base_url = normalize_base_url(base_url)
    if not api_key:
        raise click.ClickException(
            "An API key is required. Copy the unified key from the FreeLLMAPI "
            "dashboard (http://localhost:3001 > Keys)."
        )

    path = save_config(base_url, api_key, model)
    click.echo(f"[OK] Configuration written to {path}")
    click.echo(f"     Base URL: {base_url}")
    click.echo(f"     Model:    {model or DEFAULT_MODEL}")

    # Validate immediately, but never fail the command on an offline server.
    try:
        models = fetch_models(
            {"FREELLMAPI_BASE_URL": base_url, "FREELLMAPI_API_KEY": api_key}
        )
        click.echo(f"[OK] Server reachable — {len(models)} model(s) available")
    except llm.ModelError as exc:
        click.echo(f"[WARN] Could not validate the server: {exc}")

    click.echo("")
    click.echo("Try it now:")
    click.echo('  llm -m freellmapi "Hello!"')
    click.echo("")
    click.echo("Optional — make it the default model:")
    click.echo("  llm models default freellmapi")


def list_models(available: bool = False, as_json: bool = False) -> None:
    """Print the model catalog."""
    config = load_config()
    try:
        models = fetch_models(config, available=available)
    except llm.ModelError as exc:
        raise click.ClickException(str(exc)) from exc

    if as_json:
        click.echo(json.dumps(models, indent=2))
        return

    base_url = normalize_base_url(config.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL))
    if not models:
        click.echo("No models returned by the server.")
        return

    click.echo(f"Models available at {base_url}:")
    for model in models:
        model_id = model.get("id", "unknown")
        owned_by = model.get("owned_by")
        suffix = f"  ({owned_by})" if owned_by else ""
        click.echo(f"  - {model_id}{suffix}")
    click.echo("")
    click.echo(f"Total: {len(models)} model(s)")
    click.echo("Use a specific model with: llm -m freellmapi -o model <model-id> ...")


def check_status() -> None:
    """Report whether the server is reachable and the key is valid."""
    config = load_config()
    base_url = normalize_base_url(config.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL))

    if not resolve_api_key(config):
        click.echo("[WARN] No API key configured. Run 'llm freellmapi configure'.")
        click.echo(f"       Base URL: {base_url}")
        raise click.ClickException("FreeLLMAPI key is not configured")

    try:
        models = fetch_models(config)
    except llm.ModelError as exc:
        click.echo(f"[FAIL] {exc}")
        raise click.ClickException("FreeLLMAPI status check failed") from exc

    click.echo("[OK] FreeLLMAPI server is online")
    click.echo(f"     Base URL: {base_url}")
    click.echo(f"     Models:   {len(models)}")
    click.echo(f"     Default:  {config.get('FREELLMAPI_MODEL', DEFAULT_MODEL)}")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class FreeLLMAPI_Options(llm.Options):
    model: str | None = Field(
        default=None,
        description=(
            "FreeLLMAPI model id for this request. Defaults to FREELLMAPI_MODEL "
            "or 'auto', which lets the server pick an available free model."
        ),
    )
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Sampling temperature, between 0 and 2.",
    )
    max_tokens: int | None = Field(
        default=None,
        description="Maximum number of tokens to generate.",
    )
    top_p: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Nucleus sampling probability mass.",
    )
    frequency_penalty: float | None = Field(
        default=None,
        ge=-2,
        le=2,
        description="Penalize tokens by their frequency in the text so far.",
    )
    presence_penalty: float | None = Field(
        default=None,
        ge=-2,
        le=2,
        description="Penalize tokens that have already appeared.",
    )


def _text_from_message(message: Any) -> str | None:
    """Flatten an llm Message into plain text for the OpenAI wire format."""
    bits = []
    for part in getattr(message, "parts", []):
        text = getattr(part, "text", None)
        if text:
            bits.append(text)
    if bits:
        return "".join(bits)
    if getattr(message, "role", None) == "assistant":
        return ""
    return None


def build_messages(prompt: Any) -> list[dict[str, Any]]:
    """Translate ``prompt.messages`` into OpenAI chat messages."""
    messages: list[dict[str, Any]] = []
    for message in prompt.messages:
        role = getattr(message, "role", None)
        if role not in ("system", "user", "assistant", "tool"):
            continue
        content = _text_from_message(message)
        if content is None:
            continue
        messages.append({"role": role, "content": content})
    return messages


class FreeLLMAPIModel(llm.Model):
    """FreeLLMAPI model — routed through its OpenAI-compatible endpoint."""

    model_id = PLUGIN_NAME
    can_stream = True
    supports_conversation = True

    Options = FreeLLMAPI_Options

    def execute(
        self,
        prompt: llm.Prompt,
        stream: bool,
        response: llm.Response,
        conversation: llm.Conversation | None = None,
    ) -> Iterator[str]:
        config = load_config()
        base_url = normalize_base_url(
            config.get("FREELLMAPI_BASE_URL", DEFAULT_BASE_URL)
        )
        api_key = resolve_api_key(config)

        if not api_key:
            raise llm.NeedsKeyException(
                "No FreeLLMAPI API key found. Run 'llm freellmapi configure' or "
                "set FREELLMAPI_API_KEY."
            )

        model_name = (
            getattr(prompt.options, "model", None)
            or config.get("FREELLMAPI_MODEL")
            or DEFAULT_MODEL
        )

        messages = build_messages(prompt)
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": bool(stream),
        }
        for option in (
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
        ):
            value = getattr(prompt.options, option, None)
            if value is not None:
                payload[option] = value

        url = f"{base_url}/chat/completions"
        headers = _auth_headers(api_key)

        try:
            with _http_client(timeout=None if stream else 120.0) as client:
                if stream:
                    with client.stream(
                        "POST", url, json=payload, headers=headers
                    ) as resp:
                        try:
                            resp.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            _raise_for_status(exc, base_url)
                        for line in resp.iter_lines():
                            if not line:
                                continue
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            choices = chunk.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content")
                            if content:
                                yield content
                else:
                    resp = client.post(url, json=payload, headers=headers)
                    try:
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        _raise_for_status(exc, base_url)
                    data = resp.json()
                    response.response_json = data
                    choices = data.get("choices") or []
                    if choices:
                        content = (choices[0].get("message") or {}).get("content")
                        if content:
                            yield content
        except httpx.HTTPStatusError as exc:
            # Raised by raise_for_status on paths not wrapped above.
            _raise_for_status(exc, base_url)
        except httpx.HTTPError as exc:
            raise _transport_error(exc, base_url) from exc

        response._prompt_json = {"messages": messages, "model": model_name}


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the ``llm-freellmapi`` console script."""
    command = sys.argv[1] if len(sys.argv) > 1 else "configure"
    if command in ("configure", "setup"):
        configure()
    elif command == "models":
        list_models(available="--available" in sys.argv)
    elif command == "status":
        check_status()
    elif command in ("-h", "--help", "help"):
        print("Usage: llm-freellmapi [configure|models|status]")
    else:
        print(f"Unknown command: {command}")
        print("Usage: llm-freellmapi [configure|models|status]")
        sys.exit(1)


if __name__ == "__main__":
    main()
