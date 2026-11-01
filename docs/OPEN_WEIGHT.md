# Running IrysQuest on open weights

Open-weight mode sends every chat call (the coach, the weekly reckoning, captures) to any server that speaks the
OpenAI-compatible `/v1/chat/completions` API, as Ollama and vLLM do. Voice transcription stays on the Meta Model
API (D-13).

**Status:** implemented against that API and tested against a local fake of it (`tests/test_open_provider.py`,
including tool calls). Not yet run against the real Muse Glimmer weights.

## With Ollama (for judges)

```bash
ollama pull muse-glimmer
```

Add three lines to `.env`:

```
OPEN_BASE_URL=http://localhost:11434/v1
OPEN_MODEL=muse-glimmer
OPEN_API_KEY=ollama
```

`OPEN_API_KEY` can be any non-empty string: Ollama ignores it, IrysQuest refuses to start without one.

Then pass `--provider open` to any command:

```bash
irysquest --provider open dig --dry-run --days 0
irysquest --provider open reckon --dry-run
irysquest --provider open serve
```

`--provider` goes before the subcommand. Setting `MUSE_PROVIDER=open` in `.env` makes it the default instead.

## With vLLM

Same three lines, with vLLM's address and the model name it serves, e.g. `OPEN_BASE_URL=http://localhost:8000/v1`.
Start vLLM with tool calling enabled (`--enable-auto-tool-choice` and a `--tool-call-parser` that fits the model),
or the coach gets plain text back and falls back to its JSON parsing (D-14).

## If it goes wrong

- `open 404: model "muse-glimmer" not found` — the pull didn't finish, or `OPEN_MODEL` doesn't match `ollama list`.
- `No API key for provider 'open'` — `OPEN_API_KEY` is empty.
- The coach always "leaves alone" — the server isn't returning `tool_calls`; check its tool-calling support.
