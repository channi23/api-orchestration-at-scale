"""Experiment pipeline diagram (SVG). All counts resolved from frozen artifacts via provenance keys.
usage: python src/make_diagram.py analysis/<run_id>   -> analysis/<run_id>/figures/experiment_diagram.svg
"""
from __future__ import annotations

import os
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from provenance import Prov  # noqa: E402

W, H = 1260, 580


def box(x, y, w, h, title, lines, cls="step"):
    s = [f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>',
         f'<text class="t" x="{x + 14}" y="{y + 26}">{escape(title)}</text>']
    for i, ln in enumerate(lines):
        s.append(f'<text class="l" x="{x + 14}" y="{y + 50 + 19 * i}">{escape(ln)}</text>')
    s.append("</g>")
    return "\n".join(s)


def arrow(x1, y1, x2, y2):
    return f'<line class="a" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" marker-end="url(#ah)"/>'


def build(P: Prov) -> str:
    f = P.fmt
    y0, bh, bw, gap = 200, 180, 180, 26
    xs = [20 + i * (bw + gap) for i in range(6)]
    steps = [
        ("1  Catalogs", [f"{f('meta.n_schemas')} real schemas", f"→ {f('meta.n_eligible')} eligible", f"→ {f('meta.n_tools')}-tool pool",
                                     f"{f('meta.n_catalogs')} nested catalogs", f"({f('meta.n_replicates')} replicates)"]),
        ("2  Representation", ["Raw JSON", "Raw-minified JSON", "Normalized JSON", "TSCG (official)", "TSCG-info JSON"]),
        ("3  Model (fixed)", ["Qwen3-1.7B Q8_0", "llama.cpp, CPU", "greedy, seed 0", "thinking off", "same prompt text"]),
        ("4  Tool call", ["select one tool", "generate arguments", "JSON output", f"{f('meta.n_tasks')} tasks", f"({f('meta.n_intents')} intents × 2)"]),
        ("5  Validate + mock", ["parse JSON", "validate against", "  the RAW schema", "deterministic mock", "receipt check"]),
        ("6  Metrics", ["E2E success (primary)", "selection, arg EM,", "field acc, validity", "tokens, latency", "failure taxonomy"]),
    ]
    parts = []
    for i, (t, ls) in enumerate(steps):
        parts.append(box(xs[i], y0, bw, bh, t, ls, "step iv" if i == 1 else ("step out" if i == 5 else "step")))
        if i < 5:
            parts.append(arrow(xs[i] + bw + 2, y0 + bh / 2, xs[i + 1] - 4, y0 + bh / 2))
    parts.append(box(xs[1] - 10, 30, bw + 2 * (bw + gap) - 10, 130, "Independent variable",
                     ["Schema representation: 5 conditions", "Design factor: catalog size 5 / 10 / 20 / 50 / 100",
                      "Every task is paired across all conditions and sizes"], "iv"))
    parts.append(arrow(xs[1] + bw / 2, 160, xs[1] + bw / 2, y0 - 4))
    parts.append(box(xs[4] - 10, 30, bw * 2 + gap + 10, 130, "Primary outcome",
                     ["End-to-end task success:", "valid JSON ∧ correct tool ∧ schema-valid", "∧ correct arguments ∧ mock receipt match"], "out"))
    parts.append(arrow(xs[5] + bw / 2, 160, xs[5] + bw / 2, y0 - 4))
    parts.append(box(20, 410, W - 40, 125, "Held constant across all conditions",
                     ["model + version + quantization · decoding parameters · system-prompt wording · user task · tool names and tool order",
                      "tool catalog membership · evaluator · mock execution · number of trials · task IDs",
                      "Not in this experiment: retrieval, progressive discovery, MCP, planning, extra agents, training, Blaze"], "ctl"))
    css = """
  :root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#c3c2b7;--step:#ffffff;--iv:#eaf2fc;--ivb:#2a78d6;--out:#fdf1e9;--outb:#eb6834}
  @media (prefers-color-scheme: dark){:root{--bg:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;--line:#52514e;--step:#242423;--iv:#1d2b3d;--ivb:#3987e5;--out:#3a2418;--outb:#d95926}}
  svg{background:var(--bg)} rect{fill:var(--step);stroke:var(--line);stroke-width:1.5}
  .iv rect{fill:var(--iv);stroke:var(--ivb);stroke-width:2} .out rect{fill:var(--out);stroke:var(--outb);stroke-width:2}
  .ctl rect{fill:none;stroke-dasharray:6 4}
  .t{font:600 15px system-ui,sans-serif;fill:var(--ink)} .l{font:13px system-ui,sans-serif;fill:var(--ink2)}
  .a{stroke:var(--ink2);stroke-width:2} #ah path{fill:var(--ink2)}
  .prov{font:11px ui-monospace,monospace;fill:var(--ink2)}"""
    prov = f"Counts resolved from frozen artifacts (src/provenance.py; meta.*). Analysis: {os.path.relpath(P.res_path, os.path.dirname(P.analysis_dir))} sha256 {P.res_sha[:12]}…"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Experiment pipeline diagram">
<title>Representation experiment v1: pipeline, independent variable and primary outcome</title>
<style>{css}</style>
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>
{chr(10).join(parts)}
<text class="prov" x="20" y="{H - 10}">{escape(prov)}</text>
</svg>"""


if __name__ == "__main__":
    ad = sys.argv[1]
    P = Prov(ad)
    os.makedirs(os.path.join(ad, "figures"), exist_ok=True)
    out = os.path.join(ad, "figures", "experiment_diagram.svg")
    open(out, "w").write(build(P))
    print(out)
