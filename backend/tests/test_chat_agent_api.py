"""POST /api/agent/chat — the HTTP layer around the agent."""
import pytest
from fastapi.testclient import TestClient

import main
from chat_agent.llm import LLMError
from chat_agent.ratelimit import SlidingWindowLimiter
from conftest import make_item
from fake_llm import ScriptedLLM, call, say

client = TestClient(main.app)
URL = "/api/agent/chat"
BODY = {"messages": [{"role": "user", "content": "I lost a black wallet"}]}


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(main, "chat_limiter", SlidingWindowLimiter(max_calls=100, window_seconds=60))


def use_llm(monkeypatch, replies):
    llm = ScriptedLLM(replies)
    monkeypatch.setattr(main, "llm_client", llm)
    return llm


def test_503_when_the_assistant_is_not_configured(monkeypatch):
    monkeypatch.setattr(main, "llm_client", main.LLMClient(api_key=""))
    r = client.post(URL, json=BODY)
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]


def test_happy_path(monkeypatch, db):
    db.get_all_items.return_value = [make_item(item_id="f1", item_type="found", title="Black wallet")]
    use_llm(monkeypatch, [call("search_items", {"query": "black wallet"}), say("Found 1 candidate.")])

    r = client.post(URL, json=BODY)

    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "Found 1 candidate."
    assert body["steps"] == [{"tool": "search_items", "ok": True}]
    assert body["actions"] == []


def test_response_never_contains_contact_details(monkeypatch, db):
    db.get_all_items.return_value = [make_item(item_type="found", contact_info="victim@example.com | +91 90000 00000")]
    use_llm(monkeypatch, [call("search_items", {"query": "black wallet"}), say("Here you go.")])
    text = client.post(URL, json=BODY).text
    assert "victim@example.com" not in text and "90000" not in text


def test_draft_action_is_returned_to_the_frontend(monkeypatch):
    use_llm(monkeypatch, [
        call("draft_report", dict(item_type="lost", title="Black wallet", category="wallet",
                                  description="Black leather wallet with a blue card",
                                  location="Gandhipuram")),
        say("Draft ready."),
    ])
    body = client.post(URL, json=BODY).json()
    assert body["actions"][0]["type"] == "prefill_report"
    assert body["actions"][0]["draft"]["category"] == "wallet"


def test_user_id_scopes_get_my_items(monkeypatch, db):
    db.get_all_items.return_value = [
        make_item(item_id="mine", user_id="user-1"),
        make_item(item_id="theirs", user_id="user-2"),
    ]
    llm = use_llm(monkeypatch, [call("get_my_items", {}), say("You have 1 report.")])
    client.post(URL, json={**BODY, "user_id": "user-1"})
    tool_result = llm.requests[1][-1]["content"]
    assert "mine" in tool_result and "theirs" not in tool_result


def test_guest_gets_a_sign_in_message_from_tools(monkeypatch):
    llm = use_llm(monkeypatch, [call("get_my_items", {}), say("Please sign in.")])
    client.post(URL, json=BODY)            # no user_id
    assert "not signed in" in llm.requests[1][-1]["content"]


def test_400_when_the_last_message_is_not_from_the_user(monkeypatch):
    use_llm(monkeypatch, [])
    r = client.post(URL, json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert r.status_code == 400


def test_422_on_malformed_body(monkeypatch):
    use_llm(monkeypatch, [])
    assert client.post(URL, json={"nope": 1}).status_code == 422


def test_502_when_the_llm_provider_fails(monkeypatch):
    class Broken:
        configured = True

        def chat(self, messages, tools=None):
            raise LLMError("rate limited by the LLM provider")

    monkeypatch.setattr(main, "llm_client", Broken())
    r = client.post(URL, json=BODY)
    assert r.status_code == 502
    assert "rate limited" not in r.text        # provider details are not leaked to the browser


def test_429_when_the_rate_limit_is_hit(monkeypatch):
    monkeypatch.setattr(main, "chat_limiter", SlidingWindowLimiter(max_calls=1, window_seconds=60))
    use_llm(monkeypatch, [say("one"), say("two")])
    assert client.post(URL, json=BODY).status_code == 200
    assert client.post(URL, json=BODY).status_code == 429


def test_rate_limit_is_per_client_ip(monkeypatch):
    monkeypatch.setattr(main, "chat_limiter", SlidingWindowLimiter(max_calls=1, window_seconds=60))
    use_llm(monkeypatch, [say("a"), say("b"), say("c")])
    assert client.post(URL, json=BODY, headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
    assert client.post(URL, json=BODY, headers={"x-forwarded-for": "2.2.2.2"}).status_code == 200
    assert client.post(URL, json=BODY, headers={"x-forwarded-for": "1.1.1.1, 10.0.0.1"}).status_code == 429
