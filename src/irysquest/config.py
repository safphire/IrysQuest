# SPDX-License-Identifier: AGPL-3.0-or-later
"""Settings, read from .env and the environment. Nothing here is a secret store."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    server_url: str
    meta_api_key: str | None
    stall_days: int
    home: Path

    @property
    def mcp_url(self) -> str:
        return f"{self.server_url}/mcp"

    @property
    def token_file(self) -> Path:
        return self.home / "tokens.json"


def load(env_file: str | os.PathLike | None = None) -> Settings:
    load_dotenv(env_file)
    url = os.environ.get("QUEST_SERVER_URL", "").strip().rstrip("/")
    if url.endswith("/mcp"):
        url = url[: -len("/mcp")]
    if not url.startswith(("http://", "https://")):
        raise SystemExit("QUEST_SERVER_URL is missing or not an http(s) URL. Copy .env.example to .env and fill it in.")
    home = Path(os.environ.get("IRYSQUEST_HOME", ".irysquest"))
    return Settings(
        server_url=url,
        meta_api_key=os.environ.get("META_API_KEY") or None,
        stall_days=int(os.environ.get("STALL_DAYS", "3")),
        home=home,
    )
