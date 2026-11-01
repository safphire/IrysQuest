# The three-minute video

Submission rules: show only hackathon work, open with what pre-existed, ≤ 3:00. Judged on Impact 30 /
Meta tooling 25 / Technical 20 / Demo 25. Everything after the intro is a real run, recorded, not mocked.

## Decisions

- **Palette.** The intro is dark (`#0B0F0E` background, words in `#8A938F`, the glow in NextQuest's mint
  `#B8F2D4` and lime `#D8F26B`). At 0:30 we hard-cut to the app's own light palette and stay there. The cut is
  the message: dig = light. The screen recordings are in the app's colours anyway, so the intro has to land there.
- **Voice.** Manoj's own voice, recorded against the script below (phone mic in a quiet room is fine; one
  sentence per take, re-record freely). **Failsafe: `edge-tts`**, free, no key, runs on the PC:
  `pip install edge-tts` then `edge-tts --voice en-IN-PrabhatNeural --rate=-5% -f script.txt --write-media vo.mp3`.
  Alternative voice if Prabhat sounds flat: `en-GB-RyanNeural`. Decide by Monday night after one sample of each;
  whichever is used, the disclosure line is spoken, not just shown.
- **Format.** 1920×1080, 30 fps, MP4 (H.264). Captions burned in for every spoken line (judges skim muted).
- **Music.** None under the intro (silence is the point); a low, steady pad from 0:30 at −24 dB; out at 2:45.

## Script

Times are targets; the live beats will drift, cut them to fit.

| Time | Screen | Voice (also captioned) |
|---|---|---|
| 0:00–0:06 | Plain dark card, white text: *"NextQuest, the Android app and its server, existed before the hackathon. Everything else here was built during it."* | "One line first. NextQuest, the app and its server, existed before this. Everything you're about to see, the agent, was built this week." |
| 0:06–0:30 | **The burial.** Dark. Words appear one at a time, centred, each new one pushing the stack down: *sing · the pilot script · fix the bike · call Appa · the bike · Kurzgesagt channel · that course · the bike again · gym · sing* … faster, overlapping, the first ones sliding below the frame. At 0:24 the words stop. Silence. One word, far down, pulses mint: *sing*. | (0:08) "Most of us don't lose our goals to forgetting. We lose them to burial." (0:16) "Each new want lands on the last one." (0:22) silence. (0:26) "The ones that mattered are still down there." |
| 0:30–0:34 | Hard cut to light. Title card, mint/lime: **IrysQuest** · *an agent that digs them up, and only ever proposes*. | "IrysQuest is an agent that digs them up. It proposes. You decide." |
| 0:34–1:00 | **The morning dig.** Split screen: agent console (left), phone screen (right). Console shows `Morning. Checking what's buried.` then `Handing "Learn to sing" to the coach…` `Looked at: get_quest, get_history, list_decisions` `→ step: "Hum one scale (tonight, before the shower)" (3 min).` | "Every morning it reads the quest log and finds what's gone quiet. It hands each stalled quest to a coach, Muse Spark with tools. Watch it look before it decides: the quest, its history, what I accepted and refused before. Then one move. A three-minute step, with a when and a where." |
| 1:00–1:15 | Phone: Proposals screen, the proposal arrives with its reason and *I'm assuming this is…* line. Tap **Accept**. The quest's next step updates. | "The step lands in the app as a proposal, with its reason and the assumption behind it. Nothing changes until I say so. The server enforces that; the agent can't write." |
| 1:15–1:35 | Console: a second quest, coach chooses **ask_why**. Phone: the 2-minute step *"Write one line in this quest's Why."* | "When it can't tell what a quest is for, it doesn't guess. It asks. One line, two minutes." |
| 1:35–1:55 | Phone: **Reject** a proposal. Console next run: `Looked at: list_decisions` → a different angle. Then `Coach wanted to park it, but you said no to that before.` | "Refuse something and it remembers. The next angle is different, and some moves it will never repeat. Those guardrails are code, not prompt." |
| 1:55–2:15 | Phone (capture page): hold **Say it**, ramble: *"finish the pilot, mom's birthday Thursday, and I keep saying I'll learn to sing"*. Three quests appear → proposed to the inbox. Quick cut: **Snap it**, a notebook photo → quests. | "Capture is two seconds. Say it, and Muse Voice Transcribe plus Spark split the ramble into quests. Snap a notebook page, Spark reads it. They go to the inbox, never to the tracked five." |
| 2:15–2:30 | Console: `irysquest reckon` → *"The board looks alive… park 'Kurzgesagt' to make room for 'Pilot script'."* Phone: park proposal. | "On Sundays it reads the whole board and may tell you to do less. Five slots is the cap, and the coach defends it." |
| 2:30–2:48 | Architecture diagram from the README, animated left to right: agent → MCP → server (propose_* only) → app. Badges: Muse Spark · tool calling · Muse Voice Transcribe · Spark vision · Glimmer (standby). | "How it's built: a Python agent, a tool-calling loop with a budget of six, talking to the app only through its MCP endpoint. Three Meta models. Open-weight mode on Muse Glimmer is wired and on standby." |
| 2:48–3:00 | The thesis card, light: *"Procrastination is mood repair. Lower the cost of starting. Never guilt. Propose, don't act."* Then repo URL + AGPL. | "Procrastination is mood repair, not laziness. So this coach makes starting cheap, forgives first, and never writes the word overdue. It proposes. You decide. github.com/safphire/IrysQuest." |

