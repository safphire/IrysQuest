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
