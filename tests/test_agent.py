# SPDX-License-Identifier: AGPL-3.0-or-later
"""The agent loop against the fake server and a scripted, tool-calling Muse: no network, no API key."""

import json
import time

import pytest

from irysquest import context as ctx_store
from irysquest import oauth
from irysquest.agent import WHY_STEP, Agent
from irysquest.mcp_client import QuestClient
from irysquest.muse import CapturedQuest

from . import fake_server


def call(name, **args):
    return {"id": f"c_{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class ScriptedMuse:
    """Each entry in `turns` is the assistant message returned for one chat_tools call."""

    def __init__(self, turns):
        self.turns, self.calls = list(turns), []

    def chat_tools(self, messages, tools, temperature=0.3):
        self.calls.append(messages)
        return self.turns.pop(0)

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


def test_coach_looks_then_shrinks_and_remembers(world):
    client, cf = world
    muse = ScriptedMuse([
        {"role": "assistant", "content": None, "tool_calls": [call("get_history", days=14)]},
        {"role": "assistant", "content": None, "tool_calls": [call("shrink_step", step="Hum one scale", minutes=3, reason="Tiny start.", assumption="learning to sing")]},
    ])
    res = Agent(client, muse, cf, stall_days=3).dig()
    assert [(r.move, r.outcome) for r in res] == [("shrink_step", "proposed")]
    assert fake_server.PROPOSALS[-1]["payload"]["text"] == "Hum one scale"
    assert "assuming this is learning to sing" in fake_server.PROPOSALS[-1]["payload"]["reason"]
    # the tool result was fed back before the decision
    assert any(m.get("role") == "tool" for m in muse.calls[1])
    assert ctx_store.load(cf).quests["q1"].assumption == "learning to sing"
    # pending proposal → nothing re-proposed, Muse not asked again
    assert Agent(client, muse, cf, stall_days=3).dig() == [] and len(muse.calls) == 2


def test_coach_can_park_but_not_after_a_rejected_park(world):
    client, cf = world
    muse = ScriptedMuse([{"role": "assistant", "content": None, "tool_calls": [call("park_quest", reason="It keeps losing to the others.", assumption="a someday goal")]}])
    res = Agent(client, muse, cf, stall_days=3).dig()
    assert res[0].move == "park_quest" and fake_server.PROPOSALS[-1]["op"] == "park_quest"
    # user rejects the park; next run the coach wants to park again → guardrail blocks it
    fake_server.PROPOSALS[-1]["status"] = "rejected"
    muse2 = ScriptedMuse([{"role": "assistant", "content": None, "tool_calls": [call("park_quest", reason="again", assumption="x")]}])
    res2 = Agent(client, muse2, cf, stall_days=3).dig()
    assert res2[0].outcome != "proposed" or fake_server.PROPOSALS[-1]["op"] != "park_quest"
    assert ctx_store.load(cf).quests["q1"].rejected_park is True


def test_ask_why_once_then_wait(world):
    client, cf = world
    muse = ScriptedMuse([{"role": "assistant", "content": None, "tool_calls": [call("ask_why", reason="No idea what this is for.")]}])
    res = Agent(client, muse, cf, stall_days=3).dig()
    assert res[0].step == WHY_STEP and res[0].minutes == 2 and res[0].outcome == "proposed"
    fake_server.PROPOSALS[-1]["status"] = "rejected"   # user ignored it; make the quest free again
    muse2 = ScriptedMuse([{"role": "assistant", "content": None, "tool_calls": [call("ask_why", reason="still")]}])
    res2 = Agent(client, muse2, cf, stall_days=3).dig()
    assert res2[0].outcome == "left-alone"


def test_plain_text_reply_is_handled(world):
    client, cf = world
    muse = ScriptedMuse([{"role": "assistant", "content": '{"step": "Open the file", "minutes": 2, "reason": "Just open it.", "assumption": "x"}'}])
    res = Agent(client, muse, cf, stall_days=3).dig(dry_run=True)
    assert res[0].move == "shrink_step" and res[0].outcome == "dry-run" and fake_server.PROPOSALS == []


def test_capture_preview_proposes_nothing(world):
    client, cf = world
    ag = Agent(client, ScriptedMuse([]), cf, stall_days=3)
    rows = ag.capture(ag.muse.capture_text("fix the bike, call mom", ""), source="notes", preview=True)
    assert [r["outcome"] for r in rows] == ["preview", "preview"] and fake_server.PROPOSALS == []
    rows = ag.capture(ag.muse.capture_text("fix the bike", ""), source="notes")
    assert rows[0]["outcome"] == "proposed" and fake_server.PROPOSALS[-1]["payload"]["track"] is False


class ReckonMuse:
    def __init__(self, reply):
        self.reply = reply

    def chat(self, messages, temperature=0.4):
        return self.reply


def test_reckoning_parks_with_a_reason(world):
    client, cf = world
    fake_server.QUESTS[1]["touched_at"] = "2026-10-05T08:00:00"   # two stalled tracked quests
    muse = ReckonMuse('{"verdict":"park","quest_id":"q1","makes_room_for":"Ship Scriptory v2","reason":"Singing has waited a month.","board_read":"One mover, one sleeper."}')
    v = Agent(client, muse, cf, stall_days=3).reckoning()
    assert v.verdict == "park" and fake_server.PROPOSALS[-1]["op"] == "park_quest"
    assert "Ship Scriptory v2" in fake_server.PROPOSALS[-1]["payload"]["reason"]


def test_reckoning_respects_a_refused_park(world):
    client, cf = world
    fake_server.QUESTS[1]["touched_at"] = "2026-10-05T08:00:00"
    ctx = ctx_store.Context()
    ctx.notes("q1", "Learn to sing").rejected_park = True
    ctx_store.save(cf, ctx)
    muse = ReckonMuse('{"verdict":"park","quest_id":"q1","makes_room_for":"x","reason":"again","board_read":"b"}')
    v = Agent(client, muse, cf, stall_days=3).reckoning()
    assert v.verdict == "focus" and v.blocked and fake_server.PROPOSALS == []


def test_reckoning_single_quest_is_fine(world):
    client, cf = world
    fake_server.QUESTS[1]["status"] = "later"
    try:
        v = Agent(client, ReckonMuse("unused"), cf, stall_days=3).reckoning()
    finally:
        fake_server.QUESTS[1]["status"] = "tracked"
    assert v.verdict == "fine" and "Only one quest" in v.reason and fake_server.PROPOSALS == []


def test_try_it_visitor_words_stay_out_of_the_log(world):
    import threading
    from http.server import ThreadingHTTPServer

    import httpx

    from irysquest import serve

    client, cf = world
    ag = Agent(client, ScriptedMuse([]), cf, stall_days=3)
    state = serve._State()
    state.agent, state.try_token = ag, "tok"
    srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(state))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        r = httpx.post(f"{base}/text?try=tok", json={"text": "visit grandma"}).json()
        assert [q["outcome"] for q in r["quests"]] == ["preview"] and fake_server.PROPOSALS == []
        assert not any("grandma" in l["text"] for l in ag.ctx.log + ctx_store.load(cf).log)
        assert httpx.post(f"{base}/dig?try=tok").status_code == 403
        # the owner's own capture is still logged, and proposed
        httpx.post(f"{base}/text", json={"text": "fix the bike"})
        assert any("fix the bike" in l["text"] for l in ctx_store.load(cf).log) and len(fake_server.PROPOSALS) == 1
    finally:
        srv.shutdown()


def test_unanswered_why_question_is_left_alone(world):
    client, cf = world
    q1 = fake_server.QUESTS[0]
    saved = dict(q1)
    q1["next_step"], q1["why"] = {"id": "s9", "text": WHY_STEP}, None
    try:
        muse = ScriptedMuse([])   # any call to the coach would fail: nothing scripted
        res = Agent(client, muse, cf, stall_days=3).dig()
        assert [(r.move, r.outcome) for r in res] == [("leave_alone", "left-alone")]
        assert muse.calls == [] and fake_server.PROPOSALS == []
        # once the why is written, the quest goes back to the coach
        q1["why"] = "Sing at the family get-together"
        muse = ScriptedMuse([{"role": "assistant", "content": None, "tool_calls": [call("shrink_step", step="Hum one scale", minutes=3, reason="r", assumption="a")]}])
        assert Agent(client, muse, cf, stall_days=3).dig()[0].outcome == "proposed"
    finally:
        q1.clear()
        q1.update(saved)
