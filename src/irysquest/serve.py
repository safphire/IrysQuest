# SPDX-License-Identifier: AGPL-3.0-or-later
"""`irysquest serve`: the capture page, "dig now", and the morning schedule.

A plain HTTP server (no framework) on your PC. Open it from your phone's browser
on the same Wi-Fi: speak a brain dump, snap a notebook page, or press Dig now.
Everything it produces is a proposal in NextQuest; nothing is written directly.

Try-it mode: with TRY_IT_TOKEN set, a visitor who opens /?try=<token> sees what
the agent would propose for *their* dump, and nothing is submitted.

HTTPS (`--https`): phone browsers only allow the microphone on a secure origin,
and http://<LAN IP> isn't one. A self-signed certificate, made once with openssl,
makes it one; the phone shows a certificate warning the first time.
"""

from __future__ import annotations

import json
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .agent import Agent
from .console import say
from .muse import MuseError

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IrysQuest</title>
<style>
:root{--bg:#f6fbf7;--ink:#13261b;--mute:#5d7366;--lime:#c9f26b;--violet:#7a5cff;--card:#fff;--line:#dbe7dd}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
main{max-width:560px;margin:0 auto;padding:20px 16px 48px}h1{font-size:28px;margin:8px 0 2px}.sub{color:var(--mute);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}
h2{font-size:17px;margin:0 0 8px}p{margin:6px 0}button{font:600 15px system-ui;min-height:46px;padding:10px 16px;border-radius:12px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
button.primary{background:var(--lime);border-color:var(--lime)}button.rec{background:#ffe3e3;border-color:#ffb3b3}button:disabled{opacity:.5}
textarea{width:100%;min-height:90px;padding:10px;border-radius:12px;border:1px solid var(--line);font:15px system-ui}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.pill{font-size:12px;color:var(--violet);border:1px solid var(--violet);border-radius:999px;padding:2px 10px}
#log{font:13px/1.45 ui-monospace,Menlo,monospace;background:#102418;color:#d9f5c1;border-radius:12px;padding:12px;max-height:260px;overflow:auto;white-space:pre-wrap}
ul.q{padding-left:18px}ul.q li{margin:6px 0}small{color:var(--mute)}
</style></head><body><main>
<h1>IrysQuest</h1><p class="sub">An agent that digs up what you've buried. It proposes, you approve.</p>
<div id="try" class="card" hidden><span class="pill">Try-it mode</span><p>You're a visitor: you'll see what the agent would propose for your own words. Your words go to Meta's model to produce the preview; nothing is saved to the quest log.</p></div>

<div class="card"><h2>Say it</h2><p><small>Ramble about everything on your mind. The agent splits it into quests.</small></p>
<div class="row"><button id="rec">● Record</button><button id="stop" disabled>■ Stop &amp; send</button><span id="recstate"><small>idle</small></span></div></div>

<div class="card"><h2>Snap it</h2><p><small>A photo of a notebook page, a whiteboard, a sticky-note wall.</small></p>
<div class="row"><input id="photo" type="file" accept="image/*" capture="environment"><button id="sendphoto" class="primary">Read it</button></div></div>

<div class="card"><h2>Type it</h2><textarea id="dump" placeholder="e.g. need to finally finish the pilot script, also mom's birthday, learn to sing properly, fix the bike…"></textarea>
<div class="row"><button id="senddump" class="primary">Turn into quests</button></div></div>

<div id="owner">
<div class="card"><h2>Dig now</h2><p><small>Runs the morning check this minute: stalled quests get a 2–10 minute first step proposed.</small></p>
<div class="row"><button id="dig" class="primary">Dig now</button><button id="digdry">Preview only</button><button id="reckon">Weekly reckoning</button></div></div>
<div class="card"><h2>About you</h2><p><small>Who you are, your schedule, what a "small step" means for you. The agent reads this every time.</small></p>
<textarea id="profile"></textarea><div class="row"><button id="saveprofile">Save</button></div></div>
<div class="card"><h2>Your rules for the coach</h2><p><small>Standing instructions it must follow, e.g. "never park the pilot script", "no steps before 9am", "I prefer physical actions over screen ones".</small></p>
<textarea id="rules"></textarea><div class="row"><button id="saverules">Save</button></div></div>
</div>

<div class="card"><h2>Result</h2><div id="result"><small>Nothing yet.</small></div></div>
<div class="card"><h2>Agent console</h2><div id="log"></div></div>
</main>
<script>
const qs=new URLSearchParams(location.search);const tryTok=qs.get('try');const isTry=!!tryTok;
if(isTry){document.getElementById('try').hidden=false;document.getElementById('owner').hidden=true}
const H={'ngrok-skip-browser-warning':'1'};
const api=(p,opt={})=>fetch(p+(isTry?(p.includes('?')?'&':'?')+'try='+encodeURIComponent(tryTok):''),Object.assign({headers:H},opt)).then(r=>r.json());
function show(j){const r=document.getElementById('result');if(j.error){r.innerHTML='<b>Hmm.</b> '+esc(j.error);return}
 if(j.quests){r.innerHTML=(j.transcript?'<p><small>Heard: '+esc(j.transcript)+'</small></p>':'')+'<ul class="q">'+j.quests.map(q=>'<li><b>'+esc(q.title)+'</b>'+(q.next_step?'<br><small>first step: '+esc(q.next_step)+'</small>':'')+(q.outcome==='proposed'?' <span class="pill">proposed</span>':q.outcome==='preview'?' <span class="pill">preview</span>':'')+'</li>').join('')+'</ul>';return}
 if(j.results){r.innerHTML=j.results.length?'<ul class="q">'+j.results.map(x=>'<li><b>'+esc(x.title)+'</b> — <span class="pill">'+esc(x.move||'')+'</span> '+esc(x.step)+(x.minutes?' <small>('+x.minutes+' min)</small>':'')+' <small>'+esc(x.outcome)+'</small>'+(x.assumption?'<br><small>assuming: '+esc(x.assumption)+'</small>':'')+'</li>').join('')+'</ul>':'<small>Nothing is buried.</small>';return}
 r.innerHTML='<small>'+esc(JSON.stringify(j))+'</small>'}
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function refreshLog(){try{const j=await api('/log');document.getElementById('log').textContent=j.log.map(l=>l.at.slice(11)+'  '+l.text).join('\\n');if(j.profile!==undefined&&document.activeElement.id!=='profile')document.getElementById('profile').value=j.profile;if(j.rules!==undefined&&document.activeElement.id!=='rules')document.getElementById('rules').value=j.rules}catch(e){}}
// Muse Voice Transcribe takes only mono 16-bit PCM WAV at 16 or 24 kHz; browsers record webm/mp4. Convert here.
async function toWav(blob){const ac=new(window.AudioContext||window.webkitAudioContext)();
 try{const src=await ac.decodeAudioData(await blob.arrayBuffer());const n=Math.max(1,Math.ceil(src.duration*16000));
  const oc=new OfflineAudioContext(1,n,16000);const node=oc.createBufferSource();node.buffer=src;node.connect(oc.destination);node.start();  // 1 channel at 16 kHz: mixes down and resamples
  const pcm=(await oc.startRendering()).getChannelData(0);const v=new DataView(new ArrayBuffer(44+pcm.length*2));
  const tag=(o,s)=>{for(let i=0;i<4;i++)v.setUint8(o+i,s.charCodeAt(i))};
  tag(0,'RIFF');v.setUint32(4,36+pcm.length*2,true);tag(8,'WAVE');tag(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);
  v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);tag(36,'data');v.setUint32(40,pcm.length*2,true);
  for(let i=0;i<pcm.length;i++){const x=Math.max(-1,Math.min(1,pcm[i]));v.setInt16(44+i*2,x<0?x*32768:x*32767,true)}
  return new Blob([v],{type:'audio/wav'})}finally{ac.close()}}
let mr,chunks=[];
document.getElementById('rec').onclick=async()=>{if(!window.isSecureContext||!navigator.mediaDevices){show({error:'The microphone only works over HTTPS. Restart with irysquest serve --https and open https://'+location.host+'/'});return}
 let s;try{s=await navigator.mediaDevices.getUserMedia({audio:true})}catch(e){show({error:'Microphone not available: '+((e&&e.message)||e)});return}chunks=[];mr=new MediaRecorder(s);mr.ondataavailable=e=>chunks.push(e.data);
 mr.onstop=async()=>{s.getTracks().forEach(t=>t.stop());document.getElementById('recstate').innerHTML='<small>sending…</small>';let wav;
 try{wav=await toWav(new Blob(chunks,{type:mr.mimeType||'audio/webm'}))}catch(e){show({error:"This browser couldn't convert the recording to WAV: "+((e&&e.message)||e)});document.getElementById('recstate').innerHTML='<small>idle</small>';return}
 const j=await api('/voice',{method:'POST',headers:Object.assign({'Content-Type':'audio/wav'},H),body:wav});show(j);document.getElementById('recstate').innerHTML='<small>idle</small>';refreshLog()};
 mr.start();document.getElementById('rec').classList.add('rec');document.getElementById('rec').disabled=true;document.getElementById('stop').disabled=false;document.getElementById('recstate').innerHTML='<small>recording…</small>'};
document.getElementById('stop').onclick=()=>{mr.stop();document.getElementById('rec').classList.remove('rec');document.getElementById('rec').disabled=false;document.getElementById('stop').disabled=true};
document.getElementById('sendphoto').onclick=async()=>{const f=document.getElementById('photo').files[0];if(!f)return;document.getElementById('result').innerHTML='<small>reading…</small>';
 const j=await api('/photo',{method:'POST',headers:Object.assign({'Content-Type':f.type||'image/jpeg'},H),body:f});show(j);refreshLog()};
document.getElementById('senddump').onclick=async()=>{const t=document.getElementById('dump').value.trim();if(!t)return;document.getElementById('result').innerHTML='<small>thinking…</small>';
 const j=await api('/text',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({text:t})});show(j);refreshLog()};
document.getElementById('dig').onclick=async()=>{document.getElementById('result').innerHTML='<small>digging…</small>';show(await api('/dig',{method:'POST'}));refreshLog()};
document.getElementById('reckon').onclick=async()=>{document.getElementById('result').innerHTML='<small>looking at the whole board…</small>';const j=await api('/reckon',{method:'POST'});const r=document.getElementById('result');r.innerHTML=j.error?esc(j.error):'<p><span class="pill">'+esc(j.verdict)+'</span> '+esc(j.reason)+'</p><p><small>'+esc(j.board_read)+'</small></p>';refreshLog()};
document.getElementById('digdry').onclick=async()=>{document.getElementById('result').innerHTML='<small>previewing…</small>';show(await api('/dig?dry=1',{method:'POST'}));refreshLog()};
document.getElementById('saverules').onclick=async()=>{await api('/rules',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({rules:document.getElementById('rules').value})});refreshLog()};
document.getElementById('saveprofile').onclick=async()=>{await api('/profile',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({profile:document.getElementById('profile').value})});refreshLog()};
refreshLog();setInterval(refreshLog,5000);
</script></body></html>"""


class _State:
    agent: Agent
    try_token: str
    lock = threading.Lock()


def make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, obj) -> None:
            data = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _is_visitor(self) -> bool:
            q = parse_qs(urlparse(self.path).query)
            tok = (q.get("try") or [""])[0]
            return bool(state.try_token) and tok == state.try_token

        def _body(self) -> bytes:
            return self.rfile.read(int(self.headers.get("Content-Length", 0)))

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                data = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path == "/log":
                ctx = state.agent.ctx
                visitor = self._is_visitor()
                self._json(200, {"log": [] if visitor else ctx.log[-60:], **({} if visitor else {"profile": ctx.profile, "rules": ctx.rules})})
            elif path == "/health":
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            path = urlparse(self.path).path
            visitor = self._is_visitor()
            preview = visitor
            warn = say if visitor else (lambda text: state.agent._say(text, "warn"))
            try:
                with state.lock:
                    ag = state.agent
                    ag.record = not visitor   # a visitor's words never reach the owner's log or context.json
                    try:
                        if path == "/text":
                            text = json.loads(self._body() or b"{}").get("text", "").strip()
                            if not text:
                                return self._json(400, {"error": "Nothing to read."})
                            ag._say("Reading a typed brain dump.")
                            quests = ag.muse.capture_text(text, "" if visitor else ag.ctx.profile)
                            return self._json(200, {"quests": ag.capture(quests, source="notes", preview=preview)})
                        if path == "/voice":
                            audio = self._body()
                            if len(audio) < 1000:
                                return self._json(400, {"error": "That recording is empty."})
                            ag._say(f"Transcribing {len(audio) // 1024} KB of audio with Muse Voice Transcribe.")
                            transcript = ag.muse.transcribe(audio, "capture.wav")
                            ag._say(f'Heard: "{transcript[:160]}{"…" if len(transcript) > 160 else ""}"')
                            quests = ag.muse.capture_text(transcript, "" if visitor else ag.ctx.profile)
                            return self._json(200, {"transcript": transcript, "quests": ag.capture(quests, source="voice note", preview=preview)})
                        if path == "/photo":
                            image = self._body()
                            mime = self.headers.get("Content-Type", "image/jpeg").split(";")[0]
                            if len(image) < 1000:
                                return self._json(400, {"error": "No photo received."})
                            ag._say(f"Reading a {len(image) // 1024} KB photo with Muse Spark.")
                            quests = ag.muse.capture_image(image, mime, "" if visitor else ag.ctx.profile)
                            return self._json(200, {"quests": ag.capture(quests, source="photo", preview=preview)})
                        if visitor:
                            return self._json(403, {"error": "Visitors can only preview captures."})
                        if path == "/dig":
                            dry = (parse_qs(urlparse(self.path).query).get("dry") or ["0"])[0] == "1"
                            results = ag.dig(dry_run=dry)
                            return self._json(200, {"results": [r.__dict__ for r in results]})
                        if path == "/reckon":
                            v = ag.reckoning()
                            return self._json(200, v.__dict__)
                        if path == "/profile":
                            ag.set_profile(json.loads(self._body() or b"{}").get("profile", ""))
                            return self._json(200, {"ok": True})
                        if path == "/rules":
                            ag.set_rules(json.loads(self._body() or b"{}").get("rules", ""))
                            return self._json(200, {"ok": True})
                        return self._json(404, {"error": "not found"})
                    finally:
                        ag.record = True
            except MuseError as e:
                warn(f"Muse error: {e}")
                return self._json(502, {"error": str(e)})
            except Exception as e:  # keep the page alive whatever happens
                warn(f"Unexpected error: {e!r}")
                return self._json(500, {"error": "Something went wrong; see the console."})

        def log_message(self, *a):
            pass

    return Handler


def _schedule(state: _State, dig_at: str, stop: threading.Event) -> None:
    hh, mm = (int(x) for x in dig_at.split(":"))
    while not stop.is_set():
        now = datetime.now()
        nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        say(f"Next scheduled dig at {nxt:%a %H:%M}.")
        if stop.wait((nxt - now).total_seconds()):
            return
        with state.lock:
            try:
                state.agent._say("Morning. Checking what's buried.")
                state.agent.dig()
                if datetime.now().weekday() == 6:   # Sunday: the weekly reckoning
                    state.agent.reckoning()
            except Exception as e:
                state.agent._say(f"Scheduled dig failed: {e!r}", "warn")


def lan_ip() -> str:
    """The address other devices on the network reach this PC at. Nothing is sent (UDP connect only)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def ensure_cert(tls_dir: Path, ip: str) -> tuple[Path, Path]:
    """A self-signed certificate for localhost and this PC's LAN IP, made once with openssl."""
    cert, key = tls_dir / "cert.pem", tls_dir / "key.pem"
    if cert.exists() and key.exists():
        return cert, key
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("--https needs openssl on PATH (Git for Windows ships one). "
                         "Or tunnel the page instead: ngrok http 8787 (see README).")
    tls_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365",
                    "-keyout", str(key), "-out", str(cert), "-subj", "/CN=IrysQuest dev",
                    "-addext", f"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{ip}"],
                   check=True, capture_output=True)
    return cert, key


class CaptureServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # A phone refusing the self-signed certificate, or plain http on the https port: expected, not worth a traceback.
        if isinstance(sys.exc_info()[1], (ssl.SSLError, ConnectionError)):
            return
        super().handle_error(request, client_address)


def use_tls(srv: ThreadingHTTPServer, cert: Path, key: Path) -> None:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    # Handshake on first read, in the request's thread, so one slow client can't block accept().
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True, do_handshake_on_connect=False)


def serve(agent: Agent, host: str, port: int, dig_at: str, try_token: str, tls_dir: Path | None = None) -> None:
    state = _State()
    state.agent, state.try_token = agent, try_token
    stop = threading.Event()
    threading.Thread(target=_schedule, args=(state, dig_at, stop), daemon=True).start()
    srv = CaptureServer((host, port), make_handler(state))
    ip, scheme = lan_ip(), "https" if tls_dir else "http"
    if tls_dir:
        use_tls(srv, *ensure_cert(tls_dir, ip))
    say(f"Capture page at {scheme}://{host}:{port}/  (on your phone: {scheme}://{ip}:{port}/)")
    if tls_dir:
        say("Self-signed certificate: the phone warns once; choose Advanced → Proceed.")
    if try_token:
        say(f"Try-it link for friends: {scheme}://{ip}:{port}/?try={try_token}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.server_close()
        say("Stopped.")
