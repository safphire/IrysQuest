# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seed a demo board: three realistic quests, proposed to the NextQuest server. MOCK DATA.

    python scripts/seed_demo.py            # uses ./.env and the agent's sign-in

The quests are invented for demos and screenshots; each proposal's reason says so.
Like every agent write, they are only *proposals* with track=False: accept them on
the phone and track them yourself, then the board has something to reckon with.

Limitation: the server stamps `touched_at` itself when the quest is created or
changed. The agent can't backdate it, so a freshly seeded quest is 0 days old and
nothing on a seeded board looks stalled until real days pass. Use
`irysquest dig --days 0` to treat everything as stalled when demoing.
"""

from __future__ import annotations

import sys

from irysquest import config
from irysquest.mcp_client import QuestClient, ToolError

DEMO = [
    {
        "title": "Finish the pilot script for Scriptory",
        "why": "A finished pilot is the one thing I can send to people; outlines don't count.",
        "next_step": "Open the draft and reread the last scene",
    },
    {
        "title": "Fix the bike brake",
        "why": "So I can ride to work again instead of taking the bus.",
        "next_step": "Squeeze the front lever and see if the pads touch the rim",
    },
    {
        "title": "Learn to sing: one song by December",
        "why": "Sing one whole song at the family get-together without my voice cracking.",
        "next_step": "Pick the song and play it once",
    },
]

REASON = "Demo board seed (mock data from scripts/seed_demo.py), not a real capture."


def main() -> int:
    settings = config.load()
    client = QuestClient(settings.mcp_url, settings.token_file)
    client.initialize()
    ok = True
    for q in DEMO:
        try:
            r = client.propose_add_quest(q["title"], reason=REASON, why=q["why"], next_step=q["next_step"], track=False)
            print(f"{r.get('proposal_id') or r.get('id')}  {q['title']}")
        except ToolError as e:
            ok = False
            print(f"declined  {q['title']}: {e}", file=sys.stderr)
    print("\nAccept these in the app's Proposals screen, then track them.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
