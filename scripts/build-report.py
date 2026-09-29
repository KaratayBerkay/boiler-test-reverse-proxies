#!/usr/bin/env python3
"""Render results/<stack>/latest.json into one self-contained HTML report (docs/report.html).

The compacted results are embedded as a JSON blob and rendered by inline JS (no external data files, no libraries).
Run: uv run --project harness python scripts/build-report.py [--out docs/report.html]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
from pxlab.phases.load import SCENARIOS          # noqa: E402
from pxlab.probes import GROUPS, PROBES          # noqa: E402
from pxlab.report import load_all                # noqa: E402


def compact(res: dict) -> dict:
    stacks = {}
    for key, r in res.items():
        ph = r.get("phases", {})
        caps = (ph.get("capabilities") or {}).get("probes") or {}
        load = (ph.get("load") or {}).get("scenarios") or {}
        chaos = ph.get("chaos") or {}
        sc = {}
        for sid, s in load.items():
            px = s.get("proxy") or {}
            sc[sid] = {
                "status": s.get("status"), "detail": str(s.get("detail") or s.get("stderr_tail") or "")[:200],
                "rps": s.get("rps"), "p50": s.get("p50"), "p90": s.get("p90"), "p99": s.get("p99"), "max": s.get("max"),
                "requests": s.get("requests"), "errors": s.get("errors"), "non2xx": s.get("non2xx"),
                "bytes_per_s": s.get("bytes_per_s"),
                "cores": px.get("cpu_cores_avg"), "cpu_pct": px.get("cpu_pct_of_limit"), "us_req": px.get("cpu_us_per_request"),
                "mem_end": px.get("mem_end_mb"), "mem_peak": px.get("mem_peak_mb"),
                "backend_cores": (s.get("backends") or {}).get("cpu_cores_avg"),
                "codes": s.get("status_codes") or {}, "error_samples": s.get("error_samples") or {},
                "loadgen_cores": (s.get("loadgen") or {}).get("cpu_cores_avg"),
            }
        f, rl = chaos.get("failover") or {}, chaos.get("reload") or {}
        stacks[key] = {
            "display": r.get("display"), "image": r.get("image"), "family": r.get("family"), "category": r.get("category"),
            "version": r.get("version"), "image_size": r.get("image_size"), "startup_s": r.get("startup_s"),
            "notes": r.get("notes"), "docs": r.get("docs") or [], "reload_kind": r.get("reload_kind"),
            "unsupported": r.get("unsupported") or {},
            "started": r.get("started"), "finished": r.get("finished"),
            "caps": {pid: {"s": c.get("status"), "d": str(c.get("detail") or "")[:300]} for pid, c in caps.items()},
            "summary": (ph.get("capabilities") or {}).get("summary") or {},
            "load": sc,
            "chaos": {
                "failover": {"status": f.get("status"), "detail": f.get("detail"), "load": f.get("load"), "timeline": f.get("timeline"),
                             "back_after": f.get("app2_back_after_s")},
                "reload": {"status": rl.get("status"), "detail": rl.get("detail"), "load": rl.get("load"), "timeline": rl.get("timeline"),
                           "seconds": rl.get("reload_seconds")},
            } if chaos else {},
        }
    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "groups": GROUPS,
        "probes": [{"id": p.id, "group": p.group, "title": p.title, "proves": p.proves} for p in PROBES],
        "scenarios": [{"id": s.id, "title": s.title, "tool": s.tool, "metric": s.metric} for s in SCENARIOS],
        "stacks": stacks,
    }


HTML = r"""<title>Reverse Proxy Lab</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@87.5,500;87.5,700;100,400;100,600&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{
  --bg:#f4f6f9;--surface:#ffffff;--surface-2:#eaeef4;--ink:#0d1626;--muted:#5c6779;--line:#d5dbe5;--line-strong:#aeb8c8;
  --accent:#1f4fd0;--accent-ink:#ffffff;--accent-soft:#e3eafd;
  --ok:#1d7a3e;--ok-soft:#dcf3e3;--fail:#b3261e;--fail-soft:#f8dcd9;--warn:#a05a00;--warn-soft:#fbe9cf;--na:#8b95a7;--na-soft:#e6e9ef;
  --bar:#3b6be0;--bar-2:#9db4ec;--shadow:0 1px 2px rgba(13,22,38,.06),0 6px 20px rgba(13,22,38,.06);
  color-scheme:light;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0e1420;--surface:#161d2b;--surface-2:#1e2736;--ink:#e7ebf2;--muted:#9aa5b8;--line:#2a3446;--line-strong:#3c4860;
  --accent:#7fa3ff;--accent-ink:#0e1420;--accent-soft:#1c2a4b;
  --ok:#5fd38a;--ok-soft:#153724;--fail:#ff8a80;--fail-soft:#4a1d1a;--warn:#f2b45c;--warn-soft:#3e2a10;--na:#7d879a;--na-soft:#242c3b;
  --bar:#6c92f0;--bar-2:#3b4f7c;--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);color-scheme:dark;}}
:root[data-theme="dark"]{
  --bg:#0e1420;--surface:#161d2b;--surface-2:#1e2736;--ink:#e7ebf2;--muted:#9aa5b8;--line:#2a3446;--line-strong:#3c4860;
  --accent:#7fa3ff;--accent-ink:#0e1420;--accent-soft:#1c2a4b;
  --ok:#5fd38a;--ok-soft:#153724;--fail:#ff8a80;--fail-soft:#4a1d1a;--warn:#f2b45c;--warn-soft:#3e2a10;--na:#7d879a;--na-soft:#242c3b;
  --bar:#6c92f0;--bar-2:#3b4f7c;--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);color-scheme:dark;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Source Sans 3","Segoe UI",system-ui,sans-serif;font-size:15px;line-height:1.5;padding-inline:clamp(16px,3vw,40px);padding-block:0 64px}
h1,h2,h3{font-family:"Archivo","Helvetica Neue",Arial,sans-serif;font-stretch:87.5%;text-wrap:balance;margin:0}
h1{font-size:clamp(28px,4vw,42px);font-weight:700;letter-spacing:-.01em;line-height:1.05}
h2{font-size:22px;font-weight:700;margin-block:0 12px}
h3{font-size:16px;font-weight:600}
.mono,td.num,th.num,.num{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
.eyebrow{font-family:"Archivo",sans-serif;font-stretch:87.5%;text-transform:uppercase;letter-spacing:.12em;font-size:11px;color:var(--muted);font-weight:600}
a{color:var(--accent)}
header{max-width:1280px;margin:0 auto;padding-block:32px 20px;display:grid;gap:10px}
header p.lede{max-width:70ch;margin:0;color:var(--muted);font-size:16px}
.meta{display:flex;flex-wrap:wrap;gap:8px 22px;color:var(--muted);font-size:13px}
.meta b{color:var(--ink);font-weight:600}
nav.tabs{position:sticky;top:0;z-index:5;background:var(--bg);max-width:1280px;margin:0 auto;display:flex;gap:4px;padding-block:8px;border-bottom:1px solid var(--line);overflow-x:auto}
nav.tabs button{font:inherit;font-family:"Archivo",sans-serif;font-stretch:87.5%;font-weight:600;font-size:14px;color:var(--muted);background:transparent;border:1px solid transparent;border-radius:6px;padding:6px 12px;cursor:pointer;white-space:nowrap}
nav.tabs button[aria-selected="true"]{color:var(--accent);background:var(--accent-soft)}
nav.tabs button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
main{max-width:1280px;margin:0 auto}
section.panel{display:none;padding-block:24px}section.panel.active{display:block}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px 20px}
.grid{display:grid;gap:16px}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--surface-2);font-family:"Archivo",sans-serif;font-stretch:87.5%;font-weight:600;font-size:12.5px;letter-spacing:.02em;white-space:nowrap;z-index:1}
td.num,th.num{text-align:right;white-space:nowrap}
tbody tr:hover td{background:var(--surface-2)}
tbody tr:last-child td{border-bottom:0}
.pill{display:inline-block;font-family:"JetBrains Mono",monospace;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid transparent}
.pill.ok{background:var(--ok-soft);color:var(--ok)}.pill.fail{background:var(--fail-soft);color:var(--fail)}.pill.na{background:var(--na-soft);color:var(--na)}.pill.warn{background:var(--warn-soft);color:var(--warn)}
.stack{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--na-soft);min-width:140px}
.stack i{display:block;height:100%}.stack .ok{background:var(--ok)}.stack .fail{background:var(--fail)}.stack .err{background:var(--warn)}.stack .na{background:var(--na)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--muted);margin-block:10px 14px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.matrix td.c{text-align:center;font-size:15px;padding:4px 6px;cursor:default}
.matrix td.g{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
.matrix th.rot{writing-mode:vertical-rl;transform:rotate(180deg);text-align:left;padding:10px 4px;height:120px;font-size:12px}
.matrix tr.group td{background:var(--surface-2);font-weight:600;color:var(--ink);text-transform:none;letter-spacing:0;font-size:13px}
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;vertical-align:-1px}
.dot.ok{background:var(--ok)}.dot.fail{background:var(--fail)}.dot.error{background:var(--warn)}.dot.unsupported{background:transparent;border:2px solid var(--na);width:10px;height:10px}.dot.none{background:transparent}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-block:0 12px}
.filters button{font:inherit;font-size:13px;padding:4px 10px;border-radius:999px;border:1px solid var(--line-strong);background:var(--surface);color:var(--ink);cursor:pointer}
.filters button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,560px),1fr));gap:16px}
.chart h3{margin-bottom:2px}.chart .sub{color:var(--muted);font-size:13px;margin:0 0 8px}
.bars{display:grid;grid-template-columns:max-content 1fr max-content;gap:5px 10px;align-items:center;font-size:13px}
.bars .lab{white-space:nowrap}.bars .lab.win{font-weight:600}
.bars .track{height:16px;background:var(--surface-2);border-radius:3px;position:relative;overflow:hidden}
.bars .track i{position:absolute;left:0;top:0;bottom:0;background:var(--bar);border-radius:3px}
.bars .track i.win{background:var(--accent)}
.bars .val{font-family:"JetBrains Mono",monospace;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--muted)}
.bars .val b{color:var(--ink);font-weight:600}
.bars .val.bad{color:var(--fail)}
select{font:inherit;padding:6px 10px;border-radius:6px;border:1px solid var(--line-strong);background:var(--surface);color:var(--ink)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media (max-width:820px){.two{grid-template-columns:1fr}}
.note{color:var(--muted);font-size:13px}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:14px}.kv dt{color:var(--muted)}.kv dd{margin:0}
details summary{cursor:pointer;color:var(--accent)}
footer{max-width:1280px;margin:32px auto 0;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:12px}
@media (prefers-reduced-motion:no-preference){.bars .track i{transition:width .5s ease}}
</style>
<header>
  <div class="eyebrow">reverse-proxies lab · twelve proxies · one contract</div>
  <h1>Reverse Proxy Lab</h1>
  <p class="lede">Every proxy below was configured to the same routes, hosts and ports, then probed 69 ways, load-tested with 14 scenarios on four pinned cores, and shaken: a backend killed under load, a config reload under load.</p>
  <div class="meta" id="meta"></div>
