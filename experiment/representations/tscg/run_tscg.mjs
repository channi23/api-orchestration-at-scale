// Official TSCG (@tscg/core, pinned in package.json/package-lock.json) applied per tool.
// Input: JSON file [{tool_id, tool:{type:'function',function:{name,description,parameters}}}]
// Output (stdout): JSON {version, options, tools:[{tool_id, compressed, compress_ms_median, applied,
//                   tscg_metrics, sdm_tool:{...}}]}
import { compress, compressDescriptions } from '@tscg/core';
import fs from 'fs';
const version = JSON.parse(fs.readFileSync(new URL('./node_modules/@tscg/core/package.json', import.meta.url), 'utf8')).version;
const OPTIONS = { model: 'qwen-3', profile: 'conservative' };
const REPS = 15;
const items = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = [];
for (const it of items) {
  let res, times = [];
  for (let i = 0; i < REPS; i++) {
    const t0 = process.hrtime.bigint();
    res = compress([it.tool], OPTIONS);
    times.push(Number(process.hrtime.bigint() - t0) / 1e6);
  }
  times.sort((a, b) => a - b);
  const sdm = compressDescriptions([it.tool], OPTIONS).tools[0];
  out.push({ tool_id: it.tool_id, compressed: res.compressed, compress_ms_median: times[Math.floor(REPS / 2)],
             applied: res.appliedPrinciples, tscg_metrics: res.metrics.tokens, sdm_tool: sdm });
}
// Optional: whole-catalog compilation (presentation order) to verify per-tool equivalence and time it.
const catalogs = [];
if (process.argv[3]) {
  const byId = Object.fromEntries(items.map(it => [it.tool_id, it.tool]));
  const cats = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  for (const c of cats) {
    const tools = c.order.map(id => byId[id]);
    let res, times = [];
    for (let i = 0; i < REPS; i++) {
      const t0 = process.hrtime.bigint();
      res = compress(tools, OPTIONS);
      times.push(Number(process.hrtime.bigint() - t0) / 1e6);
    }
    times.sort((a, b) => a - b);
    catalogs.push({ catalog_id: c.catalog_id, compressed: res.compressed, compress_ms_median: times[Math.floor(REPS / 2)],
                    applied: res.appliedPrinciples });
  }
}
process.stdout.write(JSON.stringify({ version, options: OPTIONS, reps_for_timing: REPS, node: process.version, tools: out, catalogs }));
