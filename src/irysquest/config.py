# SPDX-License-Identifier: AGPL-3.0-or-later
"""Settings, read from .env and the environment. Nothing here is a secret store."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .muse import META_BASE_URL, META_MODEL, Provider


@dataclass(frozen=True)
class Settings:
    server_url: str
    meta_api_key: str | None
    stall_days: int
    home: Path
    provider: str                 # "meta" or "open"
    open_base_url: str
    open_model: str
    open_api_key: str
    serve_host: str
    serve_port: int
    dig_at: str                   # "HH:MM", local time
    try_it_token: str

    @property
    def mcp_url(self) -> str:
        return f"{self.server_url}/mcp"

    @property
    def token_file(self) -> Path:
        return self.home / "tokens.json"

    @property
    def context_file(self) -> Path:
        return self.home / "context.json"

    def muse_provider(self, name: str | None = None) -> Provider:
        name = name or self.provider
        if name == "open":
            return Provider(
                name="open", base_url=self.open_base_url, model=self.open_model, api_key=self.open_api_key,
                transcribe_api_key=self.meta_api_key or "",
            )
        return Provider(name="meta", base_url=META_BASE_URL, model=META_MODEL, api_key=self.meta_api_key or "")


def load(env_file: str | os.PathLike | None = None) -> Settings:
    load_dotenv(env_file)
    url = os.environ.get("QUEST_SERVER_URL", "").strip().rstrip("/")
    if url.endswith("/mcp"):
        url = url[: -len("/mcp")]
    if not url.startswith(("http://", "https://")):
        raise SystemExit("QUEST_SERVER_URL is missing or not an http(s) URL. Copy .env.example to .env and fill it in.")
    return Settings(
        server_url=url,
        meta_api_key=os.environ.get("META_API_KEY") or None,
        stall_days=int(os.environ.get("STALL_DAYS", "3")),
        home=Path(os.environ.get("IRYSQUEST_HOME", ".irysquest")),
        provider=os.environ.get("MUSE_PROVIDER", "meta").strip().lower(),
        open_base_url=os.environ.get("OPEN_BASE_URL", "").rstrip("/"),
        open_model=os.environ.get("OPEN_MODEL", "meta-models/muse-spark-open-1026"),
        open_api_key=os.environ.get("OPEN_API_KEY", ""),
        serve_host=os.environ.get("SERVE_HOST", "0.0.0.0"),
        serve_port=int(os.environ.get("SERVE_PORT", "8787")),
        dig_at=os.environ.get("DIG_AT", "08:00"),
        try_it_token=os.environ.get("TRY_IT_TOKEN", ""),
    )
