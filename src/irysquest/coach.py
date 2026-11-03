# SPDX-License-Identifier: AGPL-3.0-or-later
"""The coach: Muse decides what to do about a stalled quest, with tools, inside guardrails.

This is what makes IrysQuest an agent rather than a pipeline. For each stalled
quest Muse gets:

- read tools, to look before it decides: the quest in full, its history, past
  proposals and the user's answers;
- one decision tool per move the server allows: shrink the step, add a
  subquest, park the quest, ask for the why, or leave it alone;
- a budget (at most N tool calls) and the user's rules as the system prompt.

Muse's decision is still only a *proposal*: it goes to the server, which
validates it, and to the app, where the user accepts, edits or rejects it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .muse import Muse, MuseError, _json_block

MAX_STEPS = 6

SYSTEM = """You are the coach inside a personal quest log. The user keeps at most five tracked quests; each shows one next step. A quest has stalled: nothing about it has moved for days. Decide the smallest useful move, then make exactly one decision call.

What the research says, and what you do about it:
- Procrastination is short-term mood repair, not laziness. The step feels bad to start, so make starting cheap: 2–10 minutes, concrete, with what the user already has. Never shame.
- Effort is what to reward, not completion. Frame steps as "a few minutes on it", not "finish it".
- If-then plans work. Attach a cue to every step: when and where ("after lunch, at the desk", "tonight, before the shower"). Put it in the cue field.
- Mental contrasting: if the quest has an obstacle or a plan written, use it; if the stall looks like a known obstacle, name it gently in the reason.
- Self-forgiveness after a slip reduces later procrastination. If the user has been away for days, forgive first and ask for one small step second. Never mention streaks, "overdue" or "again".
- Fresh starts: Mondays and the first day back after a gap are good moments for a clean small start.
- A missed day barely matters for a habit; say so if relevant.
- Momentum: if just_finished_a_step is true, the user completed a step and nothing comes next yet. Don't shrink or park; propose the natural next small step on the same thread (shrink_step with a cue), and acknowledge the finished step in one warm clause. This is the cheapest moment to keep going.

How to think: look first (get_quest, get_history, list_decisions) if the summary isn't enough; then choose:
- shrink_step: the usual move. Replace the step with one concrete 2–10 minute action the user can do today, with a cue. Never "research", "plan", "think about", "decide".
- add_subquest: the quest is really several things and the step keeps bouncing between them; name the first sub-goal with its own tiny first step.
- park_quest: the user's history shows this quest keeps losing to the others, or it's clearly out of season; parking frees a slot without deleting anything. Rare. Never park if the user rejected parking before.
- ask_why: there is no why and the history gives no clue what the quest is for. Don't guess; ask.
- leave_alone: the stall looks deliberate (a dated step in the future, a note saying wait) or the user rejected the last three suggestions in a row.

Always say what you assumed about the quest's purpose, in one short clause. Take a different angle from anything the user rejected. Write reasons to the user in warm, plain language. Banned words in reasons: overdue, failed, missed, lazy, behind, again."""

READ_TOOLS = [
    {"type": "function", "function": {"name": "get_quest", "description": "The quest in full: why, next step, subquests and their progress.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_history", "description": "What happened on this quest recently: steps done, captures, accepted proposals, and who did each (user or an assistant).", "parameters": {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90}}, "required": []}}},
    {"type": "function", "function": {"name": "list_decisions", "description": "Earlier proposals for this quest and what the user decided (accepted, edited, rejected, pending).", "parameters": {"type": "object", "properties": {}, "required": []}}},
]

