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
- Cosmetic: when stderr is redirected on Windows, "→" in console lines prints as `\u2192`
  (`PYTHONIOENCODING=utf-8` avoids it). A real console is fine.

### Left on the server from this run

Pending proposals: the `ask_why` step on the Kurzgesagt quest, the four captured quests, and
"water the balcony plants every Sunday" from the `/text` check.

## 31 Oct 2026 — voice decision

- Voice: converted in the browser (D-16). Checked in a Chromium page running the real page script: an 8 kHz
  stereo WAV and a `MediaRecorder` webm/opus clip both came out as mono 16-bit 16 kHz WAV, and the converted
  speech transcribed correctly through `Muse.transcribe`. An undecodable recording shows the decoder's error in
  the Result box. Not yet tried on a real phone through `serve`: the ngrok tunnel was offline at the time.
- The `\u2192` arrow under redirection stays as is.
- Seen in passing: when the server is unreachable, a failed token refresh says "Session expired … run
  `irysquest login`" even though the tokens are fine (here ngrok's 404, ERR_NGROK_3200).

## 1 Nov 2026 — reckoning, demo board, voice from a real phone, try-it, open-weight tests

Starting point: `9b00e75` (the weekly reckoning). 15 tests passed after `pip install -e ".[dev]"`; 21 at the end.

### Weekly reckoning and the demo board

- `irysquest reckon --dry-run` with 1 tracked quest: **fine**, "Only one quest is tracked; nothing can crowd it
  out." That path returns before calling Muse and doesn't print its board_read ("A quiet board.").
- `scripts/seed_demo.py` proposed three quests (pilot script, bike brake, one song by December) with
  `track=False`; the user accepted two, rejected the bike brake, and also accepted the Valorant quest from the voice
  test below, then tracked all of them: 4/5 slots.
- `irysquest reckon --dry-run` with 4 tracked quests: Muse was called; **fine**, board_read "This week feels
  fresh and open with room to keep exploring." Reason: all four were touched recently.
- `irysquest dig --dry-run --days 0`: the coach called `get_quest`, `get_history` and `list_decisions` for every
  quest before deciding. Three `shrink_step`s at 5 minutes, each with an assumption that matches the quest's why
  (e.g. "to have a finished pilot you can send to people"); for the Valorant quest, which has no why, it chose
  `ask_why`. Nothing proposed.
- **Limitation of mock data:** the server stamps `touched_at` itself, so the agent can't backdate a seeded quest.
  Every seeded quest is 0 days old, `dig` needs `--days 0` to see anything, and the reckoning can only say "fine"
  until real days pass. A park verdict on a demo board needs a week or two of real use.

### Voice from a real phone (Chrome on Android, same LAN; browser confirmed by the user, not logged)

- Plain `http://192.168.0.53:8787/`: tapping Record did nothing, no permission prompt. `getUserMedia` exists only
  in a secure context, which a LAN IP over http is not, and the page threw an uncaught TypeError.
