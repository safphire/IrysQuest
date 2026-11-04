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
from .muse import CapturedQuest, MuseError

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>IrysQuest</title>
<style>
:root{--bg:#f3faf5;--ink:#10231a;--mute:#5c6f64;--line:#d9e6dd;--card:#ffffff;--lime:#d8f26b;--lime-ink:#1d3a12;--mint:#b8f2d4;--violet:#6b4cf6;--violet-bg:#efeafe;--danger:#ffe0e0;--danger-line:#ffb3b3;--radius:14px}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;font:16px/1.5 -apple-system,system-ui,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink)}
main{max-width:520px;margin:0 auto;padding:12px 16px calc(40px + env(safe-area-inset-bottom))}
header{display:flex;align-items:baseline;justify-content:space-between;padding:6px 0 14px}
header h1{font-size:22px;letter-spacing:-.01em;margin:0}header h1 span{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--lime);margin-right:8px;vertical-align:1px}
header small{color:var(--mute)}
#status{position:sticky;top:0;z-index:5;display:none;align-items:center;gap:10px;margin:0 -16px 12px;padding:10px 16px;background:var(--ink);color:#e9f8ee;font-size:14px}
#status.on{display:flex}#status .dot{width:10px;height:10px;border-radius:50%;background:var(--lime);animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
section{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin:0 0 12px}
h2{font-size:15px;font-weight:650;margin:0 0 4px}.hint{margin:0 0 12px;color:var(--mute);font-size:14px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.grow{flex:1 1 auto}
button,label.btn{font:600 15px -apple-system,system-ui,"Segoe UI",Roboto,sans-serif;min-height:46px;padding:10px 16px;border-radius:12px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px}
button.primary,label.btn.primary{background:var(--lime);border-color:var(--lime);color:var(--lime-ink)}button.quiet{border-color:transparent;background:transparent;color:var(--violet);padding-left:8px;padding-right:8px}
button.rec{background:var(--danger);border-color:var(--danger-line)}button:disabled,label.btn.off{opacity:.45;pointer-events:none}
textarea,input[type=text]{width:100%;padding:11px 12px;border-radius:12px;border:1px solid var(--line);font:15px/1.4 -apple-system,system-ui,"Segoe UI",Roboto,sans-serif;background:#fbfdfb;color:var(--ink)}textarea{min-height:88px;resize:vertical}
textarea:focus,input:focus{outline:2px solid var(--mint);border-color:var(--mint)}
.state{font-size:13px;color:var(--mute)}
.pill{font-size:12px;font-weight:600;color:var(--violet);background:var(--violet-bg);border-radius:999px;padding:3px 10px;white-space:nowrap}
.pill.ok{color:#1d5a2f;background:#dff7e6}.pill.warn{color:#7a4b00;background:#fff1d6}
#result:empty::before{content:"Nothing yet. Say it, snap it, or type it.";color:var(--mute);font-size:14px}
.res{border-top:1px solid var(--line);padding:12px 0 4px;margin-top:8px}.res:first-child{border-top:0;padding-top:0;margin-top:0}.res time{display:block;font-size:12px;color:var(--mute);margin-bottom:6px}
.quest{padding:10px 12px;border:1px solid var(--line);border-radius:12px;margin:8px 0;background:#fbfdfb}.quest b{font-size:15px}.quest .meta{display:block;color:var(--mute);font-size:13px;margin-top:2px}
.quest label{display:block;margin-top:8px;font-size:14px;color:var(--ink)}.quest label input{margin-top:6px}
.heard{font-size:14px;color:var(--mute);font-style:italic;margin:0 0 8px}
.verdict{display:flex;gap:10px;align-items:flex-start}.verdict .pill{margin-top:3px}
details{border-top:1px solid var(--line);margin-top:8px;padding-top:8px}section>details:first-child{border-top:0;margin-top:0;padding-top:0}details summary{cursor:pointer;font-weight:650;font-size:15px;list-style:none;display:flex;justify-content:space-between}details summary::after{content:"+";color:var(--mute)}details[open] summary::after{content:"–"}
details .body{padding-top:10px}
#log{font:12.5px/1.45 ui-monospace,Menlo,Consolas,monospace;background:#0f1f16;color:#cdefc0;border-radius:12px;padding:12px;max-height:240px;overflow:auto;white-space:pre-wrap}
.try{background:var(--violet-bg);border-color:transparent}
</style></head><body><main>
<header><h1><span></span>IrysQuest</h1><small>proposes · you decide</small></header>
<div id="status" role="status" aria-live="polite"><span class="dot"></span><span id="statustext"></span></div>
<section id="try" class="try" hidden><h2>Try-it mode</h2><p class="hint" style="margin:0">You're a visitor: you'll see what the agent would propose for your own words. Your words go to Meta's model to produce the preview; nothing is saved to the quest log.</p></section>

<section><h2>Say it</h2><p class="hint">Ramble about everything on your mind. The agent splits it into quests and asks what done looks like.</p>
<div class="row"><button id="rec" class="primary">● Record</button><button id="stop" disabled>■ Stop &amp; send</button><span id="recstate" class="state">idle</span></div></section>

<section><h2>Snap it</h2><p class="hint">A notebook page, a whiteboard, a sticky-note wall.</p>
<div class="row"><label class="btn grow">📷 Take a photo<input id="camera" type="file" accept="image/*" capture="environment" hidden></label><label class="btn grow">Gallery<input id="photo" type="file" accept="image/*" hidden></label></div>
<div class="row" style="margin-top:8px"><span id="photoname" class="state grow">no photo yet</span><button id="sendphoto" class="primary" disabled>Read it</button></div></section>

<section><h2>Type it</h2><textarea id="dump" placeholder="finish the pilot script, mom's birthday, learn to sing properly, fix the bike…"></textarea>
<div class="row" style="margin-top:8px"><button id="senddump" class="primary">Turn into quests</button></div></section>

<section><h2>Result</h2><div id="result"></div></section>

<div id="owner">
<section><h2>The morning check, now</h2><p class="hint">Runs at 08:00 on its own. Run it this minute, or just look.</p>
<div class="row"><button id="dig" class="primary">Dig now</button><button id="digdry">Preview only</button><button id="reckon" class="quiet">Weekly reckoning</button></div>
<details><summary>About you</summary><div class="body"><p class="hint">Who you are, your schedule, what a small step means for you. The coach reads this every time.</p><textarea id="profile"></textarea><div class="row" style="margin-top:8px"><button id="saveprofile">Save</button><span id="profilestate" class="state"></span></div></div></details>
<details><summary>Your rules for the coach</summary><div class="body"><p class="hint">Standing instructions, e.g. "never park the pilot script", "no steps before 9am", "physical actions over screen ones".</p><textarea id="rules"></textarea><div class="row" style="margin-top:8px"><button id="saverules">Save</button><span id="rulesstate" class="state"></span></div></div></details>
</section>
<section><details><summary>Agent console</summary><div class="body"><div id="log"></div></div></details></section>
</div>
</main>
<script>
const qs=new URLSearchParams(location.search);const tryTok=qs.get('try');const isTry=!!tryTok;
if(isTry){document.getElementById('try').hidden=false;document.getElementById('owner').hidden=true}
window.addEventListener('error',e=>{idle();keep('<p><b>Hmm.</b> '+esc(e.message)+'</p>')});window.addEventListener('unhandledrejection',e=>{idle();keep('<p><b>Hmm.</b> '+esc((e.reason&&e.reason.message)||e.reason)+'</p>')});
const H={'ngrok-skip-browser-warning':'1'};
const api=(p,opt={})=>fetch(p+(isTry?(p.includes('?')?'&':'?')+'try='+encodeURIComponent(tryTok):''),Object.assign({headers:H},opt)).then(r=>r.json());
let settleBatch=null;
const $=id=>document.getElementById(id);
function busy(m){$('statustext').textContent=m;$('status').classList.add('on');document.querySelectorAll('button.primary,#dig,#digdry,#reckon').forEach(b=>{if(!b.dataset.wasDisabled)b.dataset.wasDisabled=b.disabled?'1':'0';b.disabled=true})}
function idle(){$('status').classList.remove('on');document.querySelectorAll('button').forEach(b=>{if(b.dataset.wasDisabled!==undefined){b.disabled=b.dataset.wasDisabled==='1';delete b.dataset.wasDisabled}})}
function keep(html){idle();const r=$('result');const t=new Date().toTimeString().slice(0,5);r.insertAdjacentHTML('afterbegin','<div class="res"><time>'+t+'</time>'+html+'</div>');while(r.children.length>5)r.lastChild.remove();r.closest('section').scrollIntoView({behavior:'smooth',block:'start'})}
const questCard=(q,i)=>'<div class="quest"><b>'+esc(q.title)+'</b>'+(q.next_step?'<span class="meta">first step: '+esc(q.next_step)+'</span>':'')+(q.question?'<label>'+esc(q.question)+'<input type="text" id="why'+i+'" value="'+esc(q.why||'')+'" placeholder="one line, what done looks like"></label>':(q.why?'<span class="meta">why: '+esc(q.why)+'</span>':''))+'</div>';
function show(j){if(j.error){keep('<p><b>Hmm.</b> '+esc(j.error)+'</p>');return}
 if(j.settle){settleBatch=j;keep((j.transcript?'<p class="heard">“'+esc(j.transcript)+'”</p>':'')+'<p class="hint">'+j.quests.length+' quest'+(j.quests.length===1?'':'s')+'. Before they are proposed, say what done looks like; that becomes the Why of each. Blank is fine, the coach may ask later.</p>'+j.quests.map(questCard).join('')+'<div class="row" style="margin-top:10px"><button id="propose" class="primary">Propose these</button><button id="discard" class="quiet">Discard</button></div>');
  $('propose').onclick=proposeSettled;$('discard').onclick=()=>{settleBatch=null;document.querySelector('.res').remove()};return}
 if(j.quests){keep((j.transcript?'<p class="heard">“'+esc(j.transcript)+'”</p>':'')+j.quests.map(q=>'<div class="quest"><b>'+esc(q.title)+'</b> '+(q.outcome==='proposed'?'<span class="pill ok">proposed</span>':q.outcome==='preview'?'<span class="pill">preview</span>':q.outcome==='already there'?'<span class="pill">already there</span>':'<span class="pill warn">'+esc(q.outcome)+'</span>')+(q.why?'<span class="meta">why: '+esc(q.why)+'</span>':'')+(q.next_step?'<span class="meta">first step: '+esc(q.next_step)+'</span>':'')+'</div>').join('')+(j.quests.some(q=>q.outcome==='proposed')?'<p class="hint" style="margin:8px 0 0">Waiting in the app’s Proposals screen.</p>':''));return}
 if(j.results){keep(j.results.length?j.results.map(x=>'<div class="quest"><b>'+esc(x.title)+'</b> <span class="pill">'+esc((x.move||'').replace('_',' '))+'</span><span class="meta">'+esc(x.step)+(x.minutes?' · '+x.minutes+' min':'')+' · '+esc(x.outcome)+'</span>'+(x.assumption?'<span class="meta">assuming: '+esc(x.assumption)+'</span>':'')+'</div>').join(''):'<p class="hint" style="margin:0">Nothing is buried.</p>');return}
 if(j.verdict){keep('<div class="verdict"><span class="pill">'+esc(j.verdict)+'</span><div>'+esc(j.reason)+'<span class="meta" style="display:block;color:var(--mute);font-size:13px;margin-top:4px">'+esc(j.board_read)+'</span></div></div>');return}
 keep('<span class="state">'+esc(JSON.stringify(j))+'</span>')}
async function proposeSettled(){if(!settleBatch)return;const b=settleBatch;const quests=b.quests.map((q,i)=>({title:q.title,next_step:q.next_step||'',why:($('why'+i)?$('why'+i).value:q.why||'').trim()}));
 busy('Proposing to the app…');const j=await api('/propose',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({quests,source:b.source})});settleBatch=null;const old=document.querySelector('.res');if(old)old.remove();show(j);refreshLog()}
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
 mr.onstop=async()=>{s.getTracks().forEach(t=>t.stop());document.getElementById('recstate').textContent='sending…';busy('Transcribing with Muse Voice, then splitting into quests…');let wav;
 try{wav=await toWav(new Blob(chunks,{type:mr.mimeType||'audio/webm'}))}catch(e){show({error:"This browser couldn't convert the recording to WAV: "+((e&&e.message)||e)});document.getElementById('recstate').textContent='idle';idle();return}
 const j=await api('/voice',{method:'POST',headers:Object.assign({'Content-Type':'audio/wav'},H),body:wav});show(j);document.getElementById('recstate').textContent='idle';refreshLog()};
 mr.start();document.getElementById('rec').classList.add('rec');document.getElementById('rec').disabled=true;document.getElementById('stop').disabled=false;document.getElementById('recstate').textContent='recording…'};
document.getElementById('stop').onclick=()=>{mr.stop();document.getElementById('rec').classList.remove('rec');document.getElementById('rec').disabled=false;document.getElementById('stop').disabled=true};
let photoFile=null;for(const id of ['camera','photo'])document.getElementById(id).onchange=e=>{photoFile=e.target.files[0]||null;document.getElementById('photoname').textContent=photoFile?(photoFile.name||'photo')+' · '+Math.round(photoFile.size/1024)+' KB':'no photo yet';document.getElementById('sendphoto').disabled=!photoFile};
document.getElementById('sendphoto').onclick=async()=>{const f=photoFile;if(!f)return;busy('Reading the photo with Muse Spark…');
 const j=await api('/photo',{method:'POST',headers:Object.assign({'Content-Type':f.type||'image/jpeg'},H),body:f});show(j);refreshLog()};
document.getElementById('senddump').onclick=async()=>{const t=document.getElementById('dump').value.trim();if(!t)return;busy('Splitting into quests…');
 const j=await api('/text',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({text:t})});show(j);refreshLog()};
document.getElementById('dig').onclick=async()=>{busy('Digging: the coach is looking at each stalled quest…');show(await api('/dig',{method:'POST'}));refreshLog()};
document.getElementById('reckon').onclick=async()=>{busy('Reading the whole board…');show(await api('/reckon',{method:'POST'}));refreshLog()};
document.getElementById('digdry').onclick=async()=>{busy('Previewing: nothing will be proposed…');show(await api('/dig?dry=1',{method:'POST'}));refreshLog()};
document.getElementById('saverules').onclick=async()=>{$('rulesstate').textContent='saving…';await api('/rules',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({rules:document.getElementById('rules').value})});$('rulesstate').textContent='saved';refreshLog()};
document.getElementById('saveprofile').onclick=async()=>{$('profilestate').textContent='saving…';await api('/profile',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},H),body:JSON.stringify({profile:document.getElementById('profile').value})});$('profilestate').textContent='saved';refreshLog()};
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

        @staticmethod
        def _settled(ag: Agent, quests: list[CapturedQuest], source: str, visitor: bool) -> dict:
            """Captures are previewed first. The owner gets one what-does-done-look-like question per quest and
            proposes from the page (/propose) once answered; a visitor only ever sees the preview."""
            rows = ag.capture(quests, source=source, preview=True)
            if visitor:
                return {"quests": rows}
            for row, question in zip(rows, ag.settle_questions(quests)):
                row["question"] = question
            asked = sum(1 for r in rows if r.get("question"))
            if rows:
                ag._say(f"  {len(rows)} quest(s) captured; {asked} question(s) to settle what done looks like.")
            return {"quests": rows, "settle": True, "source": source}

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
                            return self._json(200, self._settled(ag, quests, "notes", visitor))
                        if path == "/voice":
                            audio = self._body()
                            if len(audio) < 1000:
                                return self._json(400, {"error": "That recording is empty."})
                            if not getattr(ag.muse, "replay", False):
                                ag._say(f"Transcribing {len(audio) // 1024} KB of audio with Muse Voice Transcribe.")
                            transcript = ag.muse.transcribe(audio, "capture.wav")
                            ag._say(f'Heard: "{transcript[:160]}{"…" if len(transcript) > 160 else ""}"')
                            quests = ag.muse.capture_text(transcript, "" if visitor else ag.ctx.profile)
                            return self._json(200, {"transcript": transcript, **self._settled(ag, quests, "voice note", visitor)})
                        if path == "/photo":
                            image = self._body()
                            mime = self.headers.get("Content-Type", "image/jpeg").split(";")[0]
                            if len(image) < 1000:
                                return self._json(400, {"error": "No photo received."})
                            if not getattr(ag.muse, "replay", False):
                                ag._say(f"Reading a {len(image) // 1024} KB photo with Muse Spark.")
                            quests = ag.muse.capture_image(image, mime, "" if visitor else ag.ctx.profile)
                            return self._json(200, self._settled(ag, quests, "photo", visitor))
                        if visitor:
                            return self._json(403, {"error": "Visitors can only preview captures."})
                        if path == "/propose":
                            body = json.loads(self._body() or b"{}")
                            quests = [CapturedQuest(title=str(q.get("title", ""))[:500].strip(), why=str(q.get("why", ""))[:500].strip(),
                                                    next_step=str(q.get("next_step", ""))[:2000].strip())
                                      for q in body.get("quests", []) if str(q.get("title", "")).strip()]
                            if not quests:
                                return self._json(400, {"error": "Nothing to propose."})
                            settled = sum(1 for q in quests if q.why)
                            ag._say(f"Settled: {settled} of {len(quests)} quests have a why. Proposing.")
                            return self._json(200, {"quests": ag.capture(quests, source=str(body.get("source", "notes"))[:40])})
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
    if host in ("127.0.0.1", "localhost", "::1"):
        say(f"Capture page at {scheme}://localhost:{port}/  (this machine only)")
    else:
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
