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
    enc = getattr(sys.stderr, "encoding", None) or "utf-8"
    try:
        line.encode(enc)
    except (UnicodeEncodeError, LookupError):   # a legacy code page (cp1252/437 when piped on Windows): degrade, don't crash
        line = line.translate(_ASCII).encode(enc, errors="replace").decode(enc, errors="replace")
    try:
        print(line, file=sys.stderr, flush=True)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"), file=sys.stderr, flush=True)


# Readable stand-ins for the few non-ASCII characters the console uses, so piped output stays legible.
_ASCII = str.maketrans({"─": "-", "→": "->", "—": "-", "–": "-", "•": "*", "…": "...", "‘": "'", "’": "'",
                        "“": '"', "”": '"', "✓": "v", "▶": ">"})
