# SPDX-License-Identifier: AGPL-3.0-or-later
"""Which tracked quests have stalled, and what the user already said no to.

A quest is stalled when nothing about it has changed for STALL_DAYS: the server
stamps `touched_at` on every event that touches the quest, so that one field is
the signal. Quests with a pending proposal are skipped (the user hasn't answered
yet), and steps the user rejected are collected so Muse can try a different angle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Stall:
    quest_id: str
    title: str
    why: str | None
    current_step: str | None
    days: int
    rejected: list[str] = field(default_factory=list)


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)


def find_stalls(today: dict, proposals: list[dict], stall_days: int, now: datetime | None = None) -> list[Stall]:
    now = now or datetime.now()
    pending_for = {p.get("quest") for p in proposals if p.get("status") == "pending"}
    rejected_for: dict[str, list[str]] = {}
    for p in proposals:
        if p.get("status") == "rejected" and p.get("op") == "propose_set_next_step" and p.get("quest"):
            rejected_for.setdefault(p["quest"], []).append(p.get("after", ""))

    stalls: list[Stall] = []
    for q in today.get("tracked", []):
        age = now - _parse(q["touched_at"])
        if age < timedelta(days=stall_days):
            continue
        if q["id"] in pending_for or q["title"] in pending_for:
            continue
        step = (q.get("next_step") or {}).get("text")
        stalls.append(Stall(
            quest_id=q["id"], title=q["title"], why=q.get("why"), current_step=step,
            days=age.days, rejected=rejected_for.get(q["id"], []) + rejected_for.get(q["title"], []),
        ))
    stalls.sort(key=lambda s: -s.days)
    return stalls
