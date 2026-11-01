# SPDX-License-Identifier: AGPL-3.0-or-later
"""Open-weight mode against a tiny fake of an OpenAI-compatible /v1/chat/completions endpoint.

Ollama and vLLM both expose this shape. No model is pulled and nothing leaves the
machine: the fake replays scripted replies and records what the agent sent.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from irysquest.coach import Coach
from irysquest.muse import Muse, MuseError, Provider

MODEL = "muse-glimmer"


class FakeOpenAI:
    """Replays `replies` (assistant messages) in order; records every request body and auth header."""

    def __init__(self):
        self.replies: list[dict | tuple[int, str]] = []
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                fake.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                reply = fake.replies.pop(0)
                if isinstance(reply, tuple):
                    status, text = reply
                    data = text.encode()
                else:
                    status = 200
                    finish = "tool_calls" if reply.get("tool_calls") else "stop"
                    data = json.dumps({
                        "id": f"chatcmpl-{len(fake.requests)}", "object": "chat.completion", "model": body["model"],
                        "choices": [{"index": 0, "message": reply, "finish_reason": finish}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    }).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base_url = f"http://127.0.0.1:{self.srv.server_address[1]}/v1"


@pytest.fixture
def fake():
    f = FakeOpenAI()
    yield f
    f.srv.shutdown()


@pytest.fixture
def muse(fake):
    # Ollama ignores the key, but Muse requires one: the docs say OPEN_API_KEY=ollama.
    return Muse(Provider(name="open", base_url=fake.base_url, model=MODEL, api_key="ollama"))


def tool_call(cid, name, **args):
    # OpenAI-compatible servers send arguments as a JSON string.
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def test_chat_sends_openai_shape_and_returns_content(fake, muse):
    fake.replies.append({"role": "assistant", "content": '{"verdict": "fine"}'})
    out = muse.chat([{"role": "user", "content": "hi"}], temperature=0.2)
    assert out == '{"verdict": "fine"}'
    req = fake.requests[0]
    assert req["path"] == "/v1/chat/completions" and req["auth"] == "Bearer ollama"
    assert req["body"]["model"] == MODEL and req["body"]["temperature"] == 0.2
    assert "tools" not in req["body"]


def test_chat_tools_returns_tool_calls(fake, muse):
    fake.replies.append({"role": "assistant", "content": "", "tool_calls": [tool_call("call_1", "get_quest")]})
    tools = [{"type": "function", "function": {"name": "get_quest", "parameters": {"type": "object", "properties": {}}}}]
    msg = muse.chat_tools([{"role": "user", "content": "look"}], tools)
    assert msg["tool_calls"][0]["function"]["name"] == "get_quest"
    body = fake.requests[0]["body"]
    assert body["tools"] == tools and body["tool_choice"] == "auto"


def test_http_error_becomes_muse_error(fake, muse):
    fake.replies.append((404, '{"error": {"message": "model \\"muse-glimmer\\" not found, try pulling it first"}}'))
    with pytest.raises(MuseError, match="open 404"):
        muse.chat([{"role": "user", "content": "hi"}])


def test_coach_runs_its_tool_loop_on_an_open_host(fake, muse):
    fake.replies += [
        {"role": "assistant", "content": "", "tool_calls": [tool_call("call_a", "get_history", days=14)]},
        {"role": "assistant", "content": "", "tool_calls": [tool_call("call_b", "shrink_step", step="Tighten the front brake cable", minutes=5,
                                                                      reason="One bolt, five minutes.", assumption="a working bike for commuting")]},
    ]
    looked = []
    reads = {"get_history": lambda a: looked.append(a) or {"entries": ["2026-10-20 Bought brake pads (user)"]}}
    d = Coach(muse, reads).decide({"quest_id": "q9", "title": "Fix the bike brake", "days_untouched": 9}, profile="", rules="")

    assert d.move == "shrink_step" and d.args["step"] == "Tighten the front brake cable"
    assert d.assumption == "a working bike for commuting" and d.looked_at == ["get_history"] and d.turns == 2
    assert looked == [{"days": 14}]
    # The second request carries the assistant's tool call and the tool result, linked by id.
    msgs = fake.requests[1]["body"]["messages"]
    assert msgs[-2]["tool_calls"][0]["id"] == "call_a"
    assert msgs[-1] == {"role": "tool", "tool_call_id": "call_a", "content": json.dumps({"entries": ["2026-10-20 Bought brake pads (user)"]})}
    assert all(r["body"]["model"] == MODEL for r in fake.requests)
