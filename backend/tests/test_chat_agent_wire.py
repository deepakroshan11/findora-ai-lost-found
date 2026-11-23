"""
End-to-end over a real HTTP socket: LLMClient -> (mock OpenAI-compatible server) -> agent loop.

No monkeypatching of `requests` here, so this proves the actual wire format
(URL path, auth header, tools payload, tool_calls round-trip) works.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from chat_agent.agent import run_agent
from chat_agent.llm import LLMClient
from chat_agent.tools import ToolBox
from conftest import make_item


class MockProvider(BaseHTTPRequestHandler):
    seen = []                                   # every request body received

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MockProvider.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})

        has_tool_result = any(m["role"] == "tool" for m in body["messages"])
        if not has_tool_result:
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call_abc", "type": "function",
                "function": {"name": "search_items",
                             "arguments": json.dumps({"query": "black wallet", "item_type": "found"})},
            }]}
        else:
            tool_msg = next(m for m in body["messages"] if m["role"] == "tool")
            count = json.loads(tool_msg["content"])["count"]
            message = {"role": "assistant", "content": f"I found {count} matching report(s)."}

        payload = json.dumps({"choices": [{"message": message}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):               # keep test output clean
        pass


@pytest.fixture
def provider():
    MockProvider.seen = []
    server = HTTPServer(("127.0.0.1", 0), MockProvider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_full_agent_round_trip_over_http(provider, db):
    db.get_all_items.return_value = [make_item(item_id="f1", item_type="found", title="Black wallet")]
    llm = LLMClient(api_key="secret-key", base_url=provider, model="mock-model")

    result = run_agent(
        [{"role": "user", "content": "I lost my black wallet"}],
        ToolBox(db, user_id=None),
        llm,
    )

    assert result.reply == "I found 1 matching report(s)."
    assert result.steps == [{"tool": "search_items", "ok": True}]

    first, second = MockProvider.seen
    assert first["path"] == "/v1/chat/completions"
    assert first["auth"] == "Bearer secret-key"
    assert first["body"]["model"] == "mock-model"
    assert {t["function"]["name"] for t in first["body"]["tools"]} == {
        "search_items", "get_my_items", "get_item_matches", "get_stats", "draft_report"
    }
    # round-trip: the tool result was sent back linked to the model's call id
    assert second["body"]["messages"][-1]["role"] == "tool"
    assert second["body"]["messages"][-1]["tool_call_id"] == "call_abc"
