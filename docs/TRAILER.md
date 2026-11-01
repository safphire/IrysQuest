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

Shape, from what launch videos that travel have in common: the pain in the first five seconds, the payoff
before the explanation, problem → solution → proof, show the outcome rather than tour the features, captions
throughout, name the judging criteria out loud, and end with where it goes next. The disclosure line still
comes first; the rules say so.

| Time | Screen | Voice (also captioned) |
|---|---|---|
| 0:00–0:04 | Dark card, one line: *NextQuest, the app and server, existed before. The agent is this week's work.* | "NextQuest existed before this week. The agent didn't." |
| 0:04–0:12 | **The hook.** Dark. One word, mint, centred: *sing*. Then grey words drop on top of it, fast: *pilot script · the bike · call Appa · Kurzgesagt · that course · gym · taxes*. By 0:12 *sing* is gone under the pile. | "You didn't forget you wanted to learn to sing. You wrote it down. Then you put something newer on top of it. And again." |
| 0:12–0:18 | Silence. The pile. A faint mint glow under it. | (0:15) "Every to-do app waits for you to come back. But stuck people don't come back. That's what stuck means." |
| 0:18–0:30 | **The payoff, before the explanation.** Hard cut to light. A phone, a proposal card arriving, just the card: *Hum one scale (tonight, before the shower)* · 3 min · *I'm assuming this is to sing confidently for family in December.* Thumb hovers over Accept. | "So I built an agent that comes to you. Every morning it finds what's gone quiet, and brings one step small enough to start tonight. With a when and a where. It asks before it guesses. And it can't touch anything until you tap." |
| 0:30–0:34 | Title card, mint/lime: **IrysQuest** · *digs up what you buried. Proposes. Never acts.* | "IrysQuest." |
| 0:34–1:10 | **How it got there, live.** Split: console left, phone right. The real 08:00 run: `Morning. Checking what's buried.` → `Handing "Learn to sing" to the coach` → `Looked at: get_quest, get_history, list_decisions` → the step → `Proposed.` Phone: the card lands. Accept. | "This is the real morning run, unedited. The coach is Muse Spark with tools. Watch it look before it decides: the quest, its history, what I accepted and refused before. Then one move. The step lands in the app as a proposal. Nothing changes until I accept. The server enforces that; the agent cannot write." |
| 1:10–1:30 | Phone: **Reject** one. Console, next run: `Looked at: list_decisions` → a different angle. Then `Coach wanted to park it, but you said no to that before.` | "Refuse something and it remembers. The next angle is different. Some moves it will never repeat, and those guardrails are code, not prompt." |
| 1:30–1:45 | Console: a quest with no why → `Purpose unclear: asking instead of guessing.` Phone: the 2-minute step *Write one line: what does done look like?* | "When it can't tell what a goal is for, it doesn't guess. It asks. Two minutes." |
| 1:45–2:05 | Phone capture page. Hold **Say it**, ramble: *"finish the pilot, mom's birthday Thursday, I keep saying I'll learn to sing."* Three quests appear. Cut: **Snap it**, notebook page → quests. | "Capture is two seconds. Say it: Muse Voice Transcribe, then Spark splits the ramble into goals. Snap a notebook page: Spark reads it. They go to the inbox, never to the five you're tracking." |
| 2:05–2:20 | Console: `irysquest reckon` → board read → verdict. Phone: the park proposal, or the *fine* line. | "On Sundays it reads the whole board and may tell you to do less. An agent that sometimes says: park this." |
| 2:20–2:40 | **Proof + criteria, said out loud.** Three stacked lines over the diagram: *Three Meta models: Spark with tools, Spark vision, Voice Transcribe. Open-weight mode on Muse Glimmer, wired.* / *Tool-calling loop, six-call budget, guardrails in code, 30 tests.* / *Verified on a real server, a real phone, a real morning.* | "Three Meta models, and the open-weight path on Muse Glimmer is wired. The coach is a tool-calling loop with a budget and code-level guardrails, thirty tests. Everything you saw ran for real, on my phone, this morning." |
| 2:40–2:52 | **What's next**, three cards: *series quests (the next slice of a book, each time)* · *a "coach left you something" notification* · *Glimmer, fully local*. | "Next: goals that are practices, not steps, a nudge on the phone, and the whole loop running locally on Glimmer." |
| 2:52–3:00 | Thesis card then repo: *Procrastination is mood repair. Make starting cheap. Forgive first. Never guilt. Propose, don't act.* · github.com/safphire/IrysQuest · AGPL. | "Procrastination is mood repair, not laziness. So this coach makes starting cheap, forgives first, and never writes the word overdue. It proposes. You decide." |

About 340 words, 2:55 at a calm pace. If long, cut the ask-why beat (1:30) first, then shorten the reckoning.

Why this order: the payoff card at 0:18 is the single image a judge remembers; the live run after it is the
proof that the card was real. Criteria are named at 2:20 in the judges' own words (Meta tooling, technical,
demo) so nobody has to infer them.

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
