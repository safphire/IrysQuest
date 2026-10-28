# SPDX-License-Identifier: AGPL-3.0-or-later
"""Command line entry point.

    irysquest login     sign in to the NextQuest server once (browser consent)
    irysquest today     what the server sees: tracked quests, steps, slots, streak
    irysquest quests    list open quests
    irysquest tools     list the MCP tools the server offers
    irysquest dig       find stalled quests and propose a 2–10 minute step for each
"""

from __future__ import annotations

import argparse
import json
import sys

from . import config, oauth
from .console import say
from .mcp_client import QuestClient, ToolError
from .muse import Muse, MuseError
from .stalls import find_stalls


def _client(settings: config.Settings) -> QuestClient:
    c = QuestClient(settings.mcp_url, settings.token_file)
    c.initialize()
    return c


def cmd_login(settings: config.Settings, args: argparse.Namespace) -> int:
    oauth.login(settings.mcp_url, settings.token_file, open_browser=not args.no_browser)
    return 0


def cmd_today(settings: config.Settings, args: argparse.Namespace) -> int:
    today = _client(settings).get_today()
    print(json.dumps(today, indent=2))
    return 0


def cmd_quests(settings: config.Settings, args: argparse.Namespace) -> int:
    quests = _client(settings).list_quests(args.status)
    print(json.dumps(quests, indent=2))
    return 0


def cmd_tools(settings: config.Settings, args: argparse.Namespace) -> int:
    for t in _client(settings).list_tools():
        print(f"{t['name']:28} {t.get('description', '').splitlines()[0][:90]}")
    return 0


def cmd_dig(settings: config.Settings, args: argparse.Namespace) -> int:
    c = _client(settings)
    say("Reading your tracked quests.")
    today = c.get_today()
    proposals = []
    for st in ("pending", "rejected"):
        proposals += c.list_proposals(st).get("proposals", [])
    stalls = find_stalls(today, proposals, args.days or settings.stall_days)
    say(f"{today['slots_used']}/{today['slot_cap']} slots used; {len(stalls)} stalled for {args.days or settings.stall_days}+ days.")
    if not stalls:
        say("Nothing is buried. See you tomorrow.")
        return 0
    muse = Muse(settings.meta_api_key)
    made = 0
    for s in stalls:
        say(f'"{s.title}" untouched {s.days} days (step: {s.current_step or "none"}). Asking Muse Spark for a smaller first move.')
        try:
            b = muse.breakdown(s.title, s.why, s.current_step, s.days, s.rejected)
        except MuseError as e:
            say(f"  Muse couldn't help this time: {e}")
            continue
        say(f'  → "{b.step}" ({b.minutes} min). {b.reason}')
        if args.dry_run:
            continue
        reason = f"{b.reason} (Untouched for {s.days} days; about {b.minutes} minutes.)"
        try:
            r = c.propose_set_next_step(s.quest_id, b.step, reason=reason)
            say(f"  Proposed. Waiting for you in the app ({r.get('proposal_id')}).")
            made += 1
        except ToolError as e:
            say(f"  Server declined: {e}")
    say("Dry run: nothing was proposed." if args.dry_run else f"{made} proposal(s) waiting for your call.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="irysquest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default=None, help="path to a .env file (default: ./.env)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("login", help="sign in to the server once")
    s.add_argument("--no-browser", action="store_true", help="print the consent URL instead of opening a browser")
    s.set_defaults(fn=cmd_login)

    s = sub.add_parser("today", help="tracked quests and their next steps")
    s.set_defaults(fn=cmd_today)

    s = sub.add_parser("quests", help="list quests")
    s.add_argument("--status", choices=["inbox", "tracked", "later", "done", "dropped"], default=None)
    s.set_defaults(fn=cmd_quests)

    s = sub.add_parser("tools", help="list the server's MCP tools")
    s.set_defaults(fn=cmd_tools)

    s = sub.add_parser("dig", help="find stalled quests and propose a first step for each")
    s.add_argument("--dry-run", action="store_true", help="show what would be proposed, propose nothing")
    s.add_argument("--days", type=int, default=None, help="stall threshold in days (default: STALL_DAYS)")
    s.set_defaults(fn=cmd_dig)

    args = p.parse_args(argv)
    settings = config.load(args.env)
    try:
        return args.fn(settings, args)
    except KeyboardInterrupt:
        say("Stopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
