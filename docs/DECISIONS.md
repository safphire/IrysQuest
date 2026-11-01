# Decisions

- **D-1 (27 Oct)** Separate repo, no changes to NextQuest. The hackathon FAQ requires a fresh repo containing only
  work done during the event. The agent talks to the app through the server's existing MCP endpoint, as Claude and
  ChatGPT already do.
- **D-2 (27 Oct)** Python. Small agent, fast iteration, and the maintainer already uses Python (Scriptory).
- **D-3 (27 Oct)** Hand-rolled MCP client over httpx instead of the MCP SDK. The server is stateless JSON-RPC over
  POST with no sessions or SSE; a plain client is ~100 lines, fully testable against `tests/fake_server.py`, and has no
  SDK version surprises in a nine-day window. Can be swapped later.
- **D-4 (27 Oct)** The agent signs in exactly like a connector: dynamic client registration, authorization code with
  PKCE S256, loopback redirect on 127.0.0.1 (the server allows http redirects only on loopback). The admin password is
  typed in the browser; the agent never handles it.
- **D-5 (27 Oct)** Tokens live in `.irysquest/tokens.json` (gitignored, mode 600). Refresh tokens rotate; the file is
  rewritten on every refresh.
- **D-6 (28 Oct)** Stall signal is the server's `touched_at` per quest (updated by every event on it), not
  step age: it needs no history parsing and matches what the user sees. Threshold `STALL_DAYS`, default 3.
- **D-7 (28 Oct)** Muse replies are requested as JSON but parsed defensively (first `{...}` in the text, minutes
  clamped to 2–10, step length capped). A reply that can't be parsed is skipped, never half-proposed.
- **D-8 (28 Oct)** One proposal per stalled quest per run, and none while a proposal for that quest is pending.
  Rejected steps are passed to Muse so the next attempt takes a different angle.
- **D-9 (28 Oct)** The agent keeps its own memory in `.irysquest/context.json`: a user profile, and per quest the
  inferred intent, last stated assumption, accepted and rejected steps. NextQuest stays the source of truth for
  quests; this file only holds what the agent learned. Decisions are reconciled from `list_proposals` each run.
- **D-10 (28 Oct)** Thin context → ask, don't guess. If Muse reports the purpose is unclear and the quest has no
  why, the proposal is a 2-minute step to write the why. Otherwise the stated assumption is appended to the reason.
- **D-11 (28 Oct)** Captures (voice, photo, text) always propose into the inbox with `track=false`, so the
  five-slot cap is never touched by a brain dump. Promotion to tracked is the user's call in the app.
- **D-12 (28 Oct)** `serve` is `http.server`, not a framework: one file, no dependencies, and Streamlit-style
  apps are on the organisers' overdone list. Try-it mode is a token in the URL and previews only.
- **D-13 (28 Oct)** Open-weight mode swaps the chat base URL and model only; transcription stays on the Model
  API because Muse Spark Open doesn't do ASR.
- **D-14 (30 Oct)** The breakdown call became the coach: a tool-calling loop where Muse Spark can look (get_quest,
  get_history, list_decisions) and must end with one decision call (shrink_step, add_subquest, park_quest,
  ask_why, leave_alone). Budget six turns. `tool_choice` is "auto" because the Model API accepts nothing else, so a
  plain-text reply is handled too. The model decides; the agent's guardrails and the server's validation still
  bound what reaches the user.
- **D-15 (30 Oct)** Guardrails live in code, not the prompt: no park after a rejected park, no second ask-why,
  and every proposal still states its assumption. The user's free-text rules go into the prompt as well, but
  the code-level rules hold even if the model ignores them.
- **D-16 (31 Oct)** Voice recordings are converted to WAV in the browser, not on the PC. Muse Voice Transcribe
  accepts only mono 16-bit PCM WAV at 16 or 24 kHz, and phone browsers record webm/opus or mp4. The page decodes
  the recording with the Web Audio API, renders it to one 16 kHz channel and writes a plain WAV header, so the
  server just forwards bytes. ffmpeg on the PC would have been an install step for every judge.
- **D-17 (1 Nov)** The weekly reckoning is a separate, single call over the whole board, not part of the per-quest
  coach loop: the question is different (what is crowding what?) and the answer is one verdict. Park is the only
  verdict that proposes anything; focus and fine are advice in the console. The same guardrails apply: a quest the
  user refused to park is downgraded to focus. Runs on Sundays with the morning dig, or on demand.
- **D-18 (1 Nov)** `serve --https` with a self-signed certificate, so "Say it" works from a phone. Browsers only
  expose `getUserMedia` in a secure context, and `http://<LAN IP>` isn't one (only localhost is): on the phone,
  tapping Record did nothing at all. The certificate is made once with `openssl` (on PATH; Git for Windows ships
  one) into `.irysquest/tls/`, covering localhost, 127.0.0.1 and the PC's LAN IP; the phone shows a warning the
  first time, which is fine for a dev build. Python's `cryptography` would avoid the openssl step but is a new
  dependency, and it isn't installed. Without openssl, tunnel port 8787 instead (`ngrok http 8787`), since ngrok
  gives an https URL. Plain http stays the default: localhost needs nothing more.
