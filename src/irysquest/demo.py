# SPDX-License-Identifier: AGPL-3.0-or-later
"""`irysquest demo`: the whole agent, with no accounts, no keys and no server to install.

Two stand-ins make that possible, and both are labelled as such wherever they speak:

- DemoBoard is an in-memory stand-in for the NextQuest server. It speaks the same MCP
  shape over HTTP on 127.0.0.1 (JSON-RPC, Bearer token, propose_* tools), holds a small
  sample quest log, and lets the demo play the user's part (accept, reject, mark done).
- ReplayMuse stands in for the Meta models. Its answers are the ones Muse Spark actually
  gave on real runs on 2 and 3 Nov 2026 (docs/VERIFICATION.md), replayed through the
  same tool-calling loop: the coach still "looks" with read tools before it decides.

Everything else is the real agent: stall detection, the coach loop and its guardrails,
memory, momentum, the reckoning, capture with settle-what-done-looks-like, the duplicate
check, and the capture page. Nothing leaves the machine.

With META_API_KEY set, `irysquest demo --live` uses the real Muse Spark on the same
sample board instead of the replay.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import oauth
from .agent import Agent
from .console import say
from .mcp_client import QuestClient
from .muse import CapturedQuest, MuseError

TOKEN = "demo-token"   # a local stand-in's token, not a credential for anything real


def _ago(days: float) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------------------
# DemoBoard: an in-memory NextQuest stand-in
# ---------------------------------------------------------------------------------------

class DemoBoard:
    """Sample data, clearly labelled. Quest titles follow the author's real board."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.quests: list[dict] = [
            {"id": "q-sing", "title": "Learn to sing: one song by December", "status": "tracked",
             "why": "Sing one song for family at the December get-together",
             "next_step": {"id": "s1", "text": "Pick the song and play it once"}, "touched_at": _ago(4)},
            {"id": "q-pilot", "title": "Finish the pilot script for Scriptory", "status": "tracked",
             "why": "A pilot I can send to people",
             "next_step": {"id": "s2", "text": "Open the draft and reread the last scene"}, "touched_at": _ago(5)},
            {"id": "q-valo", "title": "Check out YouTube videos on Valorant", "status": "tracked", "why": None,
             "next_step": {"id": "s3", "text": "Pick up phone and search Valorant on YouTube"}, "touched_at": _ago(4)},
            {"id": "q-kurz", "title": "Kurzgesagt-technique learning animations", "status": "tracked",
             "why": "Study how they hook viewers, for my own videos",
             "next_step": {"id": "s4", "text": "Watch one opening and note the first line"}, "touched_at": _ago(6)},
            {"id": "q-bike", "title": "Fix the bike", "status": "inbox", "why": None, "next_step": None, "touched_at": _ago(9)},
        ]
        self.proposals: list[dict] = []
        self.history: list[dict] = [
            {"quest_id": "q-sing", "at": _ago(4), "text": "Picked three candidate songs", "by": "user"},
            {"quest_id": "q-pilot", "at": _ago(5), "text": "Wrote the cold open", "by": "user"},
            {"quest_id": "q-kurz", "at": _ago(6), "text": "Captured from a voice note", "by": "user"},
        ]

    # -- the MCP tools ------------------------------------------------------------------
    def call(self, name: str, a: dict) -> tuple[dict | str, bool]:
        with self.lock:
            q_by = {q["id"]: q for q in self.quests}
            if name == "get_today":
                tracked = [q for q in self.quests if q["status"] == "tracked"]
                return {"date": datetime.now().strftime("%Y-%m-%d"), "tracked": tracked, "slots_used": len(tracked),
                        "slot_cap": 5, "streak_days": 0, "pending_proposals": sum(p["status"] == "pending" for p in self.proposals)}, False
            if name == "list_quests":
                st = a.get("status")
                return {"quests": [q for q in self.quests if (q["status"] == st if st else q["status"] not in ("done", "dropped"))]}, False
            if name == "get_quest":
                q = q_by.get(a.get("quest_id"))
                return (q, False) if q else ("unknown quest", True)
            if name == "get_history":
                return {"entries": list(self.history)}, False
            if name == "list_proposals":
                st = a.get("status")
                return {"proposals": [p for p in self.proposals if not st or p["status"] == st]}, False
            if name.startswith("propose_"):
                if not a.get("reason"):
                    return "reason is required", True
                qid = a.get("quest_id") or a.get("parent_id")
                if qid and qid not in q_by:
                    return "unknown quest", True
                title = q_by[qid]["title"] if qid else a.get("title", "")
                op = name.removeprefix("propose_")
                after = (f"{a['title']} — next: {a['next_step']}" if op == "add_quest" and a.get("next_step")
                         else a.get("text") or a.get("title", ""))
                p = {"id": f"demo-p{len(self.proposals) + 1}", "op": op, "payload": dict(a), "status": "pending",
                     "quest": title, "quest_id": qid, "after": after, "reason": a.get("reason"), "client": "IrysQuest"}
                self.proposals.append(p)
                return {"proposal_id": p["id"], "status": "pending"}, False
            return f"unknown tool {name}", True

    # -- the user's part, played by the demo ---------------------------------------------
    def decide(self, quest_title: str, accept: bool) -> dict | None:
        """Accept or reject the pending proposal for a quest, as the app would."""
        with self.lock:
            p = next((p for p in self.proposals if p["status"] == "pending" and p["quest"] == quest_title), None)
            if not p:
                return None
            p["status"] = "accepted" if accept else "rejected"
            q = next((q for q in self.quests if q["title"] == quest_title), None)
            if accept and q:
                if p["op"] == "set_next_step":
                    q["next_step"], q["needs_next_step"] = {"id": f"s-{p['id']}", "text": p["payload"]["text"]}, False
                elif p["op"] == "park_quest":
                    q["status"] = "later"
                q["touched_at"] = _ago(0)
                self.history.append({"quest_id": q["id"], "at": _ago(0), "text": f"Accepted: {p['after']}", "by": "user"})
            return p

    def done_from_notification(self, quest_title: str) -> None:
        """A step marked Done from a notification, with nothing written next: NextQuest's needs_next_step."""
        with self.lock:
            q = next(q for q in self.quests if q["title"] == quest_title)
            self.history.append({"quest_id": q["id"], "at": _ago(0), "text": f"Done: {q['next_step']['text']}", "by": "user"})
            q["next_step"], q["needs_next_step"], q["touched_at"] = None, True, _ago(0)

    # -- HTTP -----------------------------------------------------------------------------
    def start(self) -> tuple[ThreadingHTTPServer, str]:
        board = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                if self.path != "/mcp":
                    return self._send(404, {})
                if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                    self.send_response(401)
                    self.end_headers()
                    return
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                mid, method, params = body.get("id"), body.get("method"), body.get("params") or {}
                if method == "initialize":
                    res = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "NextQuest demo stand-in", "version": "0"}}
                elif method == "tools/list":
                    res = {"tools": [{"name": n, "description": "demo"} for n in
                                     ("get_today", "list_quests", "get_quest", "get_history", "list_proposals",
                                      "propose_set_next_step", "propose_add_subquest", "propose_add_quest", "propose_park_quest")]}
                elif method == "tools/call":
                    out, err = board.call(params.get("name"), params.get("arguments") or {})
                    res = {"content": [{"type": "text", "text": out if isinstance(out, str) else json.dumps(out)}], "isError": err}
                    if not err and isinstance(out, dict):
                        res["structuredContent"] = out
                else:
                    res = {}
                self._send(200, {"jsonrpc": "2.0", "id": mid, "result": res})

            def _send(self, status, obj):
                data = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, f"http://127.0.0.1:{srv.server_address[1]}"


