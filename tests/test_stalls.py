# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from irysquest.muse import MuseError, parse_breakdown
from irysquest.stalls import find_stalls

NOW = datetime(2026, 10, 28, 9, 0)


def quest(qid, title, touched, step="do it"):
    return {"id": qid, "title": title, "touched_at": touched, "next_step": {"id": "s", "text": step} if step else None}


def test_only_old_untouched_quests_stall():
    today = {"tracked": [quest("a", "Sing", "2026-10-20T08:00:00"), quest("b", "Ship", "2026-10-27T09:00:00")]}
    stalls = find_stalls(today, [], stall_days=3, now=NOW)
    assert [s.quest_id for s in stalls] == ["a"]
    assert stalls[0].days == 8 and stalls[0].current_step == "do it"


def test_pending_proposal_skips_and_rejections_carry_over():
    today = {"tracked": [quest("a", "Sing", "2026-10-20T08:00:00"), quest("b", "Draw", "2026-10-19T08:00:00")]}
    proposals = [
        {"status": "pending", "op": "propose_set_next_step", "quest": "Sing", "after": "x"},
        {"status": "rejected", "op": "propose_set_next_step", "quest": "Draw", "after": "Buy a sketchbook"},
    ]
    stalls = find_stalls(today, proposals, stall_days=3, now=NOW)
    assert [s.title for s in stalls] == ["Draw"]
    assert stalls[0].rejected == ["Buy a sketchbook"]


def test_parse_breakdown_tolerates_prose_and_clamps():
    b = parse_breakdown('Sure! {"step": "Hum one scale", "minutes": 30, "reason": "Tiny start."}')
    assert b.step == "Hum one scale" and b.minutes == 10 and b.reason == "Tiny start."


def test_parse_breakdown_rejects_garbage():
    try:
        parse_breakdown("I cannot help with that.")
    except MuseError:
        return
    raise AssertionError("expected MuseError")


def test_needs_next_step_counts_whatever_its_age():
    from datetime import datetime
    from irysquest.stalls import find_stalls
    now = datetime(2026, 11, 3, 18, 0)
    today = {"tracked": [
        {"id": "a", "title": "Fresh", "touched_at": "2026-11-03T17:00:00", "next_step": None, "needs_next_step": True},
        {"id": "b", "title": "Old", "touched_at": "2026-10-20T08:00:00", "next_step": {"text": "x"}},
        {"id": "c", "title": "Fresh too", "touched_at": "2026-11-03T17:00:00", "next_step": {"text": "y"}},
    ]}
    st = find_stalls(today, [], 3, now)
    assert [s.title for s in st] == ["Fresh", "Old"] and st[0].needs_next_step is True