</header>
<nav class="tabs" role="tablist" id="tabs"></nav>
<main>
  <section class="panel active" id="p-overview" role="tabpanel"><h2>Overview</h2><p class="note">Capabilities: ✅ verified · ❌ configured but the probe failed · 💥 probe error · ○ declared unsupported (reason in the per-proxy tab). Throughput: HTTP/1.1 keep-alive, 64 connections, proxy pinned to 4 cores. µs/req = proxy CPU microseconds per request (lower is cheaper).</p><div class="tablewrap"><table id="overview"></table></div></section>
  <section class="panel" id="p-caps" role="tabpanel"><h2>Capability matrix</h2><div class="filters" id="capfilters"></div><div class="legend"><span><i class="dot ok"></i>verified</span><span><i class="dot fail"></i>failed</span><span><i class="dot error"></i>probe error</span><span><i class="dot unsupported"></i>unsupported (hover for the reason)</span></div><div class="tablewrap"><table class="matrix" id="matrix"></table></div></section>
  <section class="panel" id="p-load" role="tabpanel"><h2>Load scenarios</h2><p class="note">Bars are the headline metric of each scenario (requests/s, MB/s, p99 ms or 2xx passed); the right column shows p99 latency and proxy CPU (cores of 4 · µs per request). Scenarios a proxy cannot run (unsupported capability) are listed without a bar.</p><div class="charts" id="charts"></div></section>
  <section class="panel" id="p-chaos" role="tabpanel"><h2>Chaos: failover and reload under load</h2><p class="note">Failover: fortio at 1 000 rps plus a 20 rps probing timeline while backend app2 is stopped at 6 s and started at 14 s. Reload: oha with 64 keep-alive connections for 15 s, the proxy's native reload issued at 5 s.</p><div class="tablewrap"><table id="chaos"></table></div></section>
  <section class="panel" id="p-proxy" role="tabpanel"><h2>Per proxy</h2><p><label for="pick">Proxy </label><select id="pick"></select></p><div id="proxy"></div></section>
