import json
import stat

import httpx
import llm
import pytest

import llm_freellmapi as plugin


def _patch_client(monkeypatch, handler):
    real_client = httpx.Client

    def factory(timeout=None):
        return real_client(transport=httpx.MockTransport(handler), timeout=timeout)

    monkeypatch.setattr(plugin, "_http_client", factory)


def _config(**overrides):
    config = {
        "FREELLMAPI_BASE_URL": "http://localhost:3001/v1",
        "FREELLMAPI_API_KEY": "freellmapi-test",
        "FREELLMAPI_MODEL": "auto",
    }
    config.update(overrides)
    return config


def _prompt(llm_model, text="Hello", system=None, **options):
    prompt = llm.Prompt(
        text,
        model=llm_model,
        system=system,
        options=plugin.FreeLLMAPI_Options(**options),
    )
    response = llm.Response(prompt, llm_model, stream=False)
    return prompt, response


# ---------------------------------------------------------------------------
# Registration and configuration
# ---------------------------------------------------------------------------


def test_register_models():
    registered = []
    plugin.register_models(registered.append)

    assert len(registered) == 1
    model = registered[0]
    assert isinstance(model, plugin.FreeLLMAPIModel)
    assert model.model_id == "freellmapi"
    assert model.can_stream is True


def test_normalize_base_url():
    assert plugin.normalize_base_url("http://localhost:3001") == (
        "http://localhost:3001/v1"
    )
    assert plugin.normalize_base_url("http://localhost:3001/v1/") == (
        "http://localhost:3001/v1"
    )
    assert plugin.normalize_base_url("") == plugin.DEFAULT_BASE_URL


def test_load_config_precedence(tmp_path, monkeypatch):
    global_env = tmp_path / "global.env"
    global_env.write_text(
        "FREELLMAPI_API_KEY=global\nFREELLMAPI_BASE_URL=http://global:3001\n",
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("FREELLMAPI_API_KEY=local\n", encoding="utf-8")
    monkeypatch.chdir(project)

    for key in plugin.ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    config = plugin.load_config(env_file=global_env)
    assert config["FREELLMAPI_API_KEY"] == "local"
    assert config["FREELLMAPI_BASE_URL"] == "http://global:3001"

    monkeypatch.setenv("FREELLMAPI_API_KEY", "from-env")
    assert plugin.load_config(env_file=global_env)["FREELLMAPI_API_KEY"] == "from-env"


def test_save_config_permissions(tmp_path):
    path = plugin.save_config(
        "http://localhost:3001",
        "freellmapi-secret",
        model="auto",
        env_file=tmp_path / "freellmapi" / "env",
    )

    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    content = path.read_text(encoding="utf-8")
    assert "FREELLMAPI_BASE_URL=http://localhost:3001/v1" in content
    assert "FREELLMAPI_API_KEY=freellmapi-secret" in content
    assert "FREELLMAPI_MODEL=auto" in content


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def test_fetch_models(monkeypatch):
    def handler(request):
        assert request.url.path == "/v1/models"
        assert request.headers["Authorization"] == "Bearer freellmapi-test"
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": "auto", "object": "model", "owned_by": "freellmapi"},
                    {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
                ],
            },
        )

    _patch_client(monkeypatch, handler)

    models = plugin.fetch_models(_config())

    assert [model["id"] for model in models] == ["auto", "gpt-4o-mini"]


def test_fetch_models_401(monkeypatch):
    def handler(request):
        return httpx.Response(
            401,
            json={
                "error": {"message": "Invalid API key", "type": "authentication_error"}
            },
        )

    _patch_client(monkeypatch, handler)

    with pytest.raises(llm.ModelError) as excinfo:
        plugin.fetch_models(_config())

    message = str(excinfo.value)
    assert "401" in message
    assert "configure" in message
    assert "Invalid API key" in message


def test_fetch_models_connection_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    _patch_client(monkeypatch, handler)

    with pytest.raises(llm.ModelError) as excinfo:
        plugin.fetch_models(_config())

    assert "Could not connect" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Model execution
# ---------------------------------------------------------------------------


def test_execute_non_stream(monkeypatch):
    captured = {}

    def handler(request):
        captured["json"] = json.loads(request.content)
        captured["auth"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "model": "auto",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Olá!"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    monkeypatch.setattr(plugin, "load_config", lambda: _config())
    _patch_client(monkeypatch, handler)

    model = plugin.FreeLLMAPIModel()
    prompt, response = _prompt(model, "Diz olá", system="Responde em português")
    chunks = list(model.execute(prompt, False, response, None))

    assert chunks == ["Olá!"]
    assert captured["auth"] == "Bearer freellmapi-test"
    assert captured["json"]["model"] == "auto"
    assert captured["json"]["stream"] is False
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "Responde em português"},
        {"role": "user", "content": "Diz olá"},
    ]
    assert response.response_json["id"] == "chatcmpl-1"


def test_execute_stream_and_options(monkeypatch):
    captured = {}

    def handler(request):
        captured["json"] = json.loads(request.content)
        body = (
            'data: {"choices":[{"delta":{"content":"Ol"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"á"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            200,
            content=body.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    monkeypatch.setattr(plugin, "load_config", lambda: _config())
    _patch_client(monkeypatch, handler)

    model = plugin.FreeLLMAPIModel()
    prompt, response = _prompt(
        model,
        "Diz olá",
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=64,
    )
    response.stream = True
    chunks = list(model.execute(prompt, True, response, None))

    assert "".join(chunks) == "Olá"
    assert captured["json"]["model"] == "gpt-4o-mini"
    assert captured["json"]["temperature"] == 0.2
    assert captured["json"]["max_tokens"] == 64
    assert captured["json"]["stream"] is True


def test_execute_stream_401_reports_server_error(monkeypatch):
    def handler(request):
        return httpx.Response(
            401,
            json={"error": {"message": "Invalid API key"}},
            headers={"content-type": "application/json"},
        )

    monkeypatch.setattr(plugin, "load_config", lambda: _config())
    _patch_client(monkeypatch, handler)

    model = plugin.FreeLLMAPIModel()
    prompt, response = _prompt(model)
    response.stream = True

    with pytest.raises(llm.ModelError) as excinfo:
        list(model.execute(prompt, True, response, None))

    message = str(excinfo.value)
    assert "401" in message
    assert "Invalid API key" in message
    assert "streaming response" not in message


def test_execute_requires_key(monkeypatch):
    monkeypatch.setattr(plugin, "load_config", dict)
    monkeypatch.setattr(plugin, "resolve_api_key", lambda config: None)

    model = plugin.FreeLLMAPIModel()
    prompt, response = _prompt(model)

    with pytest.raises(llm.NeedsKeyException):
        list(model.execute(prompt, False, response, None))
