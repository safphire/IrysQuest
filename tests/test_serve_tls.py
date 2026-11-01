# SPDX-License-Identifier: AGPL-3.0-or-later
"""`serve --https`: the self-signed certificate and the page over TLS. Needs openssl on PATH."""

import shutil
import ssl
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

import httpx
import pytest

from irysquest import serve

pytestmark = pytest.mark.skipif(not shutil.which("openssl"), reason="openssl not on PATH")


def test_cert_covers_localhost_and_the_lan_ip(tmp_path):
    cert, key = serve.ensure_cert(tmp_path / "tls", "192.168.0.53")
    info = ssl._ssl._test_decode_cert(str(cert))
    assert ("IP Address", "192.168.0.53") in info["subjectAltName"] and ("DNS", "localhost") in info["subjectAltName"]
    # Made once: a second call reuses the files.
    mtime = cert.stat().st_mtime
    assert serve.ensure_cert(tmp_path / "tls", "10.0.0.9") == (cert, key) and cert.stat().st_mtime == mtime


def test_page_is_served_over_https(tmp_path):
    state = serve._State()
    state.agent, state.try_token = SimpleNamespace(ctx=SimpleNamespace(log=[], profile="", rules="")), ""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(state))
    serve.use_tls(srv, *serve.ensure_cert(tmp_path / "tls", "127.0.0.1"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"https://127.0.0.1:{srv.server_address[1]}"
        assert httpx.get(f"{base}/health", verify=False).json() == {"ok": True}
        assert "getUserMedia" in httpx.get(f"{base}/", verify=False).text
    finally:
        srv.shutdown()