</main>
<footer>Generated <span id="gen"></span> by <code>scripts/build-report.py</code> from <code>results/&lt;stack&gt;/latest.json</code>. Numbers come from one 28-core host (proxy cpus 0-3, backends 4-9/18-23, load generator 10-13/24-27) and are comparable across proxies, not absolute.</footer>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const KEYS = Object.keys(D.stacks).sort((a,b)=>D.stacks[a].display.localeCompare(D.stacks[b].display));
const S = D.stacks;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = (v, d=0) => (v==null || isNaN(v)) ? '–' : Number(v).toLocaleString('en-US',{maximumFractionDigits:d, minimumFractionDigits:d});
const ms = v => v==null ? '–' : (v < 10 ? v.toFixed(2) : v < 100 ? v.toFixed(1) : fmt(v));
const ICON = {ok:'✅', fail:'❌', error:'💥', unsupported:'○'};

document.getElementById('gen').textContent = D.generated;
document.getElementById('meta').innerHTML = [
  `<span><b>${KEYS.length}</b> proxies</span>`, `<span><b>${D.probes.length}</b> capability probes</span>`,
  `<span><b>${D.scenarios.length}</b> load scenarios</span>`, `<span>run window <b>${esc((KEYS.map(k=>S[k].started).filter(Boolean).sort()[0]||'').slice(0,16))}</b> → <b>${esc((KEYS.map(k=>S[k].finished).filter(Boolean).sort().pop()||'').slice(0,16))}</b> UTC</span>`
].join('');

