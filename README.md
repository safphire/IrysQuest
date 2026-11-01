# IrysQuest

**An agent that notices which of your goals have stalled and proposes the smallest next move. It proposes, you approve.**

Built during the [Meta Global AI Developer Hackathon](https://dev.meta.ai/events/global-hackathon), 26 Oct – 4 Nov 2026, indie track.

> **What existed before, what is new.** [NextQuest](https://github.com/safphire/NextQuest), a local-first Android
> quest log with a self-hosted sync + MCP server, existed before the hackathon. Everything in *this* repository —
> the agent, its stall detection, the Muse-powered breakdowns, voice and notebook-photo capture — was built during the
> event. The app is not modified; the agent talks to it from outside, through the server's existing MCP endpoint.

## The problem

People who have more intentions than attention don't lose their goals to forgetting. They lose them to **burial**:
each new idea lands on the last, and the ones that mattered sink out of sight.

Every productivity tool today waits for you to come back and ask for help. But a person who is stuck doesn't come
back; that's what stuck means.

IrysQuest is an agent that notices which goals have stalled and brings you the smallest possible next move. You
decide. It proposes, you approve; it never acts on its own.

## What it does

| Trigger | What the agent does | Meta model |
|---|---|---|
| Every morning (or `irysquest dig`) | Reads your tracked quests, finds the ones nothing has touched in days, and hands each to the **coach**: Muse Spark with tools. It looks at the quest, its history and your past decisions if it needs to, then chooses one move: shrink the step to 2–10 minutes, add a subquest, park the quest, ask what it's for, or leave it alone. The move becomes a proposal with its reason and the assumption behind it | Muse Spark, tool calling |
| Sundays (or `irysquest reckon`) | The **weekly reckoning**: the coach reads the whole board at once and gives one verdict. *Park* one quest that's crowding the others, naming what it makes room for; *focus* on one this week; or *fine*. An AI that sometimes tells you to do less | Muse Spark |
| A voice brain dump (capture page) | Transcribes, splits the ramble into separate quests, proposes them | Muse Voice Transcribe + Muse Spark |
| A photo of a notebook page or whiteboard | Reads it, turns it into proposed quests | Muse Spark (vision) |
| `--provider open` | The same loop on Meta's open-weight Muse Spark Open, via Baseten or Modal | Muse Spark Open |

**It decides, within your rules.** The coach is a tool-calling loop (`coach.py`): read tools to look, one decision tool per move the server allows, a budget of six calls. Your standing rules (`irysquest rules "never park the pilot script"`) go in its system prompt, and hard guardrails sit outside the model: it can't park a quest you refused to park, and it won't ask the same question twice.

**It asks before it guesses.** A quest with no *why* and no history gets a different proposal: a 2-minute step to write what done looks like. Every other proposal states its assumption, so a wrong guess costs you nothing.

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

## Running it

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

Open the capture page from your phone on the same Wi-Fi: `http://<PC IP>:8787/`. With `TRY_IT_TOKEN` set,
`/?try=<token>` is a visitor mode: friends see what the agent would propose for their own words; nothing is sent.

Open-weight mode: set `MUSE_PROVIDER=open` and `OPEN_BASE_URL`/`OPEN_API_KEY` to any OpenAI-compatible host
serving `muse-spark-open-1026` (Baseten, Modal, or a local server), or pass `--provider open` per command.

Tests run without a NextQuest server, against a small fake in `tests/`:

```bash
pip install -e ".[dev]" && pytest
```

## Status

- [x] Sign in to the server (OAuth 2.1, PKCE) and read quests
- [x] Stall detection and Muse Spark breakdowns → proposals (`irysquest dig`, `--dry-run` to preview)
- [x] Context: profile, rules, per-quest memory, ask-for-why, stated assumptions, rejection feedback
- [x] The coach: tool-calling decisions (shrink / subquest / park / ask / leave) with guardrails
- [x] The weekly reckoning: one cross-quest verdict (park / focus / fine), Sundays
- [x] `irysquest serve`: morning schedule, Dig now, agent console
- [x] Capture page: voice (Muse Voice Transcribe), notebook photo (Muse Spark vision), typed; try-it mode
- [x] Open-weight mode (`--provider open`) — needs a host for Muse Spark Open
- [ ] Verified on a real phone end to end (in progress)

## License

AGPL-3.0-or-later, like NextQuest. See `LICENSE`.
