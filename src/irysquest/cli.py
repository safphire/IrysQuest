# SPDX-License-Identifier: AGPL-3.0-or-later
"""Command line entry point.

    irysquest login            sign in to the NextQuest server once (browser consent)
    irysquest today            tracked quests, steps, slots, streak, as the server sees them
    irysquest quests           list open quests
    irysquest tools            list the MCP tools the server offers
    irysquest dig              find stalled quests and propose a 2–10 minute step for each
    irysquest capture "text"   turn a brain dump into proposed quests
    irysquest reckon           the weekly reckoning: the whole board at once
    irysquest profile [text]   show or set what the agent knows about you
    irysquest rules [text]     show or set your standing rules for the coach
    irysquest serve            capture page + "dig now" + the morning schedule
"""

from __future__ import annotations

import argparse
import json
import sys

from . import config, oauth
from .agent import Agent
from .console import say
from .mcp_client import QuestClient
from .muse import Muse


def _client(settings: config.Settings) -> QuestClient:
    c = QuestClient(settings.mcp_url, settings.token_file)
    c.initialize()
    return c


def _agent(settings: config.Settings, provider: str | None) -> Agent:
    muse = Muse(settings.muse_provider(provider))
    return Agent(_client(settings), muse, settings.context_file, settings.stall_days)


def cmd_login(settings, args) -> int:
    oauth.login(settings.mcp_url, settings.token_file, open_browser=not args.no_browser)
    return 0


def cmd_today(settings, args) -> int:
    print(json.dumps(_client(settings).get_today(), indent=2, ensure_ascii=False))
    return 0


def cmd_quests(settings, args) -> int:
    print(json.dumps(_client(settings).list_quests(args.status), indent=2, ensure_ascii=False))
    return 0


def cmd_tools(settings, args) -> int:
    for t in _client(settings).list_tools():
        print(f"{t['name']:28} {t.get('description', '').splitlines()[0][:90]}")
    return 0


def cmd_dig(settings, args) -> int:
    _agent(settings, args.provider).dig(dry_run=args.dry_run, days=args.days)
    return 0


def cmd_reckon(settings, args) -> int:
    _agent(settings, args.provider).reckoning(dry_run=args.dry_run)
    return 0


def cmd_capture(settings, args) -> int:
    ag = _agent(settings, args.provider)
    quests = ag.muse.capture_text(args.text, ag.ctx.profile)
    ag.capture(quests, source="notes", preview=args.dry_run)
    return 0


def cmd_profile(settings, args) -> int:
    ag = _agent(settings, args.provider) if args.text else None
    if args.text:
        ag.set_profile(args.text)
    else:
        from . import context as ctx_store
        print(ctx_store.load(settings.context_file).profile or "(no profile yet)")
    return 0


def cmd_rules(settings, args) -> int:
    if args.text:
        _agent(settings, args.provider).set_rules(args.text)
    else:
        from . import context as ctx_store
        print(ctx_store.load(settings.context_file).rules or "(no rules yet)")
    return 0


def cmd_serve(settings, args) -> int:
    from .serve import serve
    serve(_agent(settings, args.provider), settings.serve_host, settings.serve_port, settings.dig_at, settings.try_it_token)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="irysquest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", default=None, help="path to a .env file (default: ./.env)")
    p.add_argument("--provider", choices=["meta", "open"], default=None, help="which Muse to use (default: MUSE_PROVIDER)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("login", help="sign in to the server once")
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(fn=cmd_login)
    sub.add_parser("today", help="tracked quests and their next steps").set_defaults(fn=cmd_today)
    s = sub.add_parser("quests", help="list quests")
    s.add_argument("--status", choices=["inbox", "tracked", "later", "done", "dropped"], default=None)
    s.set_defaults(fn=cmd_quests)
    sub.add_parser("tools", help="list the server's MCP tools").set_defaults(fn=cmd_tools)

    s = sub.add_parser("dig", help="find stalled quests and propose a first step for each")
    s.add_argument("--dry-run", action="store_true", help="show what would be proposed, propose nothing")
    s.add_argument("--days", type=int, default=None, help="stall threshold in days (default: STALL_DAYS)")
    s.set_defaults(fn=cmd_dig)

    s = sub.add_parser("reckon", help="weekly reckoning: look at all tracked quests together")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_reckon)

    s = sub.add_parser("capture", help="turn a brain dump into proposed quests")
    s.add_argument("text")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_capture)

    s = sub.add_parser("profile", help="show or set what the agent knows about you")
    s.add_argument("text", nargs="?", default=None)
    s.set_defaults(fn=cmd_profile)

    s = sub.add_parser("rules", help="show or set your standing rules for the coach")
    s.add_argument("text", nargs="?", default=None)
    s.set_defaults(fn=cmd_rules)

    sub.add_parser("serve", help="capture page, dig now, and the morning schedule").set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    settings = config.load(args.env)
    try:
        return args.fn(settings, args)
    except KeyboardInterrupt:
        say("Stopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
