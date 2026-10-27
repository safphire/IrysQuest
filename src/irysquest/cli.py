# SPDX-License-Identifier: AGPL-3.0-or-later
"""Command line entry point.

    irysquest login     sign in to the NextQuest server once (browser consent)
    irysquest today     what the server sees: tracked quests, steps, slots, streak
    irysquest quests    list open quests
    irysquest tools     list the MCP tools the server offers
"""

from __future__ import annotations

import argparse
import json
import sys

from . import config, oauth
from .console import say
from .mcp_client import QuestClient


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

    args = p.parse_args(argv)
    settings = config.load(args.env)
    try:
        return args.fn(settings, args)
    except KeyboardInterrupt:
        say("Stopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
