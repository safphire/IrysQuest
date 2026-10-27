# SPDX-License-Identifier: AGPL-3.0-or-later
"""A small MCP client for the NextQuest server.

The server is stateless JSON-RPC 2.0 over POST (no sessions, no SSE), so a
plain HTTP client covers everything the agent needs. Read tools return data;
write tools create proposals that the user accepts, edits or rejects in the app.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from . import oauth

PROTOCOL_VERSION = "2025-06-18"


class ToolError(Exception):
    """A tool result with isError: true — bad arguments, a refused proposal, a rate limit."""


class QuestClient:
    def __init__(self, mcp_url: str, token_file: Path, timeout: float = 30):
        self.mcp_url = mcp_url
        self.token_file = token_file
        self.tokens = oauth.load_tokens(token_file)
        if self.tokens is None:
            raise SystemExit("Not signed in. Run `irysquest login` first.")
        self._http = httpx.Client(timeout=timeout)
        self._id = 0

    # ---- plumbing ---------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if self.tokens.expired():
            self.tokens = oauth.refresh(self.tokens, self.token_file)
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
            "Accept": "application/json",
            # ngrok's free tier shows an interstitial to browser-like clients; this header skips it.
            "ngrok-skip-browser-warning": "1",
        }

    def rpc(self, method: str, params: dict | None = None) -> Any:
        self._id += 1
        body = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            body["params"] = params
        r = self._http.post(self.mcp_url, json=body, headers=self._headers())
        if r.status_code == 401:
            self.tokens = oauth.refresh(self.tokens, self.token_file)
            r = self._http.post(self.mcp_url, json=body, headers=self._headers())
        r.raise_for_status()
        msg = r.json()
        if "error" in msg:
            e = msg["error"]
            raise RuntimeError(f"{method}: {e.get('code')} {e.get('message')}")
        return msg.get("result")

    def initialize(self) -> dict:
        return self.rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "IrysQuest", "version": "0.1.0"},
            },
        )

    def list_tools(self) -> list[dict]:
        return self.rpc("tools/list")["tools"]

    def call(self, tool: str, **arguments: Any) -> Any:
        """Calls a tool and returns its structured content (parsed JSON text) or raises ToolError."""
        result = self.rpc("tools/call", {"name": tool, "arguments": arguments})
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise ToolError(text or f"{tool} failed")
        if "structuredContent" in result:
            return result["structuredContent"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    # ---- read tools -------------------------------------------------------------------

    def get_today(self) -> dict:
        return self.call("get_today")

    def list_quests(self, status: str | None = None) -> Any:
        return self.call("list_quests", **({"status": status} if status else {}))

    def get_quest(self, quest_id: str) -> dict:
        return self.call("get_quest", quest_id=quest_id)

    def get_history(self, days: int = 7) -> Any:
        return self.call("get_history", days=days)

    def get_stats(self) -> dict:
        return self.call("get_stats")

    def list_proposals(self, status: str = "pending") -> Any:
        return self.call("list_proposals", status=status)

    # ---- write tools: every one of these creates a proposal, never a change -------------

    def propose_set_next_step(self, quest_id: str, text: str, reason: str, due_at: str | None = None) -> dict:
        args = {"quest_id": quest_id, "text": text, "reason": reason}
        if due_at:
            args["due_at"] = due_at
        return self.call("propose_set_next_step", **args)

    def propose_add_subquest(self, parent_id: str, title: str, reason: str, next_step: str | None = None) -> dict:
        args = {"parent_id": parent_id, "title": title, "reason": reason}
        if next_step:
            args["next_step"] = next_step
        return self.call("propose_add_subquest", **args)

    def propose_add_quest(self, title: str, reason: str, why: str | None = None, next_step: str | None = None, track: bool = False) -> dict:
        args: dict[str, Any] = {"title": title, "reason": reason, "track": track}
        if why:
            args["why"] = why
        if next_step:
            args["next_step"] = next_step
        return self.call("propose_add_quest", **args)

    def propose_park_quest(self, quest_id: str, reason: str) -> dict:
        return self.call("propose_park_quest", quest_id=quest_id, reason=reason)
