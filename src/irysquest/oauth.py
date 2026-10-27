# SPDX-License-Identifier: AGPL-3.0-or-later
"""OAuth 2.1 sign-in to the NextQuest MCP server, done once.

The server is an OAuth 2.1 authorization server backed by its admin password:
discovery (RFC 9728 → RFC 8414), dynamic client registration (RFC 7591), the
authorization-code grant with PKCE S256, rotating refresh tokens. This is the
same flow Claude and ChatGPT use when added as connectors; here the "connector"
is this agent, and the redirect goes to a one-shot listener on 127.0.0.1.

The admin password is typed by the user in their browser. The agent never sees it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .console import say

CLIENT_NAME = "IrysQuest"
_H = {"ngrok-skip-browser-warning": "1"}


@dataclass
class Tokens:
    client_id: str
    token_endpoint: str
    access_token: str
    refresh_token: str
    expires_at: float  # epoch seconds

    def expired(self, skew: float = 60) -> bool:
        return time.time() + skew >= self.expires_at


def load_tokens(path: Path) -> Tokens | None:
    if not path.exists():
        return None
    return Tokens(**json.loads(path.read_text()))


def save_tokens(path: Path, tokens: Tokens) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(tokens), indent=2))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _discover(client: httpx.Client, mcp_url: str) -> tuple[dict, str]:
    """Returns (authorization-server metadata, resource) the way an MCP client does:
    401 → protected-resource metadata → authorization-server metadata."""
    r = client.post(mcp_url, json={"jsonrpc": "2.0", "id": 0, "method": "ping"})
    www = r.headers.get("www-authenticate", "")
    prm_url = None
    if "resource_metadata=" in www:
        prm_url = www.split("resource_metadata=", 1)[1].split(",")[0].strip().strip('"')
    if not prm_url:
        base = mcp_url.rsplit("/mcp", 1)[0]
        prm_url = f"{base}/.well-known/oauth-protected-resource"
    prm = client.get(prm_url).raise_for_status().json()
    issuer = prm["authorization_servers"][0].rstrip("/")
    asm = client.get(f"{issuer}/.well-known/oauth-authorization-server").raise_for_status().json()
    return asm, prm["resource"]


class _Callback(BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        q = parse_qs(urlparse(self.path).query)
        _Callback.result = {k: v[0] for k, v in q.items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>IrysQuest is connected. You can close this tab.</h2>")

    def log_message(self, *a):  # quiet
        pass


def login(mcp_url: str, token_file: Path, open_browser: bool = True) -> Tokens:
    """Runs the full flow once and stores the tokens. Returns them."""
    with httpx.Client(timeout=20, headers=_H) as c:
        asm, resource = _discover(c, mcp_url)

        srv = HTTPServer(("127.0.0.1", 0), _Callback)
        port = srv.server_address[1]
        redirect = f"http://127.0.0.1:{port}/callback"

        say("Registering this agent as a connector on the server.")
        reg = c.post(
            asm["registration_endpoint"],
            json={"client_name": CLIENT_NAME, "redirect_uris": [redirect], "token_endpoint_auth_method": "none"},
        )
        if reg.status_code >= 400:
            raise SystemExit(f"Registration refused: {reg.text}")
        client_id = reg.json()["client_id"]

        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        auth_url = asm["authorization_endpoint"] + "?" + urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "quests",
                "state": state,
                "resource": resource,
            }
        )

        say("Opening the server's consent page. Enter the admin password there to approve IrysQuest.")
        print(f"\nIf the browser didn't open, visit:\n{auth_url}\n")
        if open_browser:
            webbrowser.open(auth_url)

        t = threading.Thread(target=srv.handle_request, daemon=True)
        t.start()
        # Poll instead of one long join: on Windows a blocked join can't be interrupted by Ctrl+C.
        deadline = time.time() + 600
        while t.is_alive() and time.time() < deadline:
            t.join(timeout=0.5)
        srv.server_close()
        res = _Callback.result
        if not res:
            raise SystemExit("Timed out waiting for approval (10 minutes).")
        if res.get("state") != state:
            raise SystemExit("State mismatch on the callback; refusing the code.")
        if "error" in res:
            raise SystemExit(f"Authorization failed: {res.get('error')}: {res.get('error_description')}")

        say("Approved. Exchanging the code for tokens.")
        tok = c.post(
            asm["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": res["code"],
                "redirect_uri": redirect,
                "client_id": client_id,
                "code_verifier": verifier,
                "resource": resource,
            },
        )
        if tok.status_code >= 400:
            raise SystemExit(f"Token exchange failed: {tok.text}")
        j = tok.json()
        tokens = Tokens(
            client_id=client_id,
            token_endpoint=asm["token_endpoint"],
            access_token=j["access_token"],
            refresh_token=j["refresh_token"],
            expires_at=time.time() + float(j.get("expires_in", 3600)),
        )
        save_tokens(token_file, tokens)
        say(f"Signed in. Tokens saved to {token_file}.")
        return tokens


def refresh(tokens: Tokens, token_file: Path) -> Tokens:
    """Rotates the refresh token. The server invalidates the old one, so save at once."""
    with httpx.Client(timeout=20, headers=_H) as c:
        r = c.post(
            tokens.token_endpoint,
            data={"grant_type": "refresh_token", "refresh_token": tokens.refresh_token, "client_id": tokens.client_id},
        )
    if r.status_code >= 400:
        raise SystemExit(f"Session expired ({r.status_code}). Run `irysquest login` again.")
    j = r.json()
    new = Tokens(
        client_id=tokens.client_id,
        token_endpoint=tokens.token_endpoint,
        access_token=j["access_token"],
        refresh_token=j.get("refresh_token", tokens.refresh_token),
        expires_at=time.time() + float(j.get("expires_in", 3600)),
    )
    save_tokens(token_file, new)
    return new
