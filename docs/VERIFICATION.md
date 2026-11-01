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
