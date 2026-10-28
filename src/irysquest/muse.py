# SPDX-License-Identifier: AGPL-3.0-or-later
"""Muse Spark through the Meta Model API (OpenAI-compatible chat completions).

One job: given a stalled quest, return a first step that takes 2–10 minutes.
Everything is asked for as JSON and parsed defensively, because a breakdown
that can't be parsed must never become a half-formed proposal.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

BASE_URL = "https://api.meta.ai/v1"
MODEL = "muse-spark-1.3"

SYSTEM = """You are a coach inside a personal quest log. The user keeps at most five tracked quests, each with exactly one visible next step. A quest has stalled: its step hasn't moved in days. Your job is to propose a NEW first step that is so small the user can do it in 2 to 10 minutes, today, with what they already have. Shrink, don't plan: one concrete physical or on-screen action, no lists, no "research", no "think about". Reply with JSON only:
{"step": "<the action, imperative, under 90 characters>", "minutes": <2-10>, "reason": "<one sentence to the user: why this step, warm and plain, no guilt>"}"""


@dataclass
class Breakdown:
    step: str
    minutes: int
    reason: str


class MuseError(Exception):
    pass


class Muse:
    def __init__(self, api_key: str, base_url: str = BASE_URL, model: str = MODEL, timeout: float = 60):
        if not api_key:
            raise MuseError("META_API_KEY is not set (see .env).")
        self.model = model
        self._http = httpx.Client(
            base_url=base_url, timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    def chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        r = self._http.post("/chat/completions", json={"model": self.model, "messages": messages, "temperature": temperature})
        if r.status_code >= 400:
            raise MuseError(f"Muse {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"]

    def breakdown(self, title: str, why: str | None, current_step: str | None, stalled_days: int, rejected: list[str]) -> Breakdown:
        user = {
            "quest": title,
            "why_it_matters": why or "",
            "current_step_that_stalled": current_step or "(none set)",
            "days_untouched": stalled_days,
            "steps_the_user_already_rejected": rejected,
        }
        text = self.chat([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ])
        return parse_breakdown(text)


def parse_breakdown(text: str) -> Breakdown:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise MuseError(f"No JSON in Muse reply: {text[:200]!r}")
    try:
        j = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise MuseError(f"Bad JSON from Muse: {e}") from e
    step = str(j.get("step", "")).strip()
    if not 1 <= len(step) <= 200:
        raise MuseError(f"Step missing or too long: {step!r}")
    try:
        minutes = max(2, min(10, int(j.get("minutes", 5))))
    except (TypeError, ValueError):
        minutes = 5
    reason = str(j.get("reason", "")).strip() or f"Untouched for a while; here's a {minutes}-minute way back in."
    return Breakdown(step=step, minutes=minutes, reason=reason[:1000])