// ---- tabs
const TABS = [['p-overview','Overview'],['p-caps','Capabilities'],['p-load','Load'],['p-chaos','Chaos'],['p-proxy','Per proxy']];
const tabs = document.getElementById('tabs');
TABS.forEach(([id,label],i)=>{const b=document.createElement('button');b.role='tab';b.textContent=label;b.setAttribute('aria-selected',i===0);b.onclick=()=>{document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===id));tabs.querySelectorAll('button').forEach(x=>x.setAttribute('aria-selected',x===b));try{location.hash=id}catch(e){}};tabs.appendChild(b);});
if(location.hash){const b=[...tabs.children].find((x,i)=>TABS[i][0]===location.hash.slice(1));if(b)b.click();}

// ---- overview
function sc(k,id){return (S[k].load||{})[id];}
function pillsum(k){const s=S[k].summary||{};const tot=(s.ok||0)+(s.fail||0)+(s.error||0)+(s.unsupported||0)||1;
  return `<div class="stack" title="✅ ${s.ok||0} · ❌ ${s.fail||0} · 💥 ${s.error||0} · ○ ${s.unsupported||0}"><i class="ok" style="width:${100*(s.ok||0)/tot}%"></i><i class="fail" style="width:${100*(s.fail||0)/tot}%"></i><i class="err" style="width:${100*(s.error||0)/tot}%"></i></div><span class="mono" style="font-size:12px;color:var(--muted)">${s.ok||0}✅ ${s.fail||0}❌ ${s.unsupported||0}○</span>`;}
{
  const rows = KEYS.map(k=>{const r=S[k], h1=sc(k,'h1_keepalive'), h2=sc(k,'tls_h2'), h3=sc(k,'h3'), ws=sc(k,'ws_echo'), f=(r.chaos||{}).failover||{}, rl=(r.chaos||{}).reload||{};
    const fl=f.load||{}, rlo=rl.load||{}, ft=f.timeline||{}, rt=rl.timeline||{};
    return `<tr><td><b>${esc(r.display)}</b><br><span class="note mono">${esc((r.version||'').replace(/^[a-z ]*version[: ]*/i,'').slice(0,40))}</span></td>
      <td>${esc(r.category||'')}</td><td>${pillsum(k)}</td>
      <td class="num">${h1&&h1.status==='ok'?`<b>${fmt(h1.rps)}</b>`:'–'}</td><td class="num">${h1&&h1.status==='ok'?fmt(h1.us_req,0):'–'}</td>
      <td class="num">${h2&&h2.status==='ok'?fmt(h2.rps):'–'}</td><td class="num">${h3&&h3.status==='ok'?fmt(h3.rps):'–'}</td><td class="num">${ws&&ws.status==='ok'?fmt(ws.rps):'–'}</td>
      <td class="num">${f.status?`${fmt(fl.errors)} / ${fmt(ft.failed)}`:'–'}</td><td class="num">${rl.status?`${fmt(rlo.errors)} / ${fmt(rt.failed)}`:'–'}</td>
      <td class="num">${esc(r.image_size||'–')}</td><td class="num">${r.startup_s??'–'}</td></tr>`;}).join('');
  document.getElementById('overview').innerHTML = `<thead><tr><th>proxy</th><th>what it is</th><th>capabilities</th><th class="num">h1 rps</th><th class="num">µs/req</th><th class="num">TLS h2 rps</th><th class="num">h3 rps</th><th class="num">WS msg/s</th><th class="num">failover errors<br>load / timeline</th><th class="num">reload errors<br>load / timeline</th><th class="num">image</th><th class="num">start s</th></tr></thead><tbody>${rows}</tbody>`;
}

