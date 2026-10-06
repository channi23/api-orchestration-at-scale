"""Self-contained interactive HTML explainer generated ONLY from validated artifacts.

usage: python src/make_explainer.py --analysis analysis/<run_id> --run runs/<run_id> [--latency-run runs/<lat_id>]
output: analysis/<run_id>/explainer.html  (offline; no external requests)

Every number displayed carries a provenance key (file + JSON path) shown on hover / in tables.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

EXP = su.EXP
ARMS = ["raw", "minified", "normalized", "tscg", "tscg_info"]
LABEL = {"raw": "Raw", "minified": "Raw-minified", "normalized": "Normalized", "tscg": "TSCG", "tscg_info": "TSCG-info JSON"}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def examples(run_dir, tasks, max_per=3):
    """Real model outputs per (arm, size, primary failure) for the failure explorer."""
    ex = collections.defaultdict(list)
    for line in open(os.path.join(run_dir, "results.jsonl")):
        r = json.loads(line)
        f = r["eval"]["failure_primary"]
        if not f or r["family"] != "select":
            continue
        k = f"{r['arm']}|{r['size']}|{f}"
        if len(ex[k]) < max_per:
            t = tasks[r["task_id"]]
            ex[k].append({"request_key": r["request_key"], "task_id": r["task_id"], "tool": t["tool_name"],
                          "prompt": t["prompt"], "gold": t["gold_args"], "output": r["raw_content"][:700],
                          "secondary": r["eval"]["failure_secondary"],
                          "schema_errors": [e["message"][:160] for e in r["eval"]["schema_errors"][:3]]})
    return ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--latency-run")
    a = ap.parse_args()
    res_path = os.path.join(a.analysis, "results.json")
    res = json.load(open(res_path))
    manifest = json.load(open(os.path.join(a.run, "manifest.json")))
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(EXP, "tasks", "tasks.v1.jsonl"))}
    audit = json.load(open(os.path.join(EXP, "representations", "tscg", "information_audit.v1.summary.json")))
    tokm = json.load(open(os.path.join(EXP, "representations", "representation_metrics.v1.json")))
    diag_path = os.path.join(a.analysis, "figures", "experiment_diagram.svg")
    diagram = open(diag_path).read() if os.path.exists(diag_path) else ""
    rel = lambda p: os.path.relpath(p, EXP)  # noqa: E731
    data = {
        "provenance": {"analysis_file": rel(res_path), "analysis_sha256": sha(res_path),
                       "run_id": res["run_id"], "run_results": rel(os.path.join(a.run, "results.jsonl")),
                       "run_results_sha256": sha(os.path.join(a.run, "results.jsonl")),
                       "git_commit_at_run": manifest.get("git_commit"),
                       "latency_run": rel(a.latency_run) if a.latency_run else None,
                       "audit_file": "representations/tscg/information_audit.v1.summary.json",
                       "token_file": "representations/representation_metrics.v1.json",
                       "generated_utc": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")},
        "arms": ARMS, "labels": LABEL, "res": res, "audit": audit, "tokens": tokm,
        "examples": examples(a.run, tasks),
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(data, default=float).replace("</", "<\\/")).replace("__DIAGRAM__", diagram)
    out = os.path.join(a.analysis, "explainer.html")
    open(out, "w").write(html)
    print(out, f"{len(html) / 1024:.0f} KB")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Schema Representation Experiment</title>
<style>
:root{--bg:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--ink3:#7a7974;--line:#e6e5e0;--accent:#2a78d6;--warn:#b54708;--warnbg:#fdf1e9;
--s-raw:#2a78d6;--s-minified:#eb6834;--s-normalized:#1baf7a;--s-tscg:#eda100;--s-tscg_info:#e87ba4}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#1a1a19;--panel:#242423;--ink:#ffffff;--ink2:#c3c2b7;--ink3:#9a998f;--line:#3a3a38;--accent:#3987e5;--warn:#f0a35e;--warnbg:#3a2418;
--s-raw:#3987e5;--s-minified:#d95926;--s-normalized:#199e70;--s-tscg:#c98500;--s-tscg_info:#d55181}}
:root[data-theme="dark"]{--bg:#1a1a19;--panel:#242423;--ink:#ffffff;--ink2:#c3c2b7;--ink3:#9a998f;--line:#3a3a38;--accent:#3987e5;--warn:#f0a35e;--warnbg:#3a2418;
--s-raw:#3987e5;--s-minified:#d95926;--s-normalized:#199e70;--s-tscg:#c98500;--s-tscg_info:#d55181}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 6px} h2{font-size:19px;margin:36px 0 10px;padding-top:8px;border-top:1px solid var(--line)} h3{font-size:15px;margin:18px 0 6px}
p{margin:6px 0 10px;color:var(--ink)} .muted{color:var(--ink2)} .small{font-size:12.5px} code,.mono{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.badge{display:inline-block;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--ink2)}
.warn{background:var(--warnbg);border-color:var(--warn);color:var(--ink)} .warn b{color:var(--warn)}
.controls{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;margin:8px 0}
.controls label{display:inline-flex;gap:6px;align-items:center;cursor:pointer;font-size:13.5px}
select,button{font:inherit;font-size:13.5px;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px}
.tablewrap{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:13px} th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap} #cmptable td:first-child{white-space:normal;min-width:220px}
th{color:var(--ink2);font-weight:600} td:first-child,th:first-child,td.l,th.l{text-align:left} tr.primary td{font-weight:600}
td[data-k]{cursor:help} .ns{color:var(--ink3)} .sig{color:var(--ink);font-weight:600}
svg text{fill:var(--ink2);font-size:11.5px} .gridl{stroke:var(--line)} .axis{stroke:var(--ink3)}
#tip{position:fixed;pointer-events:none;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12.5px;box-shadow:0 4px 18px rgba(0,0,0,.15);display:none;max-width:340px;z-index:9}
.fbar{display:flex;align-items:center;gap:8px;margin:4px 0;cursor:pointer} .fbar .lab{width:230px;font-size:13px} .fbar .bar{height:16px;border-radius:0 4px 4px 0;background:var(--accent)}
.fbar.on .lab{font-weight:700} .ex{border-left:3px solid var(--line);padding:6px 10px;margin:10px 0} pre{white-space:pre-wrap;word-break:break-word;margin:4px 0;font:12px ui-monospace,monospace;color:var(--ink2)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px} .diagram svg{width:100%;height:auto}
.kpi{font-size:30px;font-weight:700} .theme{float:right}
</style></head>
<body><main>
<button class="theme" id="theme" aria-label="Toggle light/dark">◐ theme</button>
<h1>Does schema representation change tool use?</h1>
<p class="muted">Controlled experiment: one model, one task set, one tool catalog. Only the tool-schema representation changes.</p>
<div class="panel small" id="prov"></div>
<div class="panel warn small"><b>Read this first.</b> This page is an explanatory view. The authoritative results are the repository report
(<code>RESULTS.md</code>, <code>REPORT.md</code>) and <code>results.json</code>. Hover any number to see where it comes from. The benchmark uses
<b>real JSON schemas</b> with <b>generated tasks and mock execution</b>; it is not a real API workload. One compact model was tested; results may not transfer to other models.</div>

<h2>1. The experiment</h2>
<div class="diagram panel">__DIAGRAM__</div>
<div class="grid2" id="repr"></div>

<h2>2. Primary result</h2>
<div class="panel" id="primary"></div>

<h2>3. Compare representations across catalog sizes</h2>
<div class="controls"><label>Metric <select id="metric"></select></label><span id="armtoggles" class="controls"></span></div>
<div class="panel"><svg id="chart" viewBox="0 0 760 360" width="100%" role="img" aria-label="Metric by catalog size"></svg>
<p class="small muted" id="chartnote"></p></div>
<div class="tablewrap panel"><table id="maintable"></table></div>

<h2>4. Paired statistical comparisons</h2>
<p class="small muted">Each comparison pairs the same task in the same catalog. Test: exact McNemar on discordant pairs. CI: cluster bootstrap over catalog replicates.
Secondary comparisons are Holm-adjusted; ★ = pre-registered primary (unadjusted). sig. = significant, n.s. = not significant. "Not significant" means the data cannot distinguish the two conditions at α = 0.05; it does not show they are equal.</p>
<div class="controls"><label>Show <select id="cmpfilter"><option value="all">all</option><option value="pooled">pooled</option><option value="size">by catalog size</option><option value="stratum">by schema stratum</option><option value="arggen">argument generation (tool fixed)</option></select></label></div>
<div class="tablewrap panel"><table id="cmptable"></table></div>

<h2>5. Failure modes</h2>
<p class="small muted">Primary failure category per failed request (selection family). Click a category to see real model outputs.</p>
<div class="controls"><label>Representation <select id="farm"></select></label><label>Catalog size <select id="fsize"></select></label></div>
<div class="panel"><div id="fbars"></div><div id="fex"></div></div>

<h2>6. Argument generation with the tool fixed</h2>
<div class="tablewrap panel"><table id="argtable"></table></div>

<h2>7. What TSCG changes in a schema</h2>
<p class="small muted">From the per-tool information audit of the official TSCG output (conservative profile) against the raw schema. Counts are tools out of the pool.</p>
<div class="tablewrap panel"><table id="audittable"></table></div>

<h2>8. Token cost (model tokenizer)</h2>
<p class="small muted">tok/tool = mean tokens per tool; compr. = median per-tool compression vs Raw; transform ms = median transformation time per tool; @k = mean system-prompt tokens for a k-tool catalog.</p>
<div class="tablewrap panel"><table id="toktable"></table></div>

<h2>9. Latency — secondary / exploratory</h2>
<div class="panel warn small" id="latwarn"></div>
<div class="tablewrap panel"><table id="lattable"></table></div>

<h2>10. Limits of this experiment</h2>
<div class="panel" id="limits"><ul>
<li>One model (Qwen3-1.7B, Q8_0) and one tokenizer. No claim transfers to other models without new runs.</li>
<li>Tasks and mock APIs are generated. Schemas are real. The benchmark is not a real API workload.</li>
<li>Tool names and descriptions were written by the experimenter. They are identical in every condition.</li>
<li>TSCG removes information from structured schemas. The TSCG-info control separates information loss from format, but only for the information TSCG keeps.</li>
<li>Single-call tasks. E2E reduces to valid JSON ∧ correct tool ∧ schema-valid ∧ correct arguments. Multi-step orchestration is not tested.</li>
<li>Two paraphrases share one gold answer, so tasks are not fully independent. CIs resample whole replicates.</li>
<li>Prompt caching made the main run feasible on CPU. Cached and uncached outputs agreed in 48/50 requests (50/50 same E2E outcome) in the pilot check.</li>
</ul></div>
<p class="small muted">Generated by <code>src/make_explainer.py</code> from validated artifacts only. Colors: categorical palette validated for colour-vision deficiency; each representation also has a distinct marker shape.</p>
</main><div id="tip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent), R=D.res, A=D.arms, L=D.labels;
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const col=a=>css('--s-'+a); const SH={raw:'circle',minified:'square',normalized:'triangle',tscg:'diamond',tscg_info:'tri-down'};
const pct=v=>v==null?'—':(100*v).toFixed(1)+'%'; const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P=D.provenance; const AF=P.analysis_file;
document.getElementById('prov').innerHTML=`<b>Provenance</b> · run <code>${esc(P.run_id)}</code> · results <code>${esc(P.run_results)}</code> (sha256 <code>${P.run_results_sha256.slice(0,12)}…</code>)
 · analysis <code>${esc(AF)}</code> (sha256 <code>${P.analysis_sha256.slice(0,12)}…</code>) · code at run <code>${esc((P.git_commit_at_run||'').slice(0,10))}</code> · generated ${esc(P.generated_utc)}`;
// tooltip
const tip=document.getElementById('tip');
function showTip(e,html){tip.innerHTML=html;tip.style.display='block';const x=Math.min(e.clientX+14,innerWidth-360);tip.style.left=x+'px';tip.style.top=(e.clientY+14)+'px'}
document.addEventListener('mouseover',e=>{const t=e.target.closest('[data-k]');if(t&&!t.closest('svg'))showTip(e,`<span class="mono">${esc(t.dataset.k)}</span>`)});
document.addEventListener('mouseout',e=>{if(e.target.closest('[data-k]'))tip.style.display='none'});
// theme
document.getElementById('theme').onclick=()=>{const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;r.dataset.theme=dark?'light':'dark';draw()};
// representations
const REPR={raw:'Original schema, pretty JSON.',minified:'Same content, compact JSON (fewer tokens, same information).',normalized:'Local $ref inlined; definitions removed.',tscg:'Official TSCG 1.4.3 text (conservative). Keeps only top-level fields.',tscg_info:'JSON with exactly the information TSCG keeps (control).'};
document.getElementById('repr').innerHTML=A.map(a=>`<div class="panel"><span class="sw" style="background:${col(a)}"></span> <b>${L[a]}</b><p class="small muted">${REPR[a]}</p></div>`).join('');
// primary
(()=>{const c=R.paired_comparisons.find(x=>x.primary);if(!c)return;const k=`${AF} › paired_comparisons[name="${c.name}"]`;
 const sig=c.mcnemar_exact_p<0.05;
 document.getElementById('primary').innerHTML=`<p class="muted">Pre-registered primary comparison: end-to-end success, TSCG vs Raw, all catalog sizes pooled (n = ${c.n_pairs} paired requests).</p>
 <div class="grid2"><div><div class="muted small">Raw</div><div class="kpi" data-k="${esc(k)}.acc_a">${pct(c.acc_a)}</div></div>
 <div><div class="muted small">TSCG</div><div class="kpi" data-k="${esc(k)}.acc_b">${pct(c.acc_b)}</div></div>
 <div><div class="muted small">Difference (TSCG − Raw), 95% CI</div><div class="kpi" data-k="${esc(k)}.diff_pp">${c.diff_pp>=0?'+':''}${c.diff_pp.toFixed(1)} pp</div>
 <div class="small" data-k="${esc(k)}.ci95_diff_pp">[${c.ci95_diff_pp.map(v=>v.toFixed(1)).join(', ')}]</div></div>
 <div><div class="muted small">Exact McNemar p</div><div class="kpi" data-k="${esc(k)}.mcnemar_exact_p">${c.mcnemar_exact_p.toPrecision(2)}</div>
 <div class="small">${sig?'Statistically significant at α = 0.05.':'Not statistically significant at α = 0.05.'} Discordant pairs: Raw-only ${c.discordant_a_only}, TSCG-only ${c.discordant_b_only}.</div></div></div>
 <p class="small muted">Observed result only. For causes, see the TSCG-info and Raw-minified controls (section 4) and the report.</p>`})();
// metric chart
const METRICS={e2e:['End-to-end success','e2e_ci95'],e2e_strict:['E2E-strict (no invented values)',null],selection:['Tool-selection accuracy','selection_ci95'],arg_em:['Argument exact match',null],field_acc:['Argument field accuracy',null],schema_valid:['Schema validity',null],json_valid:['JSON validity',null],input_tokens:['Mean input tokens',null]};
const msel=document.getElementById('metric');msel.innerHTML=Object.entries(METRICS).map(([k,v])=>`<option value="${k}">${v[0]}</option>`).join('');
const on=Object.fromEntries(A.map(a=>[a,true]));
document.getElementById('armtoggles').innerHTML=A.map(a=>`<label><input type="checkbox" data-arm="${a}" checked><span class="sw" style="background:${col(a)}"></span>${L[a]}</label>`).join('');
document.querySelectorAll('[data-arm]').forEach(cb=>cb.onchange=()=>{on[cb.dataset.arm]=cb.checked;draw()});msel.onchange=draw;
function marker(a,x,y){const c=col(a),s=6;const st=`fill="${c}" stroke="${css('--panel')}" stroke-width="1.5"`;
 switch(SH[a]){case'square':return`<rect x="${x-s}" y="${y-s}" width="${2*s}" height="${2*s}" ${st}/>`;case'triangle':return`<path d="M${x},${y-s-1}L${x+s+1},${y+s}L${x-s-1},${y+s}Z" ${st}/>`;
 case'diamond':return`<path d="M${x},${y-s-2}L${x+s+2},${y}L${x},${y+s+2}L${x-s-2},${y}Z" ${st}/>`;case'tri-down':return`<path d="M${x},${y+s+1}L${x+s+1},${y-s}L${x-s-1},${y-s}Z" ${st}/>`;default:return`<circle cx="${x}" cy="${y}" r="${s}" ${st}/>`}}
function draw(){const m=msel.value,[name,ci]=METRICS[m],svg=document.getElementById('chart');const T=R.main_table;const sizes=R.sizes;
 const W=760,H=360,l=72,r=20,t=16,b=44;const isTok=m==='input_tokens';
 const xs=s=>l+(Math.log(s)-Math.log(sizes[0]))/(Math.log(sizes[sizes.length-1])-Math.log(sizes[0]))*(W-l-r);
 let ymax=isTok?Math.max(...T.map(x=>x.input_tokens))*1.08:1;const ys=v=>H-b-(v/ymax)*(H-t-b);
 let g='';const ticks=isTok?[0,.25,.5,.75,1].map(f=>f*ymax):[0,.2,.4,.6,.8,1];
 ticks.forEach(v=>{g+=`<line class="gridl" x1="${l}" x2="${W-r}" y1="${ys(v)}" y2="${ys(v)}"/><text x="${l-8}" y="${ys(v)+4}" text-anchor="end">${isTok?Math.round(v).toLocaleString():(100*v).toFixed(0)+'%'}</text>`});
 sizes.forEach(s=>g+=`<text x="${xs(s)}" y="${H-b+18}" text-anchor="middle">${s}</text>`);
 g+=`<text x="${(l+W-r)/2}" y="${H-6}" text-anchor="middle">Tools in catalog (log scale)</text><text transform="translate(14,${(t+H-b)/2}) rotate(-90)" text-anchor="middle">${name}</text>`;
 A.forEach((a,i)=>{if(!on[a])return;const rows=T.filter(x=>x.arm===a);const dx=(i-2)*5;
  const pts=rows.map(x=>[xs(x.tools)+dx,ys(x[m])]);g+=`<polyline fill="none" stroke="${col(a)}" stroke-width="2" points="${pts.map(p=>p.join(',')).join(' ')}"/>`;
  rows.forEach((x,j)=>{if(ci&&x[ci])g+=`<line stroke="${col(a)}" stroke-width="1.4" x1="${pts[j][0]}" x2="${pts[j][0]}" y1="${ys(x[ci][0])}" y2="${ys(x[ci][1])}"/>`;
   const k=`${AF} › main_table[tools=${x.tools},arm=${a}].${m}`;
   g+=`<g class="pt" data-tip='${esc(JSON.stringify({a,t:x.tools,v:x[m],n:x.n,ci:ci?x[ci]:null,k}))}'>${marker(a,pts[j][0],pts[j][1])}<circle cx="${pts[j][0]}" cy="${pts[j][1]}" r="13" fill="transparent"/></g>`})});
 svg.innerHTML=g;svg.querySelectorAll('.pt').forEach(p=>{p.onmousemove=e=>{const d=JSON.parse(p.dataset.tip);showTip(e,`<b>${L[d.a]}</b> · ${d.t} tools<br>${name}: <b>${isTok?Math.round(d.v).toLocaleString():pct(d.v)}</b>${d.ci?` [${pct(d.ci[0])}, ${pct(d.ci[1])}]`:''}<br>n = ${d.n} requests<br><span class="mono small">${esc(d.k)}</span>`)};p.onmouseleave=()=>tip.style.display='none'});
 document.getElementById('chartnote').textContent=ci?'Vertical lines: 95% cluster-bootstrap CI over the '+T[0].n_replicates+' catalog replicates. Points are slightly offset horizontally so they do not overlap.':'No CI is computed for this metric in the analysis; see the table.';
 // table
 const cols=[['selection','Selection'],['arg_em','Arg EM'],['field_acc','Field acc'],['schema_valid','Schema valid'],['e2e','E2E'],['e2e_strict','E2E-strict'],['input_tokens','Input tok'],['output_tokens','Output tok']];
 document.getElementById('maintable').innerHTML=`<tr><th>Tools</th><th class="l">Representation</th><th>n</th>${cols.map(c=>`<th>${c[1]}</th>`).join('')}<th>E2E 95% CI</th></tr>`+
  T.map(x=>`<tr><td>${x.tools}</td><td class="l"><span class="sw" style="background:${col(x.arm)}"></span> ${L[x.arm]}</td><td>${x.n}</td>${cols.map(c=>`<td data-k="${esc(AF)} › main_table[tools=${x.tools},arm=${x.arm}].${c[0]}">${c[0].includes('tokens')?Math.round(x[c[0]]).toLocaleString():pct(x[c[0]])}</td>`).join('')}<td data-k="${esc(AF)} › main_table[tools=${x.tools},arm=${x.arm}].e2e_ci95">[${pct(x.e2e_ci95[0])}, ${pct(x.e2e_ci95[1])}]</td></tr>`).join('')}
// comparisons
function cmpRows(){const f=document.getElementById('cmpfilter').value;return R.paired_comparisons.filter(c=>f==='all'||(f==='pooled'&&/pooled/.test(c.name))||(f==='size'&&/size \d+/.test(c.name))||(f==='stratum'&&/targets/.test(c.name))||(f==='arggen'&&/^ARGGEN/.test(c.name)))}
function drawCmp(){document.getElementById('cmptable').innerHTML=`<tr><th class="l">Comparison</th><th>n pairs</th><th>A</th><th>B</th><th>Δ (B−A)</th><th>95% CI</th><th>A-only / B-only</th><th>p exact</th><th>p Holm</th><th class="l">α=0.05</th></tr>`+
 cmpRows().map(c=>{const k=`${AF} › paired_comparisons[name="${c.name}"]`;const p=c.primary?c.mcnemar_exact_p:c.holm_p;const s=p<0.05;
 return `<tr class="${c.primary?'primary':''}"><td class="l">${esc(c.name)}<div class="small muted">A = ${L[c.a]}, B = ${L[c.b]}</div></td><td>${c.n_pairs}</td><td data-k="${esc(k)}.acc_a">${pct(c.acc_a)}</td><td data-k="${esc(k)}.acc_b">${pct(c.acc_b)}</td>
 <td data-k="${esc(k)}.diff_pp">${c.diff_pp>=0?'+':''}${c.diff_pp.toFixed(1)} pp</td><td data-k="${esc(k)}.ci95_diff_pp">[${c.ci95_diff_pp.map(v=>v.toFixed(1)).join(', ')}]</td><td>${c.discordant_a_only} / ${c.discordant_b_only}</td>
 <td data-k="${esc(k)}.mcnemar_exact_p">${c.mcnemar_exact_p.toPrecision(2)}</td><td data-k="${esc(k)}.holm_p">${c.holm_p.toPrecision(2)}</td><td class="l ${s?'sig':'ns'}">${s?'sig.':'n.s.'}${c.primary?' ★':''}</td></tr>`}).join('')}
document.getElementById('cmpfilter').onchange=drawCmp;
// failures
const FS=['wrong tool','multiple-tool confusion','correct tool, wrong argument','missing required argument','invalid argument type','invalid enum/value','hallucinated field','ignored schema constraint','context-length failure','malformed output','execution failure','semantic/task failure','other'];
const fa=document.getElementById('farm'),fz=document.getElementById('fsize');fa.innerHTML=A.map(a=>`<option value="${a}">${L[a]}</option>`).join('');fz.innerHTML=`<option value="all">all sizes</option>`+R.sizes.map(s=>`<option>${s}</option>`).join('');
let fcat=null;
function drawFail(){const a=fa.value,s=fz.value,key=`${a}|${s}`,c=R.failures_primary[key]||{};const n=R.main_table.filter(x=>x.arm===a&&(s==='all'||x.tools==s)).reduce((t,x)=>t+x.n,0);
 const mx=Math.max(1,...FS.map(f=>c[f]||0));
 document.getElementById('fbars').innerHTML=`<p class="small muted">${n} requests in this view · failed: ${FS.reduce((t,f)=>t+(c[f]||0),0)}</p>`+FS.filter(f=>c[f]).map(f=>`<div class="fbar ${f===fcat?'on':''}" data-f="${esc(f)}" data-k="${esc(AF)} › failures_primary['${key}']['${esc(f)}']"><span class="lab">${esc(f)}</span><span class="bar" style="width:${(c[f]/mx)*420}px;background:${col(a)}"></span><span class="small">${c[f]} (${(100*c[f]/n).toFixed(1)}%)</span></div>`).join('')||'<p class="muted">No failures in this view.</p>';
 document.querySelectorAll('.fbar').forEach(b=>b.onclick=()=>{fcat=b.dataset.f;drawFail()});
 const ex=[];(s==='all'?R.sizes:[+s]).forEach(z=>(D.examples[`${a}|${z}|${fcat}`]||[]).forEach(e=>ex.push(e)));
 document.getElementById('fex').innerHTML=fcat?`<h3>Examples: ${esc(fcat)} (${L[a]})</h3>`+(ex.slice(0,6).map(e=>`<div class="ex"><div class="small"><b>${esc(e.tool)}</b> · <span class="mono">${esc(e.request_key)}</span> (in <code>${esc(P.run_results)}</code>)</div>
 <div class="small">Task: ${esc(e.prompt)}</div><div class="small muted">Gold arguments:</div><pre>${esc(JSON.stringify(e.gold))}</pre><div class="small muted">Model output (raw):</div><pre>${esc(e.output)}</pre>
 ${e.schema_errors.length?`<div class="small muted">Schema errors: ${esc(e.schema_errors.join(' | '))}</div>`:''}${e.secondary.length?`<div class="small muted">Secondary: ${esc(e.secondary.join(', '))}</div>`:''}</div>`).join('')||'<p class="muted">No stored example for this filter.</p>'):'<p class="small muted">Click a category above to see real outputs.</p>'}
fa.onchange=()=>{fcat=null;drawFail()};fz.onchange=drawFail;
// arggen
document.getElementById('argtable').innerHTML=`<tr><th class="l">Representation</th><th>n</th><th>JSON valid</th><th>Arg EM</th><th>Field acc</th><th>Schema valid</th><th>Semantic correct</th><th>E2E</th><th>E2E-strict</th><th>Input tok</th></tr>`+
 R.arggen_table.map(x=>`<tr><td class="l"><span class="sw" style="background:${col(x.arm)}"></span> ${L[x.arm]}</td><td>${x.n}</td>${['json_valid','arg_em','field_acc','schema_valid','semantic_correct','e2e','e2e_strict'].map(c=>`<td data-k="${esc(AF)} › arggen_table[arm=${x.arm}].${c}">${pct(x[c])}</td>`).join('')}<td>${Math.round(x.input_tokens)}</td></tr>`).join('');
// audit
const AU=[['lossless_except_text','Lossless apart from text rewriting'],['with_dropped_substructure','Nested structure dropped'],['with_type_changes','A type shown incorrectly'],['with_lost_enums_behind_ref','Enum lost (behind $ref)'],['with_required_not_in_properties','Required field not shown'],['with_dropped_constraints','Constraints dropped'],['with_dropped_defaults','Defaults dropped'],['with_param_descriptions_rewritten','Parameter descriptions rewritten'],['with_root_description_or_title_dropped','Schema-level description/title dropped']];
document.getElementById('audittable').innerHTML=`<tr><th class="l">Change</th><th>flat tools</th><th>structured tools</th><th>all tools</th></tr>`+AU.map(([k,n])=>`<tr><td class="l">${n}</td>${['flat','structured','all'].map(s=>`<td data-k="${esc(P.audit_file)} › ${s}.${k}">${D.audit[s][k]} / ${D.audit[s].n}</td>`).join('')}</tr>`).join('');
// tokens
document.getElementById('toktable').innerHTML=`<tr><th class="l">Representation</th><th>tok/tool</th><th>compr.</th><th>transform ms</th>${R.sizes.map(s=>`<th>@${s}</th>`).join('')}</tr>`+
 A.map(a=>{const t=D.tokens[a+'/all'];return `<tr><td class="l">${L[a]}</td><td data-k="${esc(P.token_file)} › ${a}/all.mean_tokens">${t.mean_tokens}</td><td data-k="${esc(P.token_file)} › ${a}/all.median_compression_pct">${t.median_compression_pct}%</td><td data-k="${esc(P.token_file)} › ${a}/all.median_transform_ms">${t.median_transform_ms}</td>${R.sizes.map(s=>{const c=D.tokens['catalog/'+s+'/'+a];return `<td data-k="${esc(P.token_file)} › catalog/${s}/${a}.mean">${c?Math.round(c.mean).toLocaleString():'—'}</td>`}).join('')}</tr>`}).join('');
// latency
const LS=R.latency_secondary_exploratory||{};document.getElementById('latwarn').innerHTML=`<b>Secondary / exploratory.</b> ${esc(LS.label||'No latency run analysed.')}`;
document.getElementById('lattable').innerHTML=`<tr><th>Tools</th><th class="l">Representation</th><th>n</th><th class="l">individual observations (ms)</th><th>median (ms)</th><th>median prompt tokens</th></tr>`+(LS.cells||[]).map((c,i)=>`<tr><td>${c.size}</td><td class="l">${L[c.arm]}</td><td>${c.n}</td><td class="l mono" data-k="${esc(AF)} › latency_secondary_exploratory.cells[${i}].observations_ms">${c.observations_ms.join(', ')}</td><td data-k="${esc(AF)} › latency_secondary_exploratory.cells[${i}].median_ms">${Math.round(c.median_ms).toLocaleString()}</td><td>${Math.round(c.median_prompt_tokens).toLocaleString()}</td></tr>`).join('');
draw();drawCmp();drawFail();
</script></body></html>"""

if __name__ == "__main__":
    main()
