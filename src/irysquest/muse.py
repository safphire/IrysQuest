# SPDX-License-Identifier: AGPL-3.0-or-later
"""Meta's models, through the Model API or any OpenAI-compatible host.

- Muse Spark (text + vision): breakdowns of stalled quests, and turning a brain
  dump or a notebook photo into quests.
- Muse Voice Transcribe: audio → text.
- Provider "open": the same calls against Muse Spark Open on a host you choose
  (Baseten, Modal, or a local server), for the open-weight mode.

Replies are asked for as JSON and parsed defensively: anything that can't be
parsed is dropped, never half-proposed.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field

import httpx

META_BASE_URL = "https://api.meta.ai/v1"
META_MODEL = "muse-spark-1.3"
TRANSCRIBE_MODEL = "muse-voice-transcribe-1.0"

BREAKDOWN_SYSTEM = """You are a coach inside a personal quest log. The user keeps at most five tracked quests, each with one visible next step. One quest has stalled: nothing about it has moved for days.

Propose a NEW first step so small it can be done in 2 to 10 minutes, today, with what the user already has. Shrink, don't plan: one concrete physical or on-screen action. Never "research", "think about", "plan" or "decide".

Use the context you are given: the quest's why, its history, the user's profile, and what they rejected before (take a different angle from those). Say what you assumed about the quest's purpose; if the purpose is unclear and there is no why and no history, set needs_why to true and make the step: write one line in the quest's Why about what done looks like.

Reply with JSON only:
{"step": "<imperative, under 90 characters>", "minutes": <2-10>, "reason": "<one warm, plain sentence to the user; no guilt>", "assumption": "<what you assumed this quest is for, one short clause>", "needs_why": <true|false>}"""

CAPTURE_SYSTEM = """You turn a person's raw brain dump into separate quests for a personal quest log. Each quest is one outcome they want, in their own words where possible, with an optional one-line why and a first step doable in 2 to 10 minutes. Keep what they said; don't invent goals they didn't mention. Merge duplicates. Skip chatter that isn't a goal.

Reply with JSON only: {"quests": [{"title": "<under 80 chars>", "why": "<optional>", "next_step": "<2-10 minute action>"}]}"""


@dataclass
class Breakdown:
    step: str
    minutes: int
    reason: str
    assumption: str = ""
    needs_why: bool = False


@dataclass
class CapturedQuest:
    title: str
    why: str = ""
    next_step: str = ""


@dataclass
class Provider:
    name: str
    base_url: str
    model: str
    api_key: str
    transcribe_model: str = TRANSCRIBE_MODEL
    transcribe_base_url: str = META_BASE_URL   # transcription stays on the Model API in open mode
    transcribe_api_key: str = ""


class MuseError(Exception):
    pass


class Muse:
    def __init__(self, provider: Provider, timeout: float = 90):
        if not provider.api_key:
            raise MuseError(f"No API key for provider {provider.name!r} (see .env).")
        self.p = provider
        self._http = httpx.Client(timeout=timeout)

    # ---- raw calls --------------------------------------------------------------------

    def chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        r = self._http.post(
            f"{self.p.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.p.api_key}"},
            json={"model": self.p.model, "messages": messages, "temperature": temperature},
        )
        if r.status_code >= 400:
            raise MuseError(f"{self.p.name} {r.status_code}: {r.text[:300]}")
        try:
            return r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise MuseError(f"Unexpected reply shape from {self.p.name}: {e}") from e

    def chat_tools(self, messages: list[dict], tools: list[dict], temperature: float = 0.3) -> dict:
        """One chat turn with function tools. Returns the assistant message (may carry tool_calls)."""
        r = self._http.post(
            f"{self.p.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.p.api_key}"},
            json={"model": self.p.model, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": temperature},
        )
        if r.status_code >= 400:
            raise MuseError(f"{self.p.name} {r.status_code}: {r.text[:300]}")
        try:
            return r.json()["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as e:
            raise MuseError(f"Unexpected reply shape from {self.p.name}: {e}") from e

    def transcribe(self, audio: bytes, filename: str = "capture.webm") -> str:
        key = self.p.transcribe_api_key or self.p.api_key
        r = self._http.post(
            f"{self.p.transcribe_base_url}/asr/transcribe",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (filename, audio)},
            data={"model": self.p.transcribe_model},
        )
        if r.status_code >= 400:
            raise MuseError(f"transcribe {r.status_code}: {r.text[:300]}")
        j = r.json()
        text = j.get("text") or " ".join(s.get("text", "") for s in j.get("segments", []))
        if not text.strip():
            raise MuseError("Transcription came back empty.")
        return text.strip()

    # ---- tasks ------------------------------------------------------------------------

    def breakdown(self, *, title: str, why: str | None, current_step: str | None, stalled_days: int,
                  rejected: list[str], history: list[str], profile: str, prior_assumption: str) -> Breakdown:
        user = {
            "quest": title,
            "why_it_matters": why or "",
            "current_step_that_stalled": current_step or "(none set)",
            "days_untouched": stalled_days,
            "recent_history_on_this_quest": history[-8:],
            "steps_the_user_rejected": rejected,
            "your_previous_assumption": prior_assumption,
            "about_the_user": profile,
        }
        text = self.chat([
            {"role": "system", "content": BREAKDOWN_SYSTEM},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ])
        return parse_breakdown(text)

    def capture_text(self, dump: str, profile: str) -> list[CapturedQuest]:
        text = self.chat([
            {"role": "system", "content": CAPTURE_SYSTEM},
            {"role": "user", "content": json.dumps({"brain_dump": dump, "about_the_user": profile}, ensure_ascii=False)},
        ])
        return parse_capture(text)

    def capture_image(self, image: bytes, mime: str, profile: str) -> list[CapturedQuest]:
        data_url = f"data:{mime};base64," + base64.b64encode(image).decode()
        text = self.chat([
            {"role": "system", "content": CAPTURE_SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": "This is a photo of my notes. Read everything that is a goal, task or intention and turn it into quests. " + (f"About me: {profile}" if profile else "")},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]},
        ])
        return parse_capture(text)


# ---- parsing ----------------------------------------------------------------------------

def _json_block(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise MuseError(f"No JSON in reply: {text[:200]!r}")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise MuseError(f"Bad JSON in reply: {e}") from e


def parse_breakdown(text: str) -> Breakdown:
    j = _json_block(text)
    step = str(j.get("step", "")).strip()
    if not 1 <= len(step) <= 200:
        raise MuseError(f"Step missing or too long: {step!r}")
    try:
        minutes = max(2, min(10, int(j.get("minutes", 5))))
    except (TypeError, ValueError):
        minutes = 5
    reason = str(j.get("reason", "")).strip() or f"Here's a {minutes}-minute way back in."
    return Breakdown(
        step=step, minutes=minutes, reason=reason[:600],
        assumption=str(j.get("assumption", "")).strip()[:200],
        needs_why=bool(j.get("needs_why", False)),
    )


def parse_capture(text: str) -> list[CapturedQuest]:
    j = _json_block(text)
    out: list[CapturedQuest] = []
    for q in j.get("quests", []) or []:
        title = str(q.get("title", "")).strip()[:500]
        if title:
            out.append(CapturedQuest(title=title, why=str(q.get("why", "")).strip()[:500], next_step=str(q.get("next_step", "")).strip()[:2000]))
    return out[:12]
