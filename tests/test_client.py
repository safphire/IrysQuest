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
