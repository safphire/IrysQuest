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
    outcome: str = ""   # proposed | dry-run | declined | muse-failed


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
            self._say(f'"{s.title}" untouched {s.days} days (step: {s.current_step or "none"}). Asking Muse for a smaller first move.')
            try:
                b = self.muse.breakdown(
                    title=s.title, why=s.why, current_step=s.current_step, stalled_days=s.days,
                    rejected=sorted(set(s.rejected + notes.rejected)), history=history.get(s.quest_id, []),
                    profile=self.ctx.profile, prior_assumption=notes.assumption,
                )
            except MuseError as e:
                self._say(f"  Muse couldn't help this time: {e}", "warn")
                res.outcome = "muse-failed"
                results.append(res)
                continue

            if b.needs_why and not s.why and not notes.asked_for_why:
                b.step, b.minutes = WHY_STEP, 2
                b.reason = "I can't tell yet what this quest is for, so the smallest useful move is to tell me."
                notes.asked_for_why = True
                self._say("  Purpose unclear and no why set: asking instead of guessing.")
            elif b.assumption:
                self._say(f"  Assuming: {b.assumption}")
                notes.assumption = b.assumption
                notes.intent = notes.intent or b.assumption

            res.step, res.minutes, res.reason, res.assumption = b.step, b.minutes, b.reason, b.assumption
            self._say(f'  → "{b.step}" ({b.minutes} min). {b.reason}')
            if dry_run:
                res.outcome = "dry-run"
                results.append(res)
                continue

            reason = b.reason
            if b.assumption and not b.needs_why:
                reason += f" (I'm assuming this is {b.assumption}; correct me in the Why if not.)"
            reason += f" Untouched {s.days} days; about {b.minutes} minutes."
            try:
                r = self.client.propose_set_next_step(s.quest_id, b.step, reason=reason[:1000])
                res.proposal_id, res.outcome = str(r.get("proposal_id", "")), "proposed"
                notes.last_proposed_at = datetime.now().isoformat(timespec="seconds")
                self._say(f"  Proposed. Waiting for your call in the app.")
            except ToolError as e:
                res.outcome = "declined"
                self._say(f"  Server declined: {e}", "warn")
            results.append(res)

        made = sum(1 for r in results if r.outcome == "proposed")
        self._say("Dry run: nothing was proposed." if dry_run else f"{made} proposal(s) waiting for your call.")
        self._save()
        return results

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

    def set_profile(self, text: str) -> None:
        self.ctx.profile = text.strip()[:1500]
        self._say("Profile updated.")
        self._save()