# ---------------------------------------------------------------------------------------
# ReplayMuse: Muse Spark's answers from real runs, replayed through the same loop
# ---------------------------------------------------------------------------------------

# Recorded from real runs (3 Nov 2026 19:25 / 19:35 / 19:37, 2 Nov 19:51; docs/VERIFICATION.md).
REPLAY = {
    "Learn to sing: one song by December": {
        "first": ("shrink_step", {"step": "Stand and hum the chorus of your leading song idea out loud for 5 minutes", "minutes": 5,
                                  "cue": "tonight before shower, in your bedroom",
                                  "reason": "Just warming up your voice for a few minutes keeps it light and easy, and it's a kind first move toward December.",
                                  "assumption": "to sing confidently for family in December"}),
        "settled": ("leave_alone", {"reason": "To sing confidently for family in December, you already have a fresh 5-minute humming step set for tonight, so letting it breathe."}),
        "momentum": ("shrink_step", {"step": "Sing the chorus once through softly with the lyrics in front of you", "minutes": 5,
                                     "cue": "tonight after dinner, in the living room",
                                     "reason": "Lovely work getting that step done — let's keep the voice warm with a quick run-through while it's fresh.",
                                     "assumption": "to feel confident singing at the December get-together"}),
    },
    "Finish the pilot script for Scriptory": {
        "first": ("shrink_step", {"step": "Stand up and read the last scene aloud from the draft for 5 minutes", "minutes": 5,
                                  "cue": "at 9:30, at the desk to open the build block",
                                  "reason": "Starting is the hardest part, so let's keep it tiny and physical — just a few minutes hearing the voices to ease back into the scene.",
                                  "assumption": "to have a finished pilot you can send to people"}),
        "after_reject": ("shrink_step", {"step": "Grab paper and hand-write for 5 minutes on what happens next in the pilot", "minutes": 5,
                                         "cue": "after lunch, at the desk before opening the laptop",
                                         "reason": "Paper keeps this light and off-screen for a start, and a few minutes of scribbling is plenty to get the scene moving.",
                                         "assumption": "to have a finished pilot you can send to people"}),
    },
    "Check out YouTube videos on Valorant": {
        "first": ("ask_why", {"reason": "A quick note on what you want from these videos will make it easy to pick the right one to enjoy."}),
    },
    "Kurzgesagt-technique learning animations": {
        "first": ("shrink_step", {"step": "Copy one favourite Kurzgesagt opening line onto paper from memory", "minutes": 5,
                                  "cue": "after lunch, at your desk",
                                  "reason": "Starting with just the words keeps it light and hands-on, and gives you a hook you can borrow for your own videos.",
                                  "assumption": "to study hooks for your own future videos"}),
        "settled": ("leave_alone", {"reason": "To study hooks for your future videos, your paper line after lunch is already small, physical and clear, so leaving it as is for today."}),
    },
}
GENERIC = ("shrink_step", {"step": "Open it and spend 5 minutes on the smallest piece", "minutes": 5, "cue": "today, at your desk",
                           "reason": "A few minutes is enough to get it moving again.", "assumption": "something you still want"})

