# SPDX-License-Identifier: AGPL-3.0-or-later
"""The weekly reckoning: the coach looks at all tracked quests together.

The morning dig treats quests one at a time. Once a week the coach steps back
and asks a harder question: with five slots and this much attention, is anything
crowding out what matters? It may propose parking one quest so another can
breathe, or it may say the week is fine. One decision for the whole board.

Same contract as everything else: a proposal, which the user accepts or rejects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .muse import Muse, _json_block

SYSTEM = """You are the coach inside a personal quest log. The user can track at most five quests at once; each shows one next step. Once a week you look at the whole board, not one quest.

You're given every tracked quest with its why, its current step, days since anything moved, steps completed in the last 30 days, and what the user accepted or rejected from you. Also the user's profile and rules.

Decide ONE of:
- park: one quest is crowding out the others. It has had its chance (two weeks or more, few or no completed steps, suggestions rejected) and freeing its slot would help a quest that is moving. Name the quest and the quest it makes room for. Never park a quest the user's rules protect, and never one the user refused to park before.
- focus: nothing needs parking, but one quest deserves the week. Name it and say why in one sentence; propose no change.
- fine: the board is healthy. Say so in one sentence.

Be plain and kind. No guilt, no productivity jargon. Reply with JSON only:
{"verdict": "park"|"focus"|"fine", "quest_id": "<id or empty>", "makes_room_for": "<quest title or empty>", "reason": "<one or two sentences to the user>", "board_read": "<one sentence on the week as you see it>"}"""


@dataclass
class Verdict:
    verdict: str            # park | focus | fine
    quest_id: str = ""
    makes_room_for: str = ""
    reason: str = ""
    board_read: str = ""
    blocked: str = ""       # set when a guardrail overrode a park


def reckon(muse: Muse, board: list[dict], profile: str, rules: str, protected_ids: set[str]) -> Verdict:
    text = muse.chat([
        {"role": "system", "content": SYSTEM + (f"\n\nAbout the user: {profile}" if profile else "") + (f"\n\nUser's rules: {rules}" if rules else "")},
        {"role": "user", "content": json.dumps({"tracked_quests": board}, ensure_ascii=False)},
    ], temperature=0.3)
    j = _json_block(text)
    v = Verdict(
        verdict=str(j.get("verdict", "fine")).strip().lower(),
        quest_id=str(j.get("quest_id", "")).strip(),
        makes_room_for=str(j.get("makes_room_for", "")).strip()[:200],
        reason=str(j.get("reason", "")).strip()[:600],
        board_read=str(j.get("board_read", "")).strip()[:300],
    )
    if v.verdict not in ("park", "focus", "fine"):
        v.verdict = "fine"
    if v.verdict == "park":
        ids = {q["id"] for q in board}
        if v.quest_id not in ids:
            v.verdict, v.blocked = "fine", "named a quest that isn't on the board"
        elif v.quest_id in protected_ids:
            v.verdict, v.blocked = "focus", "that quest is protected (rules or an earlier refusal)"
    return v
