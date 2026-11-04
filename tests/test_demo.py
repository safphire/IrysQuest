# SPDX-License-Identifier: AGPL-3.0-or-later
"""The judges' path: `irysquest demo` runs end to end with no accounts, keys or server."""

from irysquest import demo


def test_demo_runs_without_keys_and_shows_every_move(monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    out = demo.run(pace=0)
    first = {r.title: (r.move, r.outcome) for r in out["first"]}
    assert first["Learn to sing: one song by December"] == ("shrink_step", "proposed")
    assert first["Check out YouTube videos on Valorant"] == ("ask_why", "proposed")
    # after a refusal: a different angle, never the refused step
    (pilot,) = [r for r in out["second"] if r.title == "Finish the pilot script for Scriptory"]
    assert pilot.outcome == "proposed" and "paper" in pilot.step.lower()
    # momentum: the finished step brings the next one
    (sing,) = out["third"]
    assert sing.title.startswith("Learn to sing") and sing.outcome == "proposed"
    assert out["verdict"].verdict == "fine"
    # capture: the existing inbox quest is skipped, the why travels with the proposal
    outcomes = {c["title"]: c["outcome"] for c in out["captured"]}
    assert outcomes["Fix the bike"] == "already there" and outcomes["Learn the ukulele"] == "proposed"
    uke = next(p for p in out["proposals"] if p["quest"] == "Learn the ukulele")
    assert uke["reason"].startswith("Done looks like: Play one song")
