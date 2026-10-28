# SPDX-License-Identifier: AGPL-3.0-or-later
"""The agent loop against the fake server and a scripted Muse: no network, no API key."""

import json
import time

import pytest

from irysquest import context as ctx_store
from irysquest import oauth
from irysquest.agent import WHY_STEP, Agent
from irysquest.mcp_client import QuestClient
from irysquest.muse import Breakdown, CapturedQuest

from . import fake_server


class ScriptedMuse:
    """Returns canned breakdowns; records what it was asked."""

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def breakdown(self, **kw):
        self.calls.append(kw)
        return self.replies.pop(0)

    def capture_text(self, dump, profile):
        return [CapturedQuest(title=t.strip(), next_step="Open it") for t in dump.split(",") if t.strip()]


@pytest.fixture
def world(tmp_path):
    srv, url = fake_server.start()
    fake_server.PROPOSALS.clear()
    fake_server.QUESTS[0]["touched_at"] = "2026-10-01T08:00:00"   # q1 stalled
    fake_server.QUESTS[1]["touched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")  # q2 fresh
    tf = tmp_path / "tokens.json"
    oauth.save_tokens(tf, oauth.Tokens("c", f"{url}/oauth/token", fake_server.TOKEN, "r", time.time() + 3600))
    client = QuestClient(f"{url}/mcp", tf)
    client.initialize()
    yield client, tmp_path / "context.json"
    srv.shutdown()


def test_dig_proposes_once_and_remembers(world):
    client, cf = world
    muse = ScriptedMuse([Breakdown("Hum one scale", 3, "Tiny start.", assumption="learning to sing")])
    ag = Agent(client, muse, cf, stall_days=3)
    res = ag.dig()
    assert [r.outcome for r in res] == ["proposed"]
    assert fake_server.PROPOSALS[-1]["payload"]["text"] == "Hum one scale"
    assert "assuming this is learning to sing" in fake_server.PROPOSALS[-1]["payload"]["reason"]
    saved = ctx_store.load(cf)
    assert saved.quests["q1"].assumption == "learning to sing"
    # second run: proposal is pending, so nothing is re-proposed and Muse isn't asked
    res2 = Agent(client, muse, cf, stall_days=3).dig()
    assert res2 == [] and len(muse.calls) == 1


def test_dig_asks_for_why_when_purpose_is_unclear(world):
    client, cf = world
    muse = ScriptedMuse([Breakdown("Guess", 5, "?", assumption="", needs_why=True)])
    res = Agent(client, muse, cf, stall_days=3).dig()
    assert res[0].step == WHY_STEP and res[0].minutes == 2
    assert ctx_store.load(cf).quests["q1"].asked_for_why is True


def test_dry_run_and_profile_reach_muse(world):
    client, cf = world
    ctx = ctx_store.Context(profile="Solo dev, evenings only, 'small' means 5 minutes.")
    ctx_store.save(cf, ctx)
    muse = ScriptedMuse([Breakdown("Open the file", 2, "Just open it.", assumption="x")])
    res = Agent(client, muse, cf, stall_days=3).dig(dry_run=True)
    assert res[0].outcome == "dry-run" and fake_server.PROPOSALS == []
    assert "evenings only" in muse.calls[0]["profile"]


def test_capture_preview_proposes_nothing(world):
    client, cf = world
    ag = Agent(client, ScriptedMuse([]), cf, stall_days=3)
    rows = ag.capture(ag.muse.capture_text("fix the bike, call mom", ""), source="notes", preview=True)
    assert [r["outcome"] for r in rows] == ["preview", "preview"] and fake_server.PROPOSALS == []
    rows = ag.capture(ag.muse.capture_text("fix the bike", ""), source="notes")
    assert rows[0]["outcome"] == "proposed" and fake_server.PROPOSALS[-1]["op"] == "propose_add_quest"
    assert fake_server.PROPOSALS[-1]["payload"]["track"] is False