// ---- capability matrix
{
  const filt=document.getElementById('capfilters'); let active='all';
  const mk=(id,label)=>{const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-pressed',id===active);b.onclick=()=>{active=id;[...filt.children].forEach(x=>x.setAttribute('aria-pressed',x===b));render();};filt.appendChild(b);};
  mk('all','all groups'); D.groups.forEach(g=>mk(g,g));
  function render(){
    const head=`<thead><tr><th>group</th><th>capability</th>${KEYS.map(k=>`<th class="rot">${esc(S[k].display)}</th>`).join('')}</tr></thead>`;
    let body='';
    for(const g of D.groups){ if(active!=='all'&&active!==g) continue;
      const ps=D.probes.filter(p=>p.group===g);
      body+=`<tr class="group"><td colspan="${KEYS.length+2}">${esc(g)} · ${ps.length} probes</td></tr>`;
      for(const p of ps){ body+=`<tr><td class="g">${esc(g)}</td><td><b>${esc(p.title)}</b><br><span class="note mono">${esc(p.id)}</span><br><span class="note">${esc(p.proves)}</span></td>`;
        for(const k of KEYS){const c=(S[k].caps||{})[p.id]; if(!c){body+='<td class="c"><span class="dot none"></span></td>';continue;}
          const reason=c.s==='unsupported'?(S[k].unsupported[p.id]||c.d):c.d; body+=`<td class="c" title="${esc(S[k].display)} · ${c.s}: ${esc(reason)}"><span class="dot ${c.s}"></span></td>`;}
        body+='</tr>';}
    }
    document.getElementById('matrix').innerHTML=head+'<tbody>'+body+'</tbody>';
  }
  render();
}

// ---- load charts
{
  const wrap=document.getElementById('charts');
  for(const s of D.scenarios){
    const rows=KEYS.map(k=>({k, r:sc(k,s.id)}));
    const ok=rows.filter(x=>x.r&&x.r.status==='ok');
    const val=x=>s.metric==='bytes_per_s'?x.r.bytes_per_s/1048576:s.metric==='p99'?x.r.p99:s.metric==='status'?Math.max(0,(x.r.requests||0)-(x.r.non2xx||0)-(x.r.errors||0)):x.r.rps;
    const unit=s.metric==='bytes_per_s'?'MB/s':s.metric==='p99'?'ms p99':s.metric==='status'?'2xx passed':'req/s';
    const lower=s.metric==='p99';
    ok.sort((a,b)=>lower?val(a)-val(b):val(b)-val(a));
    const max=Math.max(...ok.map(val),1e-9);
    const div=document.createElement('div');div.className='card chart';
    let html=`<h3>${esc(s.title)}</h3><p class="sub"><span class="mono">${esc(s.id)}</span> · ${esc(s.tool)} · ${unit}${lower?' (lower is better)':''}</p><div class="bars">`;
    ok.forEach((x,i)=>{const v=val(x), w=(lower?(Math.min(...ok.map(val))/v):(v/max))*100;
      const cpu=x.r.cores!=null?`${x.r.cores.toFixed(2)} cores · ${fmt(x.r.us_req)} µs/req`:'';
      const bad=(x.r.errors||0)>0&&s.metric!=='status';
      html+=`<span class="lab ${i===0?'win':''}">${esc(S[x.k].display)}</span><span class="track"><i class="${i===0?'win':''}" style="width:${w.toFixed(1)}%"></i></span><span class="val ${bad?'bad':''}"><b>${fmt(v, s.metric==='bytes_per_s'||s.metric==='p99'?1:0)}</b> ${unit} · p99 ${ms(x.r.p99)} ms${cpu?' · '+cpu:''}${bad?' · '+fmt(x.r.errors)+' errors':''}${s.metric==='status'?' of '+fmt(x.r.requests):''}</span>`;});
    const rest=rows.filter(x=>!(x.r&&x.r.status==='ok'));
    html+='</div>';
    if(rest.length) html+=`<p class="note" style="margin:10px 0 0">Not run: ${rest.map(x=>`${esc(S[x.k].display)} (${esc(x.r?x.r.status+': '+x.r.detail:'no result')})`).join(' · ')}</p>`;
    div.innerHTML=html; wrap.appendChild(div);
  }
}

// ---- chaos
{
  const rows=KEYS.map(k=>{const c=S[k].chaos||{}; const f=c.failover||{}, rl=c.reload||{}; const fl=f.load||{}, ft=f.timeline||{}, rlo=rl.load||{}, rt=rl.timeline||{};
    if(!f.status&&!rl.status) return '';
    return `<tr><td><b>${esc(S[k].display)}</b></td><td class="num">${fmt(fl.errors)} / ${fmt(fl.requests)}</td><td class="num">${fmt(ft.failed)} / ${fmt(ft.requests)}</td><td class="num">${ft.fail_window_s??'–'}</td><td class="num">${f.back_after??'–'}</td><td class="num">${ms(fl.max)}</td>
      <td>${esc(S[k].reload_kind||'')}</td><td class="num">${fmt(rlo.errors)} / ${fmt(rlo.requests)}</td><td class="num">${fmt(rt.failed)} / ${fmt(rt.requests)}</td><td class="num">${rl.seconds??'–'}</td><td class="note">${esc(Object.entries((rlo.error_samples||{})).map(([e,n])=>`${e} ×${n}`).join('; '))}</td></tr>`;}).join('');
  document.getElementById('chaos').innerHTML=`<thead><tr><th>proxy</th><th class="num">failover: load errors / requests</th><th class="num">timeline failed / requests</th><th class="num">fail window s</th><th class="num">app2 back after s</th><th class="num">max latency ms</th><th>reload mechanism</th><th class="num">reload: load errors / requests</th><th class="num">timeline failed / requests</th><th class="num">reload s</th><th>error samples</th></tr></thead><tbody>${rows}</tbody>`;
}

// ---- per proxy
{
  const pick=document.getElementById('pick'); KEYS.forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=S[k].display;pick.appendChild(o);});
  const out=document.getElementById('proxy');
  function render(){const k=pick.value, r=S[k];
    const caps=D.probes.filter(p=>r.caps[p.id]).map(p=>{const c=r.caps[p.id];const reason=c.s==='unsupported'?(r.unsupported[p.id]||c.d):c.d;return `<tr><td class="g note">${esc(p.group)}</td><td>${esc(p.title)}<br><span class="note mono">${esc(p.id)}</span></td><td class="c">${ICON[c.s]||'?'}</td><td class="note">${esc(reason)}</td></tr>`;}).join('');
    const loads=D.scenarios.map(s=>{const x=r.load[s.id]; if(!x) return ''; return `<tr><td>${esc(s.title)}</td><td><span class="pill ${x.status==='ok'?'ok':'na'}">${esc(x.status)}</span></td><td class="num">${fmt(x.rps)}</td><td class="num">${ms(x.p50)}</td><td class="num">${ms(x.p99)}</td><td class="num">${ms(x.max)}</td><td class="num" title="${esc(Object.entries(x.codes||{}).map(([c,n])=>c+': '+n).join(', '))}${Object.keys(x.error_samples||{}).length?' · '+esc(Object.entries(x.error_samples).map(([e,n])=>e+' ×'+n).join(', ')):''}">${fmt(x.errors)}/${fmt(x.non2xx)}</td><td class="num">${x.cores!=null?x.cores.toFixed(2):'–'}</td><td class="num">${fmt(x.us_req)}</td><td class="num">${x.mem_end!=null?fmt(x.mem_end):'–'}</td><td class="num">${x.backend_cores!=null?x.backend_cores.toFixed(1):'–'} / ${x.loadgen_cores!=null?x.loadgen_cores.toFixed(1):'–'}</td></tr>`;}).join('');
    out.innerHTML=`<div class="grid"><div class="card"><h3>${esc(r.display)}</h3><dl class="kv"><dt>image</dt><dd class="mono">${esc(r.image)}${r.image_size?' · '+esc(r.image_size):''}</dd><dt>version</dt><dd class="mono">${esc(r.version||'')}</dd><dt>family</dt><dd>${esc(r.family)} — ${esc(r.category||'')}</dd><dt>reload</dt><dd>${esc(r.reload_kind||'')}</dd><dt>docs</dt><dd>${(r.docs||[]).map(u=>`<a href="${esc(u)}">${esc(u.replace(/^https?:\/\//,''))}</a>`).join('<br>')}</dd></dl><p style="margin:12px 0 0">${esc(r.notes||'')}</p></div>
      <div class="card"><h3>Capabilities (${Object.keys(r.caps).length})</h3><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>group</th><th>capability</th><th>result</th><th>detail / reason</th></tr></thead><tbody>${caps}</tbody></table></div></div>
      <div class="card"><h3>Load</h3><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>scenario</th><th>status</th><th class="num">rps</th><th class="num">p50 ms</th><th class="num">p99 ms</th><th class="num">max ms</th><th class="num">errors / non-2xx</th><th class="num">proxy cores</th><th class="num">µs/req</th><th class="num">mem MB</th><th class="num">backend / loadgen cores</th></tr></thead><tbody>${loads}</tbody></table></div></div></div>`;}
  pick.onchange=render; render();
}
</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "report.html"))
    a = ap.parse_args()
    res = load_all()
    if not res:
        sys.exit("no results under results/")
    data = compact(res)
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(HTML.replace("__DATA__", blob), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB, {len(data['stacks'])} stacks)")


if __name__ == "__main__":
    main()
