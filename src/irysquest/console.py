# SPDX-License-Identifier: AGPL-3.0-or-later
"""The agent console: short, plain sentences about what the agent is doing.

Everything the agent decides is said out loud here, so a person watching
(or a demo recording) can follow its reasoning without reading logs.
"""

from __future__ import annotations

import sys
from datetime import datetime


def say(text: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {text}"
    try:
        print(line, file=sys.stderr, flush=True)
    except UnicodeEncodeError:   # a legacy console code page (e.g. cp1252 when piped on Windows): degrade, don't crash
        enc = getattr(sys.stderr, "encoding", None) or "ascii"
        print(line.encode(enc, errors="replace").decode(enc, errors="replace"), file=sys.stderr, flush=True)
