# SPDX-License-Identifier: AGPL-3.0-or-later
"""The agent's loop: read state → notice what's buried → ask Muse → propose → remember.

Used by `irysquest dig` and by the server's schedule and "dig now". Every
decision is said out loud through `say` and written to the context log, so the
console and the web page tell the same story.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import context as ctx_store
from .console import say
from .mcp_client import QuestClient, ToolError
from .coach import Coach
from .reckoning import Verdict, reckon
from .muse import CapturedQuest, Muse, MuseError
from .stalls import find_stalls

WHY_STEP = "Write one line in this quest's Why: what does done look like?"


@dataclass
class DigResult:
    quest_id: str
    title: str
    days: int
    step: str = ""
    minutes: int = 0
    reason: str = ""
    assumption: str = ""
    proposal_id: str = ""
    move: str = ""      # shrink_step | add_subquest | park_quest | ask_why | leave_alone
    outcome: str = ""   # proposed | dry-run | declined | muse-failed | left-alone


class Agent:
    def __init__(self, client: QuestClient, muse: Muse, context_file: Path, stall_days: int):
        self.client = client
        self.muse = muse
        self.context_file = context_file
        self.stall_days = stall_days
        self.ctx = ctx_store.load(context_file)

    def _say(self, text: str, kind: str = "info") -> None:
        say(text)
        self.ctx.remember(text, kind)

    def _save(self) -> None:
        ctx_store.save(self.context_file, self.ctx)

    # ---- dig: the morning loop ----------------------------------------------------------

    def dig(self, *, dry_run: bool = False, days: int | None = None) -> list[DigResult]:
        days = self.stall_days if days is None else days
        self._say("Reading your tracked quests.")
        today = self.client.get_today()
        proposals: list[dict] = []
        for st in ("pending", "rejected", "accepted", "edited"):
            proposals += self.client.list_proposals(st).get("proposals", [])
        ctx_store.reconcile(self.ctx, proposals)

        stalls = find_stalls(today, proposals, days)
        self._say(f"{today['slots_used']}/{today['slot_cap']} slots used; {len(stalls)} stalled for {days}+ days.")
        results: list[DigResult] = []
        if not stalls:
            self._say("Nothing is buried. See you tomorrow.")
            self._save()
            return results

        history = self._history_by_quest()
        for s in stalls:
            notes = self.ctx.notes(s.quest_id, s.title)
            res = DigResult(quest_id=s.quest_id, title=s.title, days=s.days)
            self._say(f'"{s.title}" untouched {s.days} days (step: {s.current_step or "none"}). Handing it to the coach.')
            rejected = sorted(set(s.rejected + notes.rejected))
            summary = {
                "quest_id": s.quest_id, "title": s.title, "why": s.why or "", "current_step": s.current_step or "",
                "days_untouched": s.days, "steps_user_rejected": rejected, "your_previous_assumption": notes.assumption,
                "user_rejected_parking_before": notes.rejected_park, "asked_for_why_before": notes.asked_for_why,
                "slots": f"{today['slots_used']}/{today['slot_cap']}",
            }
            reads = {
                "get_quest": lambda a, qid=s.quest_id: self._safe(lambda: self.client.get_quest(qid)),
                "get_history": lambda a, qid=s.quest_id: {"entries": history.get(qid, [])},
                "list_decisions": lambda a, qid=s.quest_id, t=s.title: self._decisions_for(proposals, t),
            }
            try:
                d = Coach(self.muse, reads).decide(summary, self.ctx.profile, self.ctx.rules)
            except MuseError as e:
                self._say(f"  Muse couldn't help this time: {e}", "warn")
                res.outcome = "muse-failed"
                results.append(res)
                continue
            if d.looked_at:
                self._say(f"  Looked at: {', '.join(d.looked_at)}.")
            res.move, res.assumption, res.reason = d.move, d.assumption, d.reason

            # ---- guardrails: the user's rules beat the model's choice ----
            if d.move == "park_quest" and notes.rejected_park:
                self._say("  Coach wanted to park it, but you said no to that before. Shrinking instead.")
                d.move = "ask_why" if not s.why else "leave_alone"
            if d.move == "ask_why" and (s.why or notes.asked_for_why):
                d.move = "leave_alone"
                d.reason = "I've already asked what this is for; I'll wait for the why."
            if d.assumption and d.move not in ("ask_why", "leave_alone"):
                self._say(f"  Assuming: {d.assumption}")
                notes.assumption = d.assumption
                notes.intent = notes.intent or d.assumption

            if d.move == "leave_alone":
                self._say(f"  Leaving it alone: {d.reason}")
                res.outcome = "left-alone"
                results.append(res)
                continue
            if d.move == "ask_why":
                res.step, res.minutes = WHY_STEP, 2
                res.reason = d.reason or "I can't tell yet what this quest is for, so the smallest useful move is to tell me."
                notes.asked_for_why = True
                self._say("  Purpose unclear and no why set: asking instead of guessing.")
            elif d.move == "shrink_step":
                res.step = str(d.args.get("step", "")).strip()[:200]
                res.minutes = max(2, min(10, int(d.args.get("minutes", 5) or 5)))
            elif d.move == "add_subquest":
                res.step = f"{d.args.get('title', '').strip()[:120]} → {d.args.get('next_step', '').strip()[:120]}"
                res.minutes = 5
            elif d.move == "park_quest":
                res.step, res.minutes = "Park this quest (move to Later; nothing is deleted)", 0

            if d.move == "shrink_step" and not res.step:
                self._say("  Coach returned an empty step; skipping.", "warn")
                res.outcome = "muse-failed"
                results.append(res)
                continue
            label = {"shrink_step": "step", "add_subquest": "subquest", "park_quest": "park", "ask_why": "question"}[d.move]
            self._say(f'  → {label}: "{res.step}"' + (f" ({res.minutes} min)" if res.minutes else "") + f". {res.reason}")
            if dry_run:
                res.outcome = "dry-run"
                results.append(res)
                continue

            reason = res.reason
            if d.assumption and d.move not in ("ask_why",):
                reason += f" (I'm assuming this is {d.assumption}; correct me in the Why if not.)"
            reason += f" Untouched {s.days} days" + (f"; about {res.minutes} minutes." if res.minutes else ".")
            reason = reason[:1000]
            try:
                if d.move in ("shrink_step", "ask_why"):
                    r = self.client.propose_set_next_step(s.quest_id, res.step, reason=reason)
                elif d.move == "add_subquest":
                    r = self.client.propose_add_subquest(s.quest_id, str(d.args.get("title", ""))[:500], reason=reason, next_step=str(d.args.get("next_step", ""))[:2000] or None)
                else:
                    r = self.client.propose_park_quest(s.quest_id, reason=reason)
                res.proposal_id, res.outcome = str(r.get("proposal_id", "")), "proposed"
                notes.last_proposed_at = datetime.now().isoformat(timespec="seconds")
                notes.last_move = d.move
                self._say("  Proposed. Waiting for your call in the app.")
            except ToolError as e:
                res.outcome = "declined"
                self._say(f"  Server declined: {e}", "warn")
            results.append(res)

        made = sum(1 for r in results if r.outcome == "proposed")
        self._say("Dry run: nothing was proposed." if dry_run else f"{made} proposal(s) waiting for your call.")
        self._save()
        return results

    @staticmethod
    def _safe(fn):
        try:
            return fn()
        except ToolError as e:
            return {"error": str(e)}

    @staticmethod
    def _decisions_for(proposals: list[dict], title: str) -> dict:
        rows = [{"op": p.get("op"), "proposed": p.get("after"), "status": p.get("status"), "at": p.get("created_at", "")[:10]}
                for p in proposals if p.get("quest") == title]
        return {"decisions": rows[-10:]}

    def _history_by_quest(self, days: int = 30) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        try:
            for e in self.client.get_history(days).get("entries", []):
                if e.get("quest_id"):
                    out.setdefault(e["quest_id"], []).append(f"{e.get('at', '')[:10]} {e.get('text', '')} ({e.get('by', '')})")
        except ToolError:
            pass
        return out

    # ---- capture: brain dump → proposed quests ------------------------------------------

    def capture(self, quests: list[CapturedQuest], *, source: str, preview: bool = False) -> list[dict]:
        """Proposes each captured quest into the inbox. With preview=True, proposes nothing (try-it mode)."""
        out = []
        self._say(f"{len(quests)} quest(s) found in the {source}." + (" Preview only." if preview else ""))
        for q in quests:
            row = {"title": q.title, "why": q.why, "next_step": q.next_step, "outcome": "preview"}
            self._say(f'  • {q.title}' + (f' → first step: {q.next_step}' if q.next_step else ""))
            if not preview:
                try:
                    r = self.client.propose_add_quest(
                        q.title, reason=f"Captured from your {source}. It goes to the inbox; track it when a slot is free.",
                        why=q.why or None, next_step=q.next_step or None, track=False,
                    )
                    row["outcome"], row["proposal_id"] = "proposed", r.get("proposal_id", "")
                except ToolError as e:
                    row["outcome"], row["error"] = "declined", str(e)
                    self._say(f"    Server declined: {e}", "warn")
            out.append(row)
        if not preview:
            self._say(f"{sum(1 for r in out if r['outcome'] == 'proposed')} proposal(s) waiting in the app.")
        self._save()
        return out

    # ---- the weekly reckoning: the whole board at once -----------------------------------

    def reckoning(self, *, dry_run: bool = False) -> Verdict:
        self._say("Weekly reckoning: looking at the whole board, not one quest.")
        today = self.client.get_today()
        proposals: list[dict] = []
        for st in ("pending", "rejected", "accepted", "edited"):
            proposals += self.client.list_proposals(st).get("proposals", [])
        ctx_store.reconcile(self.ctx, proposals)
        history = self._history_by_quest(30)
        now = datetime.now()
        board = []
        protected: set[str] = set()
        for q in today.get("tracked", []):
            n = self.ctx.notes(q["id"], q["title"])
            if n.rejected_park:
                protected.add(q["id"])
            touched = datetime.fromisoformat(q["touched_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            done = [h for h in history.get(q["id"], []) if "done" in h.lower() or "completed" in h.lower()]
            board.append({
                "id": q["id"], "title": q["title"], "why": q.get("why") or "", "current_step": (q.get("next_step") or {}).get("text", ""),
                "days_since_anything_moved": (now - touched).days, "steps_completed_last_30_days": len(done),
                "accepted_from_coach": n.accepted[-3:], "rejected_from_coach": n.rejected[-3:], "user_refused_parking": n.rejected_park,
            })
        if len(board) < 2:
            v = Verdict("fine", reason="Only one quest is tracked; nothing can crowd it out.", board_read="A quiet board.")
            self._say(f"  {v.reason}")
            self._save()
            return v
        try:
            v = reckon(self.muse, board, self.ctx.profile, self.ctx.rules, protected)
        except MuseError as e:
            self._say(f"  Muse couldn't help this time: {e}", "warn")
            return Verdict("fine", reason=str(e))
        self._say(f"  Board: {v.board_read}")
        if v.blocked:
            self._say(f"  Coach wanted to park, but {v.blocked}. Downgrading to focus.")
        title = next((q["title"] for q in board if q["id"] == v.quest_id), "")
        if v.verdict == "park":
            self._say(f'  → park "{title}" to make room for "{v.makes_room_for}". {v.reason}')
            if not dry_run:
                try:
                    reason = f"{v.reason} (Weekly reckoning: freeing this slot for \"{v.makes_room_for}\". Nothing is deleted; it moves to Later.)"
                    r = self.client.propose_park_quest(v.quest_id, reason=reason[:1000])
                    self._say("  Proposed. Your call in the app.")
                except ToolError as e:
                    self._say(f"  Server declined: {e}", "warn")
        elif v.verdict == "focus":
            self._say(f'  → focus on "{title}" this week. {v.reason} (No change proposed.)')
        else:
            self._say(f"  → the board is fine. {v.reason}")
        self.ctx.remember(f"reckoning:{v.verdict}:{title}", "reckoning")
        self._save()
        return v

    def set_profile(self, text: str) -> None:
        self.ctx.profile = text.strip()[:1500]
        self._say("Profile updated.")
        self._save()

    def set_rules(self, text: str) -> None:
        self.ctx.rules = text.strip()[:1500]
        self._say("Rules updated.")
        self._save()
