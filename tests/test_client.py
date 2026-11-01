# SPDX-License-Identifier: AGPL-3.0-or-later
import time

import pytest

from irysquest import oauth
from irysquest.mcp_client import QuestClient, ToolError

from . import fake_server


@pytest.fixture
def client(tmp_path):
    srv, url = fake_server.start()
    tf = tmp_path / "tokens.json"
    oauth.save_tokens(tf, oauth.Tokens("c", f"{url}/oauth/token", fake_server.TOKEN, "r", time.time() + 3600))
    c = QuestClient(f"{url}/mcp", tf)
    c.initialize()
    yield c
    srv.shutdown()


def test_reads(client):
    today = client.get_today()
    assert today["slot_cap"] == 5
    assert [q["id"] for q in today["tracked"]] == ["q1", "q2"]
    assert len(client.list_quests()["quests"]) == 3
    assert client.get_quest("q1")["title"] == "Learn to sing"


def test_proposals_never_mutate(client):
    before = client.get_quest("q1")["next_step"]["text"]
    p = client.propose_set_next_step("q1", "Hum one scale, 2 minutes", reason="Untouched for 7 days.")
    assert p["status"] == "pending"
    assert client.get_quest("q1")["next_step"]["text"] == before
    assert client.list_proposals()["proposals"][-1]["id"] == p["id"]


def test_tool_errors_surface(client):
    with pytest.raises(ToolError):
        client.get_quest("nope")


@pytest.mark.parametrize("status, body, says", [
    (400, b'{"error": "invalid_grant"}', "Session expired"),
    (404, b"<html>ERR_NGROK_3200</html>", "Server unreachable (404)"),
    (502, b'{"error": "bad_gateway"}', "Server unreachable (502)"),
    (None, b"", "Server unreachable (ConnectError)"),
])
def test_refresh_failure_says_expired_only_for_invalid_grant(tmp_path, status, body, says):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Token(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))   # drain, or Windows may reset the socket
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Token)
    url = f"http://127.0.0.1:{srv.server_address[1]}/oauth/token"
    if status is None:
        srv.server_close()          # nothing listening: connection refused
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    tf = tmp_path / "tokens.json"
    tokens = oauth.Tokens("c", url, "a", "r", time.time() - 1)
    oauth.save_tokens(tf, tokens)
    try:
        with pytest.raises(SystemExit, match=says.replace("(", r"\(").replace(")", r"\)")):
            oauth.refresh(tokens, tf)
    finally:
        if status is not None:
            srv.shutdown()
    assert oauth.load_tokens(tf).refresh_token == "r"   # nothing lost