Word count ≈ 330; at a calm 115 wpm that's 2:50 of speech. Cut the 1:15 beat first if long.

## Remotion intro (0:00–0:34)

One composition, `Burial`, 34 s, 1920×1080, 30 fps.

- `Disclosure` (0–6 s): centred, Inter 40px, `#E6ECE9` on `#0B0F0E`, fade in 0.4 s, hold, fade out 0.3 s.
- `Burial` (6–30 s): words from the list above (20 of them). Word *i* appears at `6 + 1.2·i^0.85` s (so they
  accelerate), Inter 56px `#8A938F`, spring in from y+40. Each arrival pushes earlier words down by 72px with a
  0.3 s ease-out; words below y=1080 are kept rendering (nothing deleted). At 24 s: stop. At 26 s the word `sing`
  (index 0, now ~1400px down) is scrolled back into view over 1.5 s with the whole stack, and pulses `#B8F2D4`
  (opacity 0.6↔1, 1.2 s period). Nothing else moves.
- `Cut` (30 s): one frame white, then `#F4FBF7` background, `IrysQuest` in Inter 96px `#0B0F0E`, tagline 36px,
  a lime `#D8F26B` underline growing left→right over 0.6 s. Hold to 34 s.
- No audio in the composition; the voice track is laid over in the editor so takes can be swapped.

## Recording rig (Monday)

Board for the demo, seeded Sunday night so it's a day old by Monday:
`python scripts/seed_demo.py` (three mock quests, accept + track in the app), plus the real *Learn to sing* and
*Pilot script*. Keep *Kurzgesagt* for the reckoning beat.

Sunday night, or the 08:00 run finds nothing (the 1 Nov scheduled run proved the scheduler and found 0 stalled,
because nothing was three days old):
- `STALL_DAYS=0` in `.env` for the demo days: every tracked quest goes to the coach each morning. Back to 3 after.
- Write *Kurzgesagt*'s Why in the app, or reject its pending why-question; while it's unanswered the agent
  deliberately leaves that quest alone.
- In `.irysquest/context.json`, set Valorant's `asked_for_why` to `false` (a stale flag from a dry run before
  `830c78f`).
- Restart `irysquest serve --https` and don't touch the tracked quests before 08:00. If launching from a script,
  pass the command with `-EncodedCommand`: `Start-Process` strips the inner quotes and runs the wrong thing.

1. **08:00, the real scheduled run.** Have the console window recording (OBS, window capture, 1080p) from
   07:58. Phone screen-recording running too. This gives beat 0:34–1:15 unscripted. If it fires but the
   board is thin, re-run with `irysquest dig --days 0` and label nothing differently; the console is identical.
2. **Rejection beat:** reject one proposal on the phone, run `irysquest dig --days 0` again, record.
3. **Say it / Snap it:** on the phone over `https://192.168.0.53:8787/`. Script the ramble; say it once
   before recording so the transcript is clean.
4. **Reckoning:** `irysquest reckon --dry-run` first; if the verdict is *fine*, park nothing and read the
   *fine* reason on camera instead ("an AI that sometimes says: nothing to do"). Honest beats mock.
5. **Architecture:** screenshot the README diagram; animate in the editor, or a 15 s Remotion `Arch` comp.
6. **Voice:** record all lines in one sitting, after the screen takes, so the words match what happened.

Never show `.env`, the token file, or the ngrok URL bar with the key visible; crop the console to the agent's
output. Phone recording: turn notifications off except NextQuest's.

## Edit order (Tuesday)

Intro → live beats in script order → architecture → thesis. Captions on every line. Export, watch once muted,
once with sound. Upload unlisted to YouTube; link in README; then both repos public.
