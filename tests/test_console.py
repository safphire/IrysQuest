# SPDX-License-Identifier: AGPL-3.0-or-later
import io
import sys

from irysquest import console


def _capture(monkeypatch, encoding: str) -> str:
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding=encoding, errors="backslashreplace")
    monkeypatch.setattr(sys, "stderr", stream)
    console.say("─── → step — done • ok…")
    stream.flush()
    return raw.getvalue().decode(encoding)


def test_piped_legacy_code_page_stays_readable(monkeypatch):
    out = _capture(monkeypatch, "cp1252")
    assert "\\u" not in out
    assert "--- -> step - done * ok..." in out


def test_utf8_keeps_the_real_characters(monkeypatch):
    assert "─── → step" in _capture(monkeypatch, "utf-8")
