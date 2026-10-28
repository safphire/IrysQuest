# SPDX-License-Identifier: AGPL-3.0-or-later
"""The agent's own memory: who the user is, and what it has learned per quest.

NextQuest holds the quests; this file holds what the agent inferred about them
and what the user said back. It lives next to the tokens, never in the repo.

- profile: a few lines the user wrote about themselves (role, schedule, what a
  "small step" means for them). Professionals and casual users differ most here.
- quests[id]: intent the agent inferred, the assumption it last stated, the
  steps accepted and rejected, and when it last proposed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class QuestNotes:
    title: str = ""
    intent: str = ""          # what the agent currently believes the quest is for
    assumption: str = ""      # the assumption stated in the last proposal
    accepted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    last_proposed_at: str = ""
    asked_for_why: bool = False


@dataclass
class Context:
    profile: str = ""
    quests: dict[str, QuestNotes] = field(default_factory=dict)
    log: list[dict] = field(default_factory=list)   # the console's recent lines, for the web page

    def notes(self, quest_id: str, title: str = "") -> QuestNotes:
        n = self.quests.setdefault(quest_id, QuestNotes())
        if title:
            n.title = title
        return n

    def remember(self, line: str, kind: str = "info") -> None:
        self.log.append({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "text": line})
        del self.log[:-200]


def load(path: Path) -> Context:
    if not path.exists():
        return Context()
    raw = json.loads(path.read_text())
    ctx = Context(profile=raw.get("profile", ""), log=raw.get("log", []))
    for qid, n in raw.get("quests", {}).items():
        ctx.quests[qid] = QuestNotes(**{k: v for k, v in n.items() if k in QuestNotes.__dataclass_fields__})
    return ctx


def save(path: Path, ctx: Context) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(ctx), indent=2, ensure_ascii=False))


def reconcile(ctx: Context, proposals: list[dict]) -> None:
    """Folds the user's decisions (from the server's proposal list) into the notes."""
    by_title = {n.title: n for n in ctx.quests.values() if n.title}
    for p in proposals:
        n = by_title.get(p.get("quest") or "")
        if not n or p.get("op") != "propose_set_next_step":
            continue
        step = p.get("after", "")
        if p.get("status") in ("accepted", "edited") and step and step not in n.accepted:
            n.accepted.append(step)
        if p.get("status") == "rejected" and step and step not in n.rejected:
            n.rejected.append(step)