RECKONING = {"verdict": "fine", "quest_id": "", "makes_room_for": "",
             "reason": "All four quests were touched recently and there's still an open slot, so nothing is in the way.",
             "board_read": "The board looks alive with a little movement everywhere this week."}

CAPTURE_STEPS = {  # first steps and settle questions Muse Spark gave on 2–3 Nov
    "bike": ("Check the bike for 5 minutes and note what's broken", "What will your first smooth ride feel like?"),
    "appa": ("Pick a time this weekend and put it in your calendar", "How do you hope Appa feels after hearing you?"),
    "ukulele": ("Watch one 5-minute tutorial", "What first song would feel great to play all the way through?"),
    "pilot": ("Open the draft and reread the last scene", ""),
}


class ReplayMuse:
    """Same interface the agent uses; answers replayed from real Muse Spark runs."""

    label = "replayed from real Muse Spark runs (2–3 Nov 2026)"
    replay = True
    think = 0.0   # seconds to pause per answer, so the paced tour unfolds quest by quest

    def chat_tools(self, messages: list[dict], tools: list[dict], temperature: float = 0.3) -> dict:
        user = messages[1]["content"]
        summary = json.loads(user.split("\n", 1)[1].split("\n\nLook if")[0])
        if not any(m.get("role") == "tool" for m in messages):
            reads = [{"id": f"r{i}", "type": "function", "function": {"name": n, "arguments": "{}"}}
                     for i, n in enumerate(("get_quest", "get_history", "list_decisions"))]
            return {"role": "assistant", "content": None, "tool_calls": reads}
        move, args = self._decide(summary)
        _pause(self.think)
        return {"role": "assistant", "content": None,
                "tool_calls": [{"id": "d", "type": "function", "function": {"name": move, "arguments": json.dumps(args)}}]}

    @staticmethod
    def _decide(s: dict) -> tuple[str, dict]:
        book = REPLAY.get(s.get("title", ""), {})
        if s.get("just_finished_a_step"):
            return book.get("momentum", GENERIC)
        if s.get("steps_user_rejected"):
            return book.get("after_reject", book.get("first", GENERIC))
        first = book.get("first")
        if first and first[0] == "shrink_step" and (s.get("current_step") or "").startswith(first[1]["step"]):
            return book.get("settled", ("leave_alone", {"reason": "The step you accepted is already small; letting it play out."}))
        return first or GENERIC

    def chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        _pause(self.think)
        return json.dumps(RECKONING)

    def capture_text(self, dump: str, profile: str) -> list[CapturedQuest]:
        out = []
        for part in re.split(r",|\band\b|\n", dump):
            t = part.strip(" .").strip()
            t = re.sub(r"^(i keep saying i'?ll|i need to|need to|also)\s+", "", t, flags=re.I)
            if len(t) < 3:
                continue
            key = next((k for k in CAPTURE_STEPS if k in t.lower()), None)
            out.append(CapturedQuest(title=t[:1].upper() + t[1:], next_step=CAPTURE_STEPS[key][0] if key else "Spend 5 minutes on the first piece"))
        return out[:12]

    def settle(self, quests: list[CapturedQuest], profile: str) -> list[str]:
        qs = []
        for q in quests:
            key = next((k for k in CAPTURE_STEPS if k in q.title.lower()), None)
            qs.append(CAPTURE_STEPS[key][1] if key else f'What does done look like for "{q.title}"?')
        return qs

    def capture_image(self, *a, **k):
        raise MuseError("Photo capture needs the real Muse Spark: set META_API_KEY and run `irysquest demo --serve --live`.")

    def transcribe(self, *a, **k):
        raise MuseError("Voice capture needs Muse Voice Transcribe: set META_API_KEY and run `irysquest demo --serve --live`.")

    def breakdown(self, *a, **k):
        raise MuseError("not used in demo mode")