- Fixed by `baf57c7` (`serve --https`, self-signed certificate via openssl, D-18) and `b43f633` (the page says
  why recording can't start). Python's `cryptography` is not installed; Git for Windows' openssl was on PATH.
- Over `https://192.168.0.53:8787/`, after accepting the certificate warning once: 275 KB of WAV from the phone,
  transcribed as "I would like to check out YouTube videos on Valorant.", one quest, one pending `add_quest`
  proposal on the server. **Voice capture now works end to end on a real phone.**
- `0e33635`: the phone retries while it refuses the certificate, and plain http to the https port fails the
  handshake. One session left 369 tracebacks (~600 KB) in the console; these are now dropped quietly.

### Try-it mode

`TRY_IT_TOKEN` set in `.env` (12 random alphanumerics), `serve --https` restarted, checked with curl:

- visitor `POST /text?try=…`: 200, both quests `"outcome": "preview"`;
- visitor `POST /dig?try=…` and `POST /dig?dry=1&try=…`: 403 "Visitors can only preview captures.";
- visitor `GET /log?try=…`: empty log, no profile or rules;
- pending proposals on the server unchanged.

### Open-weight mode

Not run on real weights; no model was pulled. `tests/test_open_provider.py` runs `Muse.chat`,
`Muse.chat_tools` and `Coach.decide` against a local fake of the OpenAI-compatible `/v1/chat/completions` (as
Ollama and vLLM expose it), including a `tool_calls` reply fed back as a `tool` message and a 404 "model not
found". How to run it for real: `docs/OPEN_WEIGHT.md`.

### Needs a decision

- The try-it banner says "Nothing is saved or sent anywhere", but a visitor's words go to the Meta API and their
  previewed quests are written to the owner's console log in `context.json`. Reword the banner, or keep visitor
  captures out of the log.
- Without `?try=`, anyone who can reach the page has owner access (Dig now, profile, rules). Fine on a home LAN;
  worth knowing before sharing the address more widely.
- The README calls the open model "Muse Spark Open" (`muse-spark-open-1026`); the new docs say Muse Glimmer.

### Left on the server from this run

Nothing pending. Four tracked quests: the Kurzgesagt quest, Valorant (voice test), the pilot script and one song
by December (both demo data). The bike-brake demo proposal was rejected.

## 1 Nov 2026 (evening) — decisions applied, publication checks

Starting point: `f527cc2`. 27 tests at the end (21 before), all passing.

### Decisions applied

- `991a185` Try-it: a visitor's requests no longer reach the owner's log or `context.json`; the banner now says
  "Your words go to Meta's model to produce the preview; nothing is saved to the quest log." Checked live on the
  restarted `serve --https`: visitor `POST /text` returned a preview, `context.json` kept the same number of log
  entries (95 → 95) with no trace of the visitor's words, `/dig` still 403. The PC's console still echoes the
  visitor's text (stderr, not saved by the agent); if stderr is redirected to a file, it lands there.
- `f3b9cbb` The open-weight model is Muse Glimmer everywhere; `OPEN_MODEL` defaults to `muse-glimmer`, with
  `meta-models/muse-spark-open-1026` as a commented alternative in `.env.example`.
- `ed599f9` A quest whose step is the unanswered why-question (empty Why) is left alone without calling Muse.
  This is the Kurzgesagt case from the earlier run, where the coach replaced its own question with a shrink step.
- `23acd72` The phone in the voice check was Chrome on Android (confirmed by the user; the server doesn't log
  User-Agent).
- The README's "Verified on a real phone end to end" stays unticked until photo and Dig now are tried from the
  phone.

### Fixes from the earlier known-issues list

- `096b7f6` A failed token refresh says "Session expired" only for a 400/401 `invalid_grant`; a tunnel's 404,
  a 5xx or a connection error says "Server unreachable … your sign-in is kept". Tested with all four cases.
- `01c4ac5` Single-quest reckoning prints its board read and verdict line.
- `972bc03` pytest-asyncio removed (no async tests; it only printed a deprecation warning).
- The local clone had no fetch refspec for `origin`; added (`+refs/heads/*:refs/remotes/origin/*`) and `main`
  now tracks `origin/main`. Local git config only, nothing committed.

### Publication checks (nothing made public)

- **gitleaks 8.30.1** (installed with winget): `gitleaks git .` over the full history, 32 commits, **no leaks**.
  `gitleaks dir .` over the working tree found 3, all in gitignored, untracked files: `.env`,
  `.irysquest/tokens.json` and `.irysquest/tls/key.pem`. Also checked by counts only: the API key, its 8-character
  prefix and the try-it token appear 0 times in `git log -p --all`; `.env` and `.irysquest/` were never committed.
- **Licences** (`pip-licenses` in the venv only): `docs/THIRD_PARTY_LICENSES.md` (`6026b1f`). All runtime
  dependencies are MIT, BSD-3-Clause or PSF-2.0 except **certifi (MPL-2.0)**, the CA bundle, used unmodified;
  MPL-2.0 is compatible with the AGPL.
- **SPDX headers**: every tracked Python file had one except the empty `tests/__init__.py`; it and
  `pyproject.toml` got one (`ce38eff`).
- **`tests/fixtures/notes.jpg`**: generated (PIL, `535d877`), 900×620, JFIF header only, no EXIF. Content is four
  invented goals in a handwriting-style font; no personal data.
- **README** (`3b10204`): "Running it yourself (judges)" from clone to first dig, including the NextQuest server
  (repo, `docker compose up -d`, HTTPS tunnel, pairing the app), and "What to look at".

### Running overnight

`irysquest serve --https` was restarted at 15:43 as a detached process (console in
`%TEMP%\irysquest-serve.err.log`) so the scheduled dig fires on Mon 2 Nov at 08:00. Not yet observed: check for
"Morning. Checking what's buried." in that file or on the page's console.

## 1 Nov (evening): research layer, Sunday reckoning, photo input

Run on Sun 1 Nov 2026, 16:50–17:00, Windows 11, against the real NextQuest server (ngrok) and the real Meta Model
API. Commits under test: `4ffb274`, `986f50a`, `0b2f948`. Dry runs only; nothing was proposed. Tally: 10 PASS,
0 FAIL, 5 FINDING.

**Setup**
- 1 Nov · 1 PASS — `git pull` fast-forwarded to `0b2f948`; `git status` clean.
- 1 Nov · 2 FINDING — `pip install -e ".[dev]"` failed with "[WinError 5] Access is denied:
  …\.venv\scripts\irysquest.exe" because the running serve held the exe; the half-done install left `irysquest`
  unimportable (pytest: 5 errors). After stopping serve, reinstall OK and **29 passed**. pip now warns "Ignoring
  invalid distribution ~rysquest" (leftover folder in site-packages, harmless). Stop serve before reinstalling.
- 1 Nov · 3 PASS — `curl http://localhost:8080/health` → `{"ok":true,"name":"NextQuest"}` (200); `irysquest today`
  → 4/5 slots, Kurzgesagt, Valorant, Learn to sing, Pilot script. The old serve (3 processes) was stopped.

**A. Research layer (`986f50a`)**
- 1 Nov · 4 PASS — `dig --dry-run --days 0`. Kurzgesagt: not handed to the coach ("still waiting for its why …
  Leaving it alone", the `ed599f9` guard). The other three: "Looked at: get_quest, get_history, list_decisions."
  - Valorant → leave_alone: "Assuming it's for a fun break exploring Valorant, this one is brand new from today
    with a clear first move, so giving it space to get started."
  - Learn to sing → leave_alone: "This one is fresh from today, to sing confidently for family in December, and
    picking the song and playing it once is already a kind first start, so I'll let you enjoy it."
  - Pilot script → shrink_step: "Copy your favourite line from the last scene by hand and add the next 2 lines on
    paper (at 9:30, at the desk as build block starts)" (5 min); reason: "Paper is an easy way in, and a few minutes
    of writing keeps the pilot alive and moving toward sendable." **Cue present on 1 of 1 shrink_step.**
  - Banned words (overdue, failed, missed, lazy, behind, again; case-insensitive, whole words): no hits. "streak":
    no hits.
- 1 Nov · 5 PASS — `last_proposed_at` in `context.json` unchanged by the dry run for all four quests (three empty,
  Kurzgesagt `2026-10-30T21:23:36`). The `inspect` check printed `True True`.
- 1 Nov · 6a PASS — `_days_since_any_activity` defined at `agent.py:203`, called at `agent.py:78`
  (`away_days = …`), passed to the coach at `agent.py:97` as `"days_since_user_did_anything": away_days`
  (`is_monday` at line 98).
- 1 Nov · 6b FINDING — second `dig --dry-run --days 0`: no "You've been away" line (the user was active today,
  so away_days < 2) and the forgiveness path wasn't exercised. Tone is gentle but not a welcome-back, e.g. Learn to
  sing: "This one is brand new today to sing confidently for family in December, so leaving it fresh for you to pick
  the song in your own time." The Pilot script went from shrink_step (run 1) to leave_alone (run 2). No banned words
  or "streak" in run 2. Testing forgiveness live needs a quest log with a gap of 2+ days.

**B. Weekly reckoning on a Sunday (D-17)**
- 1 Nov · 7 PASS — `reckon --dry-run`: board read "The board looks alive with a little movement everywhere this
  week."; verdict **fine**, no quest named; reason "All four quests were touched recently and there's still an open
  slot, so nothing is in the way." No banned words.

**C. Photo input (`4ffb274`)**
- 1 Nov · 8 PASS — `serve --https` started in its own console window ("IrysQuest serve"). The desktop app's
  built-in browser refuses the self-signed certificate (ERR_CERT_AUTHORITY_INVALID) and can't proceed past it, so
  the page source was fetched with `curl --cacert .irysquest/tls/cert.pem https://localhost:8787/` (verified TLS,
  200). Tag: `<input id="photo" type="file" accept="image/*">`, no `capture` attribute.
- 1 Nov · 9 PASS — `/log` (what the page's console pane shows) returned 60 lines; last three:
  "Board: The board looks alive with a little movement everywhere this week." / "→ the board is fine. All four quests
  were touched recently and there's still an open slot, so nothing is in the way." / "reckoning:fine:".

**D. Scheduler readiness**
- 1 Nov · 10 FINDING — startup line: "[16:56:17] Next scheduled dig at Mon 08:00." `.env` has **no** `DIG_AT=`
  line; the default in `config.py:70` (`"08:00"`) applies, so the schedule is right but not pinned in `.env`.
  Serve left running for Monday.

**E. Hygiene**
- 1 Nov · 11 PASS — `git log --oneline -3`: `0b2f948`, `986f50a`, `4ffb274`; `git status` clean before this entry.
- 1 Nov · 12 PASS — `git check-ignore -v` lists all three: `.env` (rule `.env`), `.irysquest/tokens.json` and
  `.irysquest/tls/cert.pem` (rule `.irysquest/`). There is no `*.pem` rule; the certificate is covered by
  `.irysquest/`.

**Also found**
- 1 Nov · FINDING — **Dry runs write to `context.json`.** Valorant has `asked_for_why: true` but no
  `last_proposed_at`. That flag came from the 15:03 dry run (coach chose ask_why), so run 2 overrode the coach with
  "I've already asked what this is for; I'll wait for the why." The quest can't get its why-question though none
  was ever proposed. In `dig`, `asked_for_why` and the assumption/intent notes are set before the `if dry_run:`
  check (`agent.py:158`) and saved at the end. Smallest fix: set them only after a proposal succeeds.
- 1 Nov · FINDING — The console pane shows the internal marker "reckoning:fine:" (from
  `ctx.remember(f"reckoning:{v.verdict}:{title}", "reckoning")`). Cosmetic; filter kind "reckoning" out of `/log`
  or word it for people.

## 1 Nov (late): the scheduled dig fires on its own

Run on Sun 1 Nov 2026, 17:40–17:50, Windows 11, `dd8a3a3`, real NextQuest server (ngrok) and real Meta Model API.
Only the scheduled run was allowed to propose; it proposed nothing (see 7b). Tally: 11 PASS, 0 FAIL, 5 FINDING.

**Setup**
- 1 Nov · 1 PASS — Stopped the "IrysQuest serve" console (cmd, irysquest, tee, 2× python); nothing listened on 8787.
- 1 Nov · 2 PASS — `git pull` → `dd8a3a3` (includes `830c78f`); `pip install -e ".[dev]"` with serve stopped;
  `pytest -q` → **30 passed**.
- 1 Nov · 3 PASS — `/health` → `{"ok":true,"name":"NextQuest"}`. Before: 4/5 slots — Kurzgesagt-technique learning
  animations (touched 31 Oct 17:46), Check out YouTube videos on Valorant, Learn to sing: one song by December,
  Finish the pilot script for Scriptory (all three 1 Nov 15:02).
- 1 Nov · 4 PASS — Pending before: **1** ("Read the book 'Lean startup' from page 180", not from the agent).

**A. Fire the schedule**
- 1 Nov · 5 FINDING — The suggested `Start-Process powershell -ArgumentList '-NoExit','-Command','…'` line does not
  survive Windows argument quoting: the inner double quotes are dropped, so the new shell parsed
  `$Host.UI.RawUI.WindowTitle=IrysQuest serve;`, which *runs* `irysquest serve` (the global Python's editable
  install, before activation, no `--https`, output captured into the title) and blocks; the `cd`, activate,
  `DIG_AT` and `Tee-Object` never ran. That process served plain http on the default 08:00 schedule. Stopped it
  and relaunched the identical commands with `-EncodedCommand` (base64 UTF-16LE), which keeps the quoting.
- 1 Nov · 6 PASS — `DIG_AT=17:49` for that window only. Startup line within 10 s: "[17:45:52] Next scheduled dig at
  Sun 17:49." Process: `.venv\Scripts\irysquest.exe serve --https`.
- 1 Nov · 7 PASS — Fired on its own at 17:48:59 (the timer wakes up to a second early), ran a real dig, then the
  Sunday reckoning ("Board:" line and a **fine** verdict), then re-armed: "Next scheduled dig at Mon 17:49." No
  banned words (overdue, failed, missed, lazy, behind, again, streak; whole words, case-insensitive) in any line.
  `.irysquest\serve.log`, verbatim (Windows PowerShell's `Tee-Object` garbles "→" into "ΓåÆ"; `/log` has the arrow):

  ```
  [17:48:59] Morning. Checking what's buried.
  [17:48:59] Reading your tracked quests.
  [17:49:00] 4/5 slots used; 0 stalled for 3+ days.
  [17:49:00] Nothing is buried. See you tomorrow.
  [17:49:00] Weekly reckoning: looking at the whole board, not one quest.
  [17:49:09]   Board: Everything on the board feels fresh and in motion this week.
  [17:49:09]   ΓåÆ the board is fine. All four quests have moved in the last day, so there's nothing to put aside.
  [17:49:09] Next scheduled dig at Mon 17:49.
  ```
- 1 Nov · 7b FINDING — The scheduled dig uses `STALL_DAYS` from `.env` (3), not `--days 0`, and every quest was
  touched 0–1 days ago, so **the coach handled no quest**: no "Looked at:" lines, moves, steps or cues to record.
  The schedule, the dig, the reckoning and the re-arm are proven; the coach acting *on the schedule* is not yet.
  Monday 08:00 will also find nothing stalled unless a quest is 3+ days old by then (Kurzgesagt reaches 3 days on
  Tue 3 Nov 17:46).
- 1 Nov · 8 PASS — Pending after: **1** (the same Lean Startup proposal). New = 1 − 1 = **0**, matching **0**
  "Proposed." lines in the log. Verdict was fine, so no park proposal.
- 1 Nov · 9 PASS — `curl --cacert .irysquest\tls\cert.pem https://localhost:8787/log` shows the same seven lines from
  "Morning. Checking what's buried." to "→ the board is fine. …". This run wrote no `reckoning:` marker.
- 1 Nov · 9b FINDING — `/log` still holds one bare marker from before `830c78f`: `2026-11-01T16:55:59`,
  kind `reckoning`, text "reckoning:fine:". The fix stopped writing it but didn't filter old entries; it ages out
  of the 200-line log.
- 1 Nov · 10 PASS — No quest was proposed for, and all four quests' fields are unchanged from before the run:
  Kurzgesagt `last_proposed_at: 2026-10-30T21:23:36`, `asked_for_why: true`, `last_move: ask_why`; Valorant
  `last_proposed_at: (empty)`, `asked_for_why: true`; Learn to sing and Pilot script `last_proposed_at: (empty)`,
  `asked_for_why: false`.
- 1 Nov · 10b FINDING — Valorant's `asked_for_why: true` is stale: an earlier dry run wrote it, before `830c78f`
  stopped dry runs leaving traces, and no why-question was ever proposed. The fix doesn't repair existing memory,
  so the coach still can't ask Valorant's why. Clearing that one flag in `context.json` (by hand or a one-off
  reconcile) would undo it.

**B. Restore**
- 1 Nov · 11 PASS — Stopped the 17:49 window; relaunched the same way without `DIG_AT` (same title, same tee):
  "[17:49:50] Next scheduled dig at Mon 08:00." Left running (`.venv\Scripts\irysquest.exe serve --https`), `/health`
  OK.
- 1 Nov · 12 PASS — `git status` clean before this entry; `git check-ignore -v .irysquest/serve.log` →
  `.gitignore:2:.irysquest/`. NextQuest checkout untouched.

**Also found**
- 1 Nov · FINDING — With `2>&1 | Tee-Object` in Windows PowerShell 5.1, serve's first stderr line is wrapped in a
  `NativeCommandError` block ("irysquest : [17:45:52] … At line:1 char:122 … RemoteException") and non-ASCII is
  garbled ("ΓåÆ"). Cosmetic, and only in the tee'd file; the restart's `Tee-Object` also overwrites `serve.log`
  (the 17:49 log was copied aside first). Running serve without piping, or from `pwsh` 7, avoids both.

## 1 Nov (night): freeze bug pass — settle at capture

Run on Mon 2 Nov, 16:07–16:20, against `main` at `7768b04`. No source changes; NextQuest untouched.
Tally: **6 PASS, 0 FAIL, 1 UNVERIFIED** (step 6), plus findings. Step 7 is a hand-off (ids below).

- 1 · PASS with FINDINGs — No serve was running (nothing to stop). `git pull`: already up to date.
  - FINDING: HEAD is **`7768b04`**, not `e2f4921`. `7768b04` ("Snap it offers Take a photo and Choose from
    gallery…") came after the freeze and only touches the Snap it markup/JS and `tests/test_client.py`; the settle
    flow is as in `e2f4921`, so this pass verifies `7768b04`.
  - FINDING: **the tag `v0.1.0-freeze` doesn't exist**, locally or on `origin` (`git ls-remote --tags origin` is
    empty); `git describe --tags` → "fatal: No names found, cannot describe anything." Not created in this run.
  - `pip install -e ".[dev]"` OK (warns "Ignoring invalid distribution ~rysquest", a leftover folder from an
    interrupted install; harmless). `pytest -q` → **31 passed**.
  - Serve started in the "IrysQuest serve" window via `-EncodedCommand`, `cmd /c "… serve --https 2>&1" |
    Tee-Object .irysquest\serve.log` (no `NativeCommandError` wrapping this way; the arrow is still garbled in the
    file). Startup: "Next scheduled dig at **Tue** 08:00." FINDING, not a bug: it was Monday 16:07, past 08:00.
    Left running.
- 2 · PASS — Pending before: **3** (three inbox `add_quest` from 1 Nov photo captures).
- 3 · PASS — `POST https://localhost:8787/text` (`curl --cacert .irysquest\tls\cert.pem`) → 200,
  `"settle": true`, `"source": "notes"`, all outcomes `"preview"`:
  - "Learn to sing": why "For the family get-together in December" (taken from the text), **no question**;
  - "Fix the bike": "**What will your first smooth ride feel like?**";
  - "Read The Lean Startup from page 180": "**What will finishing these pages help you decide?**"

  Pending still 3. Console: "3 quest(s) captured; 2 question(s) to settle what done looks like." (preceded by
  "3 quest(s) found in the notes. Preview only.").
- 4 · PASS with FINDING — `POST /propose` with the bike (why "Ride it to work by 1 Dec") and the Lean Startup (empty
  why) → both `"outcome": "proposed"` (`01a19bd7-28ba-71e5-8cec-72041c5d56b8`,
  `01a19bd7-28f2-7df7-8aa1-7334f42d2417`). Console: "Settled: 1 of 2 quests have a why. Proposing." Pending
  **5** = 3 + 2.
  - FINDING: **why and track can't be read back.** The server's `list_proposals` (`ProposalDto`: id, op, status,
    source, client, created_at, quest, before, after, reason) and the propose reply (id, "pending", message) carry
    no payload. Agent side, `agent.py:259-261` passes `why=q.why or None, track=False`, and
    `mcp_client.py:126-131` sends `track` always and `why` when non-empty. Check in the app's Proposals screen.
  - FINDING: no duplicate check against the inbox. "read the lean startup from page 180" was proposed while
    "Read the book 'Lean startup' from page 180" (`01a196b4-f9e8-7b19-8d6e-b231a0f0565f`, 1 Nov) was still pending.
- 5 · PASS — Visitor `POST /text?try=<token>` (token read from the startup line, not printed) → 200, keys
  `["quests"]` only (no `settle`), all three `"preview"`, no `question` keys. Visitor `POST /propose?try=<token>`
  → **403** "Visitors can only preview captures." Pending still 5.
- 6 · **UNVERIFIED** — The desktop app's built-in browser refuses the self-signed certificate
  (`ERR_CERT_AUTHORITY_INVALID`) and offers no way to accept it. Edge opened with the URL via `Start-Process`, but
  screen access to a browser is read-only (no clicks), so the warning couldn't be passed and nothing on the page
  was driven; no screenshot. Static check of the served HTML only (no JS run): it contains "Turn into quests",
  "Propose these", "Discard", "Preview only", "Weekly reckoning", "digging…", "looking at the whole board…" and a
  `/propose` call; results are inserted with `insertAdjacentHTML('afterbegin', …)` and trimmed by
  `while(r.children.length>5)r.lastChild.remove()`. Needs a person at a desktop browser.
- 7 · HAND-OFF — Can't reach the app. Reject these two inbox proposals from step 4 on the phone:
  `01a19bd7-28ba-71e5-8cec-72041c5d56b8` ("fix the bike") and `01a19bd7-28f2-7df7-8aa1-7334f42d2417`
  ("read the lean startup from page 180").
- 8 · PASS — `git status` clean before this entry; `.env` and `.irysquest/` ignored; `tests/fixtures/notes.jpg`
  tracked.

Left on the server: 5 pending inbox proposals (the 3 from 1 Nov, the 2 above). Serve still running in the
"IrysQuest serve" window; an Edge window with the certificate warning may still be open.

## 2 Nov (evening): design pass, duplicate check, why on the card

Run on Mon 2 Nov, 18:25–18:35, against `main` at `2a3d664` (`91d0b4c` page design pass, `2a3d664` duplicate
check). No source changes; NextQuest untouched.
Tally: **10 PASS, 1 FAIL** (step 8, duplicate check), plus findings. Steps 10–11 are static only; the browser part
is a hand-off.

- 1 · PASS — The previous serve had already exited: nothing listening on 8787, no python process, no Edge window
  (only windowless background Edge processes, left alone).
- 2 · PASS — `git pull`: `cecdbae..2a3d664` fast-forward. Tag created from the PC:
  `git tag -a v0.1.0-freeze 7768b04 -m "Code freeze for the hackathon submission"`, `git push origin
  v0.1.0-freeze` → "[new tag] v0.1.0-freeze -> v0.1.0-freeze". `git ls-remote --tags origin`:
  `5a35008… refs/tags/v0.1.0-freeze`, `7768b04a… refs/tags/v0.1.0-freeze^{}`.
- 3 · PASS — `pip install -e ".[dev]"` OK (the harmless "Ignoring invalid distribution ~rysquest" warning again).
  `pytest -q` → **32 passed**.
- 4 · FINDING — `.env` has **`STALL_DAYS=3`**, not 0; not edited. `.irysquest\context.json`: "Check out YouTube
  videos on Valorant" → `asked_for_why = True` (still set).
- 5 · PASS — Serve started in the "IrysQuest serve" window (`-EncodedCommand`, tee to `.irysquest\serve.log`).
  Startup: "[18:29:01] Next scheduled dig at Tue 08:00." Left running.
- 6 · PASS — Pending before: **5**.
- 7 · PASS — `POST /text` `{"text":"fix the bike, call appa this weekend"}` → 200, `"settle": true`,
  `"source": "notes"`, both `"preview"`:
  - "fix the bike" (step "Walk to bike and note what's wrong in 5 min"): "**What will your bike ride feel like once
    it's fixed?**"
  - "call appa this weekend" (step "Pull up Appa's contact to call"): "**How do you hope Appa feels after hearing
    you?**"
- 8 · **FAIL** (duplicate check) / PASS (why on the card) — `POST /propose` with the bike (why "Ride it to work by
  1 Dec") and appa (empty why) → **both `"proposed"`** (`01a19c58-7c34-7b29-90d6-178406b08d98` "fix the bike",
  `01a19c58-7c6f-78bf-a426-77385052a2e8` "call appa this weekend"). Expected "fix the bike" → "already there",
  since `01a19bd7-28ba-71e5-8cec-72041c5d56b8` "fix the bike" was pending. Console: "Settled: 1 of 2 quests have a
  why. Proposing.", "2 quest(s) found in the notes.", both bullets, "2 proposal(s) waiting in the app."; the line
  "Already in the quest log or waiting in Proposals; skipping." never appeared. Pending **7** (expected 6).
  - Repro: with an add-quest proposal pending on the real server, capture the same title again. The server's
    `list_proposals` gives `"quest": "fix the bike"` and `"after": "fix the bike — next: Check the bike for 5
    minutes and note what's broken"`. `Agent._known_titles` (`agent.py`) adds `_norm(p.get("after") or
    p.get("quest"))`, so it uses `after`: `_norm` of it is `'fix the bike next check the bike for 5 minutes and note
    what s broken'`, which never equals `_norm("fix the bike")` = `'fix the bike'`. The test passes because
    `tests/fake_server.py:54` sets `after` to the bare title; the real server appends " — next: <step>". Reading
    `quest` first (or cutting `after` at " — next:") would match. The live-quest half of the check
    (`list_quests`) wasn't exercised here.
  - Why on the card, PASS. Read back via `list_proposals`: bike reason "Done looks like: Ride it to work by 1 Dec.
    Captured from your notes. …"; appa reason "Captured from your notes. It goes to the inbox; track it when a slot
    is free." (nothing about why). Console shows "(done looks like: Ride it to work by 1 Dec)" on the bike bullet.
  - Separate `POST /propose` "learn the ukulele" → `"proposed"` (`01a19c58-ce10-74c2-b6c9-eea07fd683e3`),
    console "Settled: 1 of 1 quests have a why. Proposing." Reason read back: "**Done looks like: Play one song at
    the December get-together. Captured from your notes. It goes to the inbox; track it when a slot is free.**"
    Pending **8**.
- 9 · PASS — Visitor `POST /text?try=<token>` → 200, keys `["quests"]` (no `settle`), both `"preview"`, no
  `question` keys. Visitor `POST /propose?try=<token>` → **403** `{"error": "Visitors can only preview captures."}`.
  Pending still 8.
- 10 · PASS (static) — `GET /` → 200, 16899 bytes. Contains
  `<div id="status" role="status" aria-live="polite"><span class="dot"></span><span id="statustext"></span></div>`,
  `<label class="btn grow">📷 Take a photo<input id="camera" type="file" accept="image/*" capture="environment"
  hidden></label>` and `<label class="btn grow">Gallery<input id="photo" type="file" accept="image/*" hidden>`.
  `<section><h2>Result</h2>` comes before `<section><h2>The morning check, now</h2>`. "About you", "Your rules for
  the coach" and "Agent console" are each in a `<summary>` inside a `<details>`.
- 11 · PASS — Saved to `%TEMP%\irysquest-page.html`; the one `<script>` block extracted and `node --check`
  (node v24.4.0) → exit 0.

Hand-off for the owner:
- [ ] On the phone: Take a photo → Read it; watch the status bar; answer a question; Propose these; accept in the
  app; open the quest and confirm its Why.
- [ ] Reject or accept the test inbox proposals: `01a19c58-7c6f-78bf-a426-77385052a2e8` "call appa this weekend",
  `01a19c58-ce10-74c2-b6c9-eea07fd683e3` "learn the ukulele", `01a19c58-7c34-7b29-90d6-178406b08d98` "fix the bike"
  (today's duplicate), and yesterday's `01a19bd7-28ba-71e5-8cec-72041c5d56b8` "fix the bike" and
  `01a19bd7-28f2-7df7-8aa1-7334f42d2417` "read the lean startup from page 180".

Left on the server: 8 pending inbox proposals (the 3 from 1 Nov, the 2 from this afternoon, the 3 above). Serve
still running in the "IrysQuest serve" window.
