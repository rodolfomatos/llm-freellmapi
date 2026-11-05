import click
from click.testing import CliRunner

import llm_freellmapi as plugin


def _cli():
    @click.group()
    def cli():
        pass

    plugin.register_commands(cli)
    return cli


def test_commands_registered():
    runner = CliRunner()
    result = runner.invoke(_cli(), ["freellmapi", "--help"])

    assert result.exit_code == 0
    assert "configure" in result.output
    assert "models" in result.output
    assert "status" in result.output


def test_models_command(monkeypatch):
    monkeypatch.setattr(plugin, "load_config", dict)
    monkeypatch.setattr(
        plugin,
        "fetch_models",
        lambda config=None, available=False: [
            {"id": "auto", "owned_by": "freellmapi"},
            {"id": "gpt-4o-mini", "owned_by": "openai"},
        ],
    )

    result = CliRunner().invoke(_cli(), ["freellmapi", "models"])

    assert result.exit_code == 0
    assert "auto" in result.output
    assert "gpt-4o-mini" in result.output
    assert "Total: 2 model(s)" in result.output


def test_models_command_json(monkeypatch):
    monkeypatch.setattr(plugin, "load_config", dict)
    monkeypatch.setattr(
        plugin,
        "fetch_models",
        lambda config=None, available=False: [{"id": "auto"}],
    )

    result = CliRunner().invoke(_cli(), ["freellmapi", "models", "--json"])

    assert result.exit_code == 0
    assert '"id": "auto"' in result.output


def test_status_command(monkeypatch, tmp_path):
    monkeypatch.setattr(plugin, "ENV_FILE", tmp_path / "env")
    monkeypatch.setattr(
        plugin,
        "load_config",
        lambda: {
            "FREELLMAPI_BASE_URL": "http://localhost:3001/v1",
            "FREELLMAPI_API_KEY": "key",
            "FREELLMAPI_MODEL": "auto",
        },
    )
    monkeypatch.setattr(
        plugin,
        "fetch_models",
        lambda config=None, available=False: [{"id": "auto"}],
    )

    result = CliRunner().invoke(_cli(), ["freellmapi", "status"])

    assert result.exit_code == 0
    assert "server is online" in result.output
    assert "Models:   1" in result.output


def test_status_without_key(monkeypatch):
    monkeypatch.setattr(plugin, "load_config", dict)
    monkeypatch.setattr(plugin, "resolve_api_key", lambda config: None)

    result = CliRunner().invoke(_cli(), ["freellmapi", "status"])

    assert result.exit_code != 0
    assert "No API key configured" in result.output


def test_configure_non_interactive(monkeypatch, tmp_path):
    env_file = tmp_path / "env"
    monkeypatch.setattr(plugin, "ENV_FILE", env_file)
    monkeypatch.setattr(plugin, "load_config", lambda **kwargs: {})
    monkeypatch.setattr(
        plugin,
        "fetch_models",
        lambda config=None, available=False: [{"id": "auto"}],
    )

    result = CliRunner().invoke(
        _cli(),
        [
            "freellmapi",
            "configure",
            "--base-url",
            "http://localhost:3001",
            "--api-key",
            "freellmapi-secret",
            "--model",
            "auto",
        ],
    )

    assert result.exit_code == 0
    assert env_file.is_file()
    assert "Configuration written" in result.output
    assert "Server reachable" in result.output
    assert "FREELLMAPI_API_KEY=freellmapi-secret" in env_file.read_text()
