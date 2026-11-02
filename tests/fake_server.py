# SPDX-License-Identifier: AGPL-3.0-or-later
"""A tiny stand-in for the NextQuest MCP server, so the agent's tests run without it.

It speaks the same shape: stateless JSON-RPC over POST /mcp, Bearer auth, tool
results with structuredContent, proposals that only ever land in a list. Nothing
here is the real server; it exists so the agent's own logic can be tested fast.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = "fake-token"

QUESTS = [
    {"id": "q1", "title": "Learn to sing", "status": "tracked", "next_step": {"id": "s1", "text": "Find a vocal warm-up video"}, "touched_at": "2026-10-20T08:00:00"},
    {"id": "q2", "title": "Ship Scriptory v2", "status": "tracked", "next_step": {"id": "s2", "text": "Fix pronunciation bug"}, "touched_at": "2026-10-27T09:00:00"},
    {"id": "q3", "title": "Read the Kotlin book", "status": "later", "next_step": None, "touched_at": "2026-10-01T08:00:00"},
]
PROPOSALS: list[dict] = []

TOOLS = [
    {"name": "get_today", "description": "Tracked quests with their next steps."},
    {"name": "list_quests", "description": "Quests by status."},
    {"name": "get_quest", "description": "One quest."},
    {"name": "list_proposals", "description": "Proposals and decisions."},
    {"name": "propose_set_next_step", "description": "Propose a new next step."},
    {"name": "propose_add_subquest", "description": "Propose a subquest."},
    {"name": "propose_add_quest", "description": "Propose a new quest."},
    {"name": "propose_park_quest", "description": "Propose parking a quest."},
]


def _call(name: str, a: dict) -> tuple[dict | str, bool]:
    if name == "get_today":
        tracked = [q for q in QUESTS if q["status"] == "tracked"]
        return {"date": "2026-10-27", "tracked": tracked, "slots_used": len(tracked), "slot_cap": 5, "streak": 3, "pending_proposals": len(PROPOSALS)}, False
    if name == "list_quests":
        st = a.get("status")
        return {"quests": [q for q in QUESTS if (q["status"] == st if st else q["status"] not in ("done", "dropped"))]}, False
    if name == "get_quest":
        q = next((q for q in QUESTS if q["id"] == a.get("quest_id")), None)
        return (q, False) if q else ("unknown quest", True)
    if name == "list_proposals":
        return {"proposals": PROPOSALS}, False
    if name.startswith("propose_"):
        if not a.get("reason"):
            return "reason is required", True
        qid = a.get("quest_id") or a.get("parent_id")
        title = next((q["title"] for q in QUESTS if q["id"] == qid), a.get("title"))
        p = {"id": f"p{len(PROPOSALS) + 1}", "op": name.removeprefix("propose_"), "payload": a, "status": "pending",
             "quest": title,
             # as the real server shapes it: an add_quest's `after` is "title — next: step"
             "after": (f"{a['title']} — next: {a['next_step']}" if name == "propose_add_quest" and a.get("next_step") else a.get("text") or a.get("title", "")),
             "reason": a.get("reason")}
        PROPOSALS.append(p)
        return p, False
    return f"unknown tool {name}", True


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/mcp":
            return self._send(404, {})
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Bearer resource_metadata="http://127.0.0.1/.well-known/oauth-protected-resource"')
            self.end_headers()
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        mid, method, params = body.get("id"), body.get("method"), body.get("params") or {}
        if method == "initialize":
            res = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "fake", "version": "0"}}
        elif method == "ping":
            res = {}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            out, err = _call(params.get("name"), params.get("arguments") or {})
            text = out if isinstance(out, str) else json.dumps(out)
            res = {"content": [{"type": "text", "text": text}], "isError": err}
            if not err and isinstance(out, dict):
                res["structuredContent"] = out
        else:
            return self._send(200, {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown method"}})
        self._send(200, {"jsonrpc": "2.0", "id": mid, "result": res})

    def _send(self, status: int, obj: dict):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def start() -> tuple[HTTPServer, str]:
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


if __name__ == "__main__":
    srv, url = start()
    print(f"fake server at {url}/mcp (token: {TOKEN})")
    threading.Event().wait()