# ---------------------------------------------------------------------------------------
# The demo itself
# ---------------------------------------------------------------------------------------

def _setup(live: bool):
    board = DemoBoard()
    srv, url = board.start()
    home = Path(tempfile.mkdtemp(prefix="irysquest-demo-"))
    tf = home / "tokens.json"
    oauth.save_tokens(tf, oauth.Tokens("demo", f"{url}/oauth/token", TOKEN, "demo-refresh", time.time() + 86400))
    client = QuestClient(f"{url}/mcp", tf)
    client.initialize()
    if live:
        from .muse import META_BASE_URL, META_MODEL, Muse, Provider
        key = os.environ.get("META_API_KEY", "")
        if not key:
            raise SystemExit("--live needs META_API_KEY in the environment (or in .env). Without it, run `irysquest demo`.")
        muse = Muse(Provider(name="meta", base_url=META_BASE_URL, model=META_MODEL, api_key=key))
        label = "live: real Muse Spark"
    else:
        muse = ReplayMuse()
        label = ReplayMuse.label
    agent = Agent(client, muse, home / "context.json", stall_days=3)
    return board, srv, agent, label


def _banner(label: str) -> None:
    say("─" * 78)
    say("IrysQuest DEMO MODE: no accounts, no keys, nothing leaves this machine.")
    say("  Quest log: a built-in NextQuest stand-in holding SAMPLE quests (in memory).")
    say(f"  Coach:     {label}.")
    say("  Everything else is the real agent. The demo plays your part in the app.")
    say("─" * 78)


