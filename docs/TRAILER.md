# The demo video

Three minutes, built to be watched muted: every beat carries its own on-screen headline, and the sound is music
and a few tonal effects, no voiceover. The opening card states what existed before the hackathon.

## What is real, what is rebuilt

| Beat | Source |
|---|---|
| The real run (0:34) | `irysquest dig` against the real NextQuest server and the Meta Model API, 3 Nov 19:25. Console shown unedited, all four quests |
| The refusal (1:18) | The next real run, 3 Nov 19:35, after the pilot-script step was rejected in the app. The coach took a different angle and left three quests alone |
| Momentum (1:06) | The real coach (Muse Spark) on a demo board, because only a notification Done in the app can leave a quest needing a next step. Labelled "Demo board · real coach" on screen |
| Ask why (1:36) | A real dry run, 2 Nov 19:51 |
| Capture (1:46) | IrysQuest's own capture page, running and driven frame by frame; the questions are the ones Muse Spark asked on 2 Nov |
| Weekly reckoning (2:06) | A real run, 1 Nov |
| Phone screens | NextQuest's Proposals screen, rebuilt from its Compose source (`ProposalsScreen.kt`, the theme tokens and the app's own fonts) and filled with the proposals from those runs; noted on screen |

The run logs are recorded in [VERIFICATION.md](VERIFICATION.md) (3 Nov: video runs).

## How it was made

HTML scenes drawn as a pure function of time, rendered frame by frame with Playwright and encoded with ffmpeg,
one file per scene, joined without re-encoding. The score is one piano part (D minor under the opening, D major
from the cut to light, 80 BPM) written as MIDI and timed to the cut; the effects are synthesised tones. None of
the video tooling is part of the agent, so it isn't in this repository.