_common = {
    "reason": {"type": "string", "description": "One or two warm sentences to the user explaining why this move, no guilt."},
    "assumption": {"type": "string", "description": "What you assumed this quest is for, one short clause."},
}
DECISION_TOOLS = [
    {"type": "function", "function": {"name": "shrink_step", "description": "Propose a new 2–10 minute next step for this quest, with a when/where cue.", "parameters": {"type": "object", "properties": {"step": {"type": "string", "maxLength": 200}, "minutes": {"type": "integer", "minimum": 2, "maximum": 10}, "cue": {"type": "string", "maxLength": 80, "description": "When and where, an if-then cue: 'after lunch, at the desk'."}, **_common}, "required": ["step", "minutes", "reason", "assumption"]}}},
    {"type": "function", "function": {"name": "add_subquest", "description": "Propose a subquest under this quest, with its own first step.", "parameters": {"type": "object", "properties": {"title": {"type": "string", "maxLength": 200}, "next_step": {"type": "string", "maxLength": 200}, **_common}, "required": ["title", "next_step", "reason", "assumption"]}}},
    {"type": "function", "function": {"name": "park_quest", "description": "Propose moving this quest to Later, freeing its slot. Nothing is deleted.", "parameters": {"type": "object", "properties": {**_common}, "required": ["reason", "assumption"]}}},
    {"type": "function", "function": {"name": "ask_why", "description": "Propose a 2-minute step asking the user to write what done looks like, because the purpose is unclear.", "parameters": {"type": "object", "properties": {"reason": _common["reason"]}, "required": ["reason"]}}},
    {"type": "function", "function": {"name": "leave_alone", "description": "Propose nothing this time.", "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]}}},
]
DECISION_NAMES = {t["function"]["name"] for t in DECISION_TOOLS}


def clean_assumption(text) -> str:
    """The agent writes "I'm assuming this is <assumption>", so drop a lead-in the model already wrote:
    "assuming this is for fun" → "for fun"."""
    a = str(text or "").strip().rstrip(".")
    a = re.sub(r"^(?:i'?m |i am )?(?:assuming|assumed|assumption:?)\s+(?:that\s+)?(?:this|it)\s+(?:is|'s)\s+", "", a, flags=re.I)
    a = re.sub(r"^(?:this|it)\s+is\s+", "", a, flags=re.I)
    return a[:200]


@dataclass
class Decision:
    move: str                 # shrink_step | add_subquest | park_quest | ask_why | leave_alone
    args: dict
    reason: str
    assumption: str = ""
    looked_at: list[str] = field(default_factory=list)   # read tools it called, in order
    turns: int = 0


class Coach:
    """Runs the tool loop for one stalled quest. `reads` supplies the read tools' answers."""

    def __init__(self, muse: Muse, reads: dict, max_steps: int = MAX_STEPS):
        self.muse, self.reads, self.max_steps = muse, reads, max_steps

    def decide(self, summary: dict, profile: str, rules: str = "") -> Decision:
        system = SYSTEM + (f"\n\nAbout the user: {profile}" if profile else "") + (f"\n\nUser's rules: {rules}" if rules else "")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "Stalled quest summary:\n" + json.dumps(summary, ensure_ascii=False) + "\n\nLook if you need to, then make one decision call."},
        ]
        tools = READ_TOOLS + DECISION_TOOLS
        looked: list[str] = []
        for turn in range(1, self.max_steps + 1):
            msg = self.muse.chat_tools(messages, tools)
            calls = msg.get("tool_calls") or []
            if not calls:
                # Plain text instead of a decision: treat a JSON-looking reply as shrink_step, else leave alone.
                return self._from_text(msg.get("content") or "", looked, turn)
            messages.append(msg)
            for tc in calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                if name in DECISION_NAMES:
                    return Decision(move=name, args=args, reason=str(args.get("reason", "")).strip()[:600],
                                    assumption=clean_assumption(args.get("assumption", "")), looked_at=looked, turns=turn)
                result = self.reads.get(name, lambda a: {"error": f"unknown tool {name}"})(args)
                looked.append(name)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]})
        return Decision(move="leave_alone", args={}, reason="Couldn't reach a decision within budget.", looked_at=looked, turns=self.max_steps)

    @staticmethod
    def _from_text(text: str, looked: list[str], turn: int) -> Decision:
        try:
            j = _json_block(text)
            step = str(j.get("step", "")).strip()
            if step:
                return Decision("shrink_step", {"step": step, "minutes": int(j.get("minutes", 5) or 5), "reason": j.get("reason", ""), "assumption": j.get("assumption", "")},
                                reason=str(j.get("reason", ""))[:600], assumption=clean_assumption(j.get("assumption", "")), looked_at=looked, turns=turn)
        except MuseError:
            pass
        return Decision("leave_alone", {}, reason=(text or "No decision.")[:600], looked_at=looked, turns=turn)
