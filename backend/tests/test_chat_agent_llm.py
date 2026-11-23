import pytest
import requests

from chat_agent import llm as llm_module
from chat_agent.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LLMClient, LLMError


class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code = status
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def ok(message):
    return FakeResponse(200, {"choices": [{"message": message}]})


@pytest.fixture
def client():
    return LLMClient(api_key="test-key", base_url="https://llm.example/v1/", model="test-model")


def test_returns_the_assistant_message(client, monkeypatch):
    monkeypatch.setattr(llm_module.requests, "post", lambda *a, **k: ok({"role": "assistant", "content": "hi"}))
    assert client.chat([{"role": "user", "content": "hello"}])["content"] == "hi"


def test_request_shape(client, monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, json=json, timeout=timeout)
        return ok({"content": "x"})

    monkeypatch.setattr(llm_module.requests, "post", fake_post)
    tools = [{"type": "function", "function": {"name": "t"}}]
    client.chat([{"role": "user", "content": "hello"}], tools=tools)

    assert seen["url"] == "https://llm.example/v1/chat/completions"   # trailing slash handled
    assert seen["headers"]["Authorization"] == "Bearer test-key"
    assert seen["json"]["model"] == "test-model"
    assert seen["json"]["tools"] == tools and seen["json"]["tool_choice"] == "auto"
    assert seen["timeout"] == 30


def test_no_tools_key_when_none_given(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(llm_module.requests, "post",
                        lambda url, headers, json, timeout: seen.update(json=json) or ok({"content": "x"}))
    client.chat([{"role": "user", "content": "hello"}])
    assert "tools" not in seen["json"]


def test_not_configured_raises_without_any_network_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not call the network")

    monkeypatch.setattr(llm_module.requests, "post", boom)
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        LLMClient(api_key="").chat([])


def test_rate_limit_is_a_clear_error(client, monkeypatch):
    monkeypatch.setattr(llm_module.requests, "post", lambda *a, **k: FakeResponse(429))
    with pytest.raises(LLMError, match="rate limited"):
        client.chat([])


def test_http_errors_are_wrapped(client, monkeypatch):
    monkeypatch.setattr(llm_module.requests, "post", lambda *a, **k: FakeResponse(500, text="boom"))
    with pytest.raises(LLMError, match="HTTP 500"):
        client.chat([])


def test_network_errors_are_wrapped(client, monkeypatch):
    def fail(*a, **k):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(llm_module.requests, "post", fail)
    with pytest.raises(LLMError, match="network error"):
        client.chat([])


@pytest.mark.parametrize("response", [
    FakeResponse(200, None),                         # not JSON
    FakeResponse(200, {"choices": []}),              # no choices
    FakeResponse(200, {"unexpected": True}),         # wrong shape
])
def test_malformed_responses_are_wrapped(client, monkeypatch, response):
    monkeypatch.setattr(llm_module.requests, "post", lambda *a, **k: response)
    with pytest.raises(LLMError, match="unexpected response"):
        client.chat([])


def test_defaults_and_env_configuration(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    default = LLMClient()
    assert not default.configured
    assert default.base_url == DEFAULT_BASE_URL and default.model == DEFAULT_MODEL

    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setenv("LLM_MODEL", "some-gemini-model")
    configured = LLMClient()
    assert configured.configured
    assert configured.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert configured.model == "some-gemini-model"