def _you(text: str) -> None:
    say(f"YOU (played by the demo, in the app): {text}")


def _pause(seconds: float) -> None:
    if seconds:
        time.sleep(seconds)


def run(live: bool = False, pace: float = 0.8) -> dict:
    """The scripted tour. Returns a summary, so tests can check it."""
    board, srv, agent, label = _setup(live)
    if getattr(agent.muse, "replay", False):
        agent.muse.think = pace * 0.75
    _banner(label)
    try:
        say("1) The morning dig. Four tracked quests have gone quiet for 4–6 days.")
        _pause(pace)
        first = agent.dig()
        _pause(pace)

        _you("accept the singing step, reject 'read the last scene aloud', accept the Kurzgesagt step; leave the why-question for now.")
        board.decide("Learn to sing: one song by December", True)
        board.decide("Finish the pilot script for Scriptory", False)
        board.decide("Kurzgesagt-technique learning animations", True)
        _pause(pace)

        say("2) The next dig. It remembers the refusal and takes a different angle.")
        _pause(pace)
        second = agent.dig()
        _pause(pace)

        _you("hum the chorus, then tap Done on the reminder notification, with nothing written next.")
        board.decide("Finish the pilot script for Scriptory", True)
        board.done_from_notification("Learn to sing: one song by December")
        _pause(pace)

        say("3) Momentum. A finished step with nothing next goes to the coach at once.")
        _pause(pace)
        third = agent.dig()
        _pause(pace)

        say("4) The weekly reckoning: the whole board, one verdict.")
        _pause(pace)
        verdict = agent.reckoning(dry_run=True)
        _pause(pace)

        say("5) Capture: a typed brain dump, with one 'what does done look like?' question each.")
        dump = "fix the bike, call appa this weekend and I keep saying I'll learn the ukulele"
        say(f'  Brain dump: "{dump}"')
        quests = agent.muse.capture_text(dump, "")
        for q, question in zip(quests, agent.settle_questions(quests)):
            say(f"  • {q.title}" + (f"  →  asks: {question}" if question else ""))
            if "ukulele" in q.title.lower():
                q.why = "Play one song at the December get-together"
        _you("answer the ukulele question; leave the others blank.")
        captured = agent.capture(quests, source="notes")
        _pause(pace)

        say("─" * 78)
        say("What would now be waiting in the app's Proposals screen (sample data):")
        for p in board.proposals:
            if p["status"] == "pending":
                say(f"  [{p['op']}] {p['quest']}: {p['after']}")
                say(f"      reason: {p['reason'][:150]}{'…' if len(p['reason']) > 150 else ''}")
        say("─" * 78)
        say("Next: `irysquest demo --serve` opens the capture page at http://localhost:8787 on this sample board.")
        say("With your own Meta Model API key in META_API_KEY, add --live to use the real Muse Spark instead of the replay.")
        return {"first": first, "second": second, "third": third, "verdict": verdict, "captured": captured, "proposals": board.proposals}
    finally:
        srv.shutdown()


def serve_demo(live: bool = False, port: int = 8787) -> None:
    from .serve import serve
    board, srv, agent, label = _setup(live)
    _banner(label)
    say("The capture page runs on the sample board. Try Type it, Dig now, Preview only, Weekly reckoning.")
    say("Voice and photo need the real models (--live with META_API_KEY); typed capture works without them.")
    try:
        serve(agent, "127.0.0.1", port, "03:00", "", tls_dir=None)
    finally:
        srv.shutdown()
