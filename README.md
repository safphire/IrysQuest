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
| Every morning (or `irysquest dig`) | Reads your tracked quests, finds the ones whose step hasn't moved in days, drafts a 2–10 minute first step for each, submits it as a proposal with a reason | Muse Spark |
| A voice brain dump (capture page) | Transcribes, splits the ramble into separate quests, proposes them | Muse Voice Transcribe + Muse Spark |
| A photo of a notebook page or whiteboard | Reads it, turns it into proposed quests | Muse Spark (vision) |
| `--provider open` | The same loop on Meta's open-weight Muse Spark Open, via Baseten or Modal | Muse Spark Open |

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
```

Tests run without a NextQuest server, against a small fake in `tests/`:

```bash
pip install -e ".[dev]" && pytest
```

## Status

- [x] Sign in to the server (OAuth 2.1, PKCE) and read quests
- [x] Stall detection and Muse Spark breakdowns → proposals (`irysquest dig`, `--dry-run` to preview)
- [ ] Scheduled runs and the agent console
- [ ] Capture page: voice (Muse Voice Transcribe) and notebook photo (Muse Spark vision)
- [ ] Open-weight mode (Muse Spark Open)

## License

AGPL-3.0-or-later, like NextQuest. See `LICENSE`.
