# Verification

Runs of IrysQuest against the real NextQuest server and the real Meta Model API.

## 30 Oct 2026 — first end-to-end run (Windows 11, Python 3.12)

Starting point: `501993e` (the coach). The local checkout was two commits behind `origin/main` with rewritten
hashes but identical trees; it was reset to `origin/main` (old tip kept as `backup/pre-sync-33d6e9d`).

### Worked first time

- `irysquest today`: real tracked quest, slots, touched_at.
- `irysquest profile` / `irysquest rules`: stored in `context.json` (run from PowerShell; Git Bash mangles `–` in argv).
- `irysquest dig --dry-run --days 0`: Muse Spark tool calling accepted with no schema changes. In all 4 runs the
  coach called `get_quest`, `get_history` and `list_decisions` before `shrink_step`; steps followed the profile
  (5 minutes, physical); it never parked the quest the rules protect.
- `irysquest dig --days 0`: one `set_next_step` proposal, reason includes the stated assumption.
- Pending proposal for a quest → that quest is skipped on the next run.
- `irysquest capture` (dry run and real): 4 quests from the 4-item dump, each with a 2–5 minute first step;
  4 pending `add_quest` proposals. `track=False` is sent explicitly (`agent.py`); `list_proposals` doesn't
  return the payload, so the flag can't be read back from the server.
- `Muse.capture_image` with `tests/fixtures/notes.jpg`: all four handwritten lines read correctly, heading ignored.
- `irysquest serve`: `/health`, `POST /text`, `POST /dig?dry=1`, `GET /log` all OK; page has the Rules box.

### Fixed

- `7ac8057` `context.json` read/written with the platform encoding (cp1252 on Windows): every dig and capture
  crashed on "→". Now UTF-8. (5 of 12 tests failed before this.)
- `118aa89` The server lists proposals with op `set_next_step` / `park_quest`, not the tool name
  `propose_set_next_step`. Rejected steps and rejected parks were never noticed, so not fed back to the coach or
  kept in `context.json`. The fake server now reports ops like the real one. After the fix, a rejected step
  appeared under the quest in `context.json`, and the coach switched approach (`ask_why`) instead of repeating it.
- `a176738` `/v1/asr/transcribe` needs a JSON `request` part (`model`, `audioEncoding: "WAV"`) and an `audio`
  part, and replies with `transcript`. A 3.3 s Windows TTS WAV now transcribes exactly.
- `535d877` Added `tests/fixtures/notes.jpg` (rendered with PIL from the system Python; no new dependency).

### Needs a decision

- **Voice capture from the phone can't work yet.** The API accepts only mono 16-bit PCM WAV at 16 or 24 kHz
  (22.05 kHz was rejected: "expected mono s16le at 16000 or 24000 Hz"). The page records with `MediaRecorder`,
  which gives webm/opus (Android Chrome) or mp4 (Safari). Options: encode 16 kHz WAV in the page with the Web
  Audio API (no dependency, ~30 lines of JS), or convert on the PC with ffmpeg (new dependency).
- Cosmetic: when stderr is redirected on Windows, "→" in console lines prints as `→`
  (`PYTHONIOENCODING=utf-8` avoids it). A real console is fine.

### Left on the server from this run

Pending proposals: the `ask_why` step on the Kurzgesagt quest, the four captured quests, and
"water the balcony plants every Sunday" from the `/text` check.
