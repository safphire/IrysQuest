# IrysQuest

**An agent that notices which of your goals have stalled and proposes the smallest next move. It proposes, you approve.**

Built during the [Meta Global AI Developer Hackathon](https://dev.meta.ai/events/global-hackathon), 26 Oct – 4 Nov 2026, indie track.

**▶ [Watch the 3-minute demo](https://www.youtube.com/watch?v=Sg_Gt-SzO2E)**

> **What existed before, what is new.** [NextQuest](https://github.com/safphire/NextQuest), a local-first Android
> quest log with a self-hosted sync + MCP server, existed before the hackathon. Everything in *this* repository —
> the agent, its stall detection, the Muse-powered breakdowns, voice and notebook-photo capture — was built during the
> event. The app is not modified; the agent talks to it from outside, through the server's existing MCP endpoint.

## The problem

People with more intentions than attention lose goals two ways. Some are forgotten; NextQuest's two-second
capture is for those. The rest are **buried**: written down, known, and still not started, because each new want
lands on the last and the ones that mattered sink out of sight. That is procrastination, and it is what IrysQuest
is for.

Every productivity tool today waits for you to come back and ask for help. But a person who is stuck doesn't come
back; that's what stuck means.

IrysQuest is an agent that notices which goals have stalled and brings you the smallest possible next move. You
decide. It proposes, you approve; it never acts on its own.

## What it believes about procrastination

Procrastination is short-term mood repair, not laziness: the task feels bad to start, so we do something else. That
one finding decides how the coach behaves, and each behaviour below has research behind it.

| What the coach does | Why |
|---|---|
| Proposes steps of 2–10 minutes, never "plan" or "decide" | Lowering the cost of *starting* is the lever; completion takes care of itself |
| Attaches a when/where cue to each step ("after lunch, at the desk") | If-then plans are among the strongest goal interventions known |
| Forgives first after a gap, then asks for one small step | Self-forgiveness after procrastinating reduces later procrastination |
| Treats Mondays and the first day back as clean starts | The fresh-start effect: temporal landmarks motivate new beginnings |
| Frames XP and streaks as feedback, never payment; no penalties | Controlling rewards erode intrinsic motivation; informational feedback doesn't |
| Sometimes says *park this* | Attention residue from too many parallel goals kills flow; five slots is the cap, and the coach defends it |
| Never writes overdue, failed, missed, lazy, behind, again | Guilt is the mood the whole loop is trying to avoid |

Where this sits against the apps people already use: **Fabulous** calibrates you with a long questionnaire and sells a
programme; the result is thorough, paywalled and heavy. **Goblin Tools** and **Todoist** break a task down when you ask.
IrysQuest calibrates from what you actually accept and refuse, asks one question only when it has to, comes to you
before you ask, and is open source. That's the bet: a coach that learns you by watching, not by interviewing.

## What it does

| Trigger | What the agent does | Meta model |
|---|---|---|
| Every morning (or `irysquest dig`) | Reads your tracked quests, finds the ones nothing has touched in days, and hands each to the **coach**: Muse Spark with tools. It looks at the quest, its history and your past decisions if it needs to, then chooses one move: shrink the step to 2–10 minutes, add a subquest, park the quest, ask what it's for, or leave it alone. The move becomes a proposal with its reason and the assumption behind it | Muse Spark, tool calling |
| A step marked done from a notification, with nothing next | **Momentum**: the quest goes to the coach at the next dig, whatever its age, and gets the next small step on the same thread, so a quest is never left stuck midway | Muse Spark, tool calling |
| Sundays (or `irysquest reckon`) | The **weekly reckoning**: the coach reads the whole board at once and gives one verdict. *Park* one quest that's crowding the others, naming what it makes room for; *focus* on one this week; or *fine*. An AI that sometimes tells you to do less | Muse Spark |
| A voice brain dump (capture page) | Transcribes, splits the ramble into separate quests, asks what done looks like for each, proposes them with your answers as their Why | Muse Voice Transcribe + Muse Spark |
| A photo of a notebook page or whiteboard | Reads it, turns it into proposed quests | Muse Spark (vision) |
| `--provider open` | The same loop on Meta's open-weight Muse Glimmer, via Ollama, vLLM or a hosted endpoint | Muse Glimmer |

**It decides, within your rules.** The coach is a tool-calling loop (`coach.py`): read tools to look, one decision tool per move the server allows, a budget of six calls. Your standing rules (`irysquest rules "never park the pilot script"`) go in its system prompt, and hard guardrails sit outside the model: it can't park a quest you refused to park, and it won't ask the same question twice.

**It settles what done looks like, first.** Every capture is previewed with one question per quest (*"What does done look like for 'learn to sing'?"*); your one-line answer becomes the quest's Why before it's proposed. Mental contrasting, made a habit at the moment of capture. Leave it blank and the coach may ask later: a tracked quest with no *why* and no history gets a 2-minute step to write what done looks like. Every other proposal states its assumption, so a wrong guess costs you nothing.

**It remembers.** `.irysquest/context.json` holds what you told it about yourself (`irysquest profile`), what it inferred about each quest, and what you accepted or rejected. Rejected steps are never re-proposed; the next attempt takes a different angle.

**Nothing the agent does changes your data.** The NextQuest server only exposes *propose\_\** tools to AI clients;
every output lands in the app's Proposals screen, where you accept, edit or reject it. This is enforced by the server,
not promised by the agent.

## How it fits together

```
 schedule / capture page / "dig now"
                │
                ▼
      ┌──────────────────────┐         ┌──────────────────────┐
      │  IrysQuest agent     │  MCP    │  NextQuest server    │  sync   ┌────────────────┐
      │  read state          │────────▶│  read tools          │────────▶│ NextQuest app  │
      │  find stalls         │         │  propose_* tools     │         │ Proposals:     │
      │  draft (Muse)        │◀────────│  (validation, cap)   │◀────────│ accept / edit  │
      │  validate, propose   │         └──────────────────────┘         │ / reject       │
      └──────────────────────┘              existing, unchanged         └────────────────┘
```

## Running it yourself (judges)

IrysQuest is an agent for an app that already exists, so it needs three things: the
[NextQuest](https://github.com/safphire/NextQuest) server, the NextQuest Android app paired to it (that's where
proposals are accepted or rejected), and a Meta Model API key. The tests need none of them (last step).

**1. The NextQuest server** (Docker; unchanged by this project)

```bash
git clone https://github.com/safphire/NextQuest && cd NextQuest
cp .env.example .env       # set ADMIN_PASSWORD (12+ characters)
docker compose up -d
curl http://localhost:8080/health
```

The app only pairs over HTTPS, so put the server behind a tunnel, e.g. `ngrok http 8080`. Set `PUBLIC_URL` in
NextQuest's `.env` to the tunnel's `https://` address and run `docker compose up -d` again.

**2. The app, paired.** Install the debug APK (CI artifacts on the NextQuest repo, or
`./gradlew :app:assembleDebug`). Open `PUBLIC_URL` in a browser, sign in with the admin password, choose **Pair a
device** and scan the QR code with the phone (or enter the code under **Settings → Sync & AI**).

**3. The agent**

```bash
git clone https://github.com/safphire/IrysQuest && cd IrysQuest
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env       # QUEST_SERVER_URL = NextQuest's PUBLIC_URL; META_API_KEY = your key
irysquest login            # a browser opens the server's consent page; approve with the admin password
irysquest today            # proves the connection: tracked quests and slots
```

**4. Something to dig into.** Track a quest or two in the app, or seed a demo board:

```bash
python scripts/seed_demo.py    # proposes 3 mock quests; accept them in the app's Proposals screen, then track them
```

The server stamps each quest's last-touched time itself, so new quests are 0 days old. `--days 0` treats
everything as stalled:

```bash
irysquest dig --dry-run --days 0   # watch the coach look (get_quest, get_history, list_decisions) and decide
irysquest dig --days 0             # the same, proposed: accept, edit or reject in the app
irysquest reckon --dry-run         # the weekly reckoning over the whole board
irysquest serve --https            # capture page for the phone (voice, photo, text) and Dig now
```

**5. Tests**, with no server, phone or key:

```bash
pip install -e ".[dev]" && pytest
```

Open-weight mode on a local model: [docs/OPEN_WEIGHT.md](docs/OPEN_WEIGHT.md).

## What to look at

- [`src/irysquest/coach.py`](src/irysquest/coach.py): the agent. A tool-calling loop where Muse Spark looks
  (`get_quest`, `get_history`, `list_decisions`), then makes exactly one decision call (shrink, subquest, park,
  ask why, leave alone), within a budget of six calls.
- [`src/irysquest/reckoning.py`](src/irysquest/reckoning.py): the weekly reckoning. One verdict over the whole
  board (park / focus / fine), downgraded if it names a quest the user protected.
- [`src/irysquest/agent.py`](src/irysquest/agent.py): the loop around the coach, and the guardrails that live in
  code rather than in the prompt (in `dig`). No park after a refused park, no second ask-why, no replacing an
  unanswered why-question, every proposal states its assumption.
- [`src/irysquest/serve.py`](src/irysquest/serve.py): the capture page, the browser-side WAV conversion for voice,
  try-it mode, and the morning schedule.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): why it is built this way, one dated line per decision.
- [`docs/VERIFICATION.md`](docs/VERIFICATION.md): what was run against the real server, the Meta Model API and a
  real phone, what broke, and what's still unverified.

## Everyday commands

Prerequisites: Python 3.11+, a running NextQuest server (its `docker compose up`), and a Meta Model API key.

```bash
pip install -e .
cp .env.example .env         # set QUEST_SERVER_URL and META_API_KEY
irysquest login              # one-time: approves this agent on the server's consent page
irysquest today              # proves the connection: tracked quests and their steps
irysquest dig --dry-run      # what the agent would propose, without proposing
irysquest dig                # propose; accept, edit or reject in the app
irysquest profile "Solo dev, evenings only; a small step is 5 minutes."
irysquest capture "finish the pilot script, mom's birthday, learn to sing"
irysquest serve              # capture page (voice, photo, text), Dig now, and the 08:00 schedule
```

Open the capture page from your phone on the same Wi-Fi. For voice, run `irysquest serve --https` and open
`https://<PC IP>:8787/`: phone browsers only allow the microphone over HTTPS. The certificate is self-signed
(made once with `openssl`), so the phone warns the first time; choose Advanced → Proceed. No openssl? Use
`ngrok http 8787` and open the https URL it prints. With `TRY_IT_TOKEN` set,
`/?try=<token>` is a visitor mode: friends see what the agent would propose for their own words. Their words go to
Meta's model to produce the preview; nothing is proposed or saved to the quest log.

Open-weight mode: set `MUSE_PROVIDER=open` and `OPEN_BASE_URL`/`OPEN_API_KEY` to any OpenAI-compatible host
serving `muse-glimmer` (Ollama, vLLM, or a hosted endpoint), or pass `--provider open` per command.
Running it locally with Ollama or vLLM: [docs/OPEN_WEIGHT.md](docs/OPEN_WEIGHT.md).

Tests run without a NextQuest server, against a small fake in `tests/`:

```bash
pip install -e ".[dev]" && pytest
```

## How this was built

I'm a solo developer. I set the problem, the design and the rules the agent must follow, made every judgment call
(they're dated in [docs/DECISIONS.md](docs/DECISIONS.md)), and tested it on my own server, phone and quest log.
Claude (Anthropic) worked with me as a coding assistant: it wrote much of the code and the tests to my direction,
and Claude Code sessions on my machine ran the verification passes. Commits it helped with carry a
`Co-Authored-By: Claude` line. Every claim in this README is backed by a logged run in
[docs/VERIFICATION.md](docs/VERIFICATION.md), including what broke and what's still unverified.

## Status

- [x] Sign in to the server (OAuth 2.1, PKCE) and read quests
- [x] Stall detection and Muse Spark breakdowns → proposals (`irysquest dig`, `--dry-run` to preview)
- [x] Context: profile, rules, per-quest memory, ask-for-why, stated assumptions, rejection feedback
- [x] The coach: tool-calling decisions (shrink / subquest / park / ask / leave) with guardrails
- [x] The weekly reckoning: one cross-quest verdict (park / focus / fine), Sundays
- [x] `irysquest serve`: morning schedule, Dig now, agent console
- [x] Capture page: voice (Muse Voice Transcribe), notebook photo (Muse Spark vision), typed; settle-what-done-looks-like before proposing; try-it mode
- [x] Open-weight mode: implemented against the Ollama/vLLM OpenAI-compatible API; verification on real Muse Glimmer is on standby (no local disk for the weights during the event)
- [x] Momentum: a quest left without a next step gets the next one
- [x] Verified end to end on a real server, the real Meta Model API and a real phone (see docs/VERIFICATION.md)

## What's next

- **Series quests.** "Read the book from page 180" is a practice, not a step: the coach should propose the next slice
  each time one is done (NextQuest already models practices; the agent needs `propose_add_practice` and a
  *next slice* move).
- **A "coach left you something" notification** on the phone, which needs an app-side change and so waited.
- **Open-weight mode verified** on real Muse Glimmer (implemented, offline-tested; on standby until the weights can be hosted).
- **Obstacle and plan** fields (mental contrasting) read by the coach once the app exposes them over MCP.

## License

AGPL-3.0-or-later, like NextQuest. See `LICENSE`.
