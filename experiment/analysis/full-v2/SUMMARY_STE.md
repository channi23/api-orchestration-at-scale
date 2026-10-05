# Summary: does the schema format change tool use?

*Controlled-language summary (about 80% of ASD-STE100 style). The full report (`REPORT.md`) is the authoritative source.*

## Purpose
We tested one question.
Does the format of a tool schema change how well a small model uses tools?

## Method
We used one model: Qwen3-1.7B.
We used real schemas from JSONSchemaBench.
We made 300<sup>[1]</sup> tools from these schemas.
We wrote 100<sup>[2]</sup> tasks for these tools.
Each task asks the model to call one tool with the correct values.

We showed the same tools in five formats:
1. Raw: the original JSON schema.
2. Raw-minified: the same JSON, without spaces.
3. Normalized: the same JSON, with references written out in full.
4. TSCG: a short text format from a published tool.
5. TSCG-info: JSON that holds only the information that TSCG keeps.

We changed only the format.
The model, the tasks, the tools, and the scoring stayed the same.
We also changed the number of tools that the model could choose from: 5, 10, 20, 50, or 100.
We ran 3,000<sup>[3]</sup> requests in the main run.

We counted a task as a success only when all of these were true:
- The output was valid JSON.
- The model selected the correct tool.
- The arguments obeyed the original schema.
- The requested values were correct.

## Observed results
These are measurements. They are not explanations.

1. With Raw, the model completed 82.4%<sup>[4]</sup> of the tasks.
2. With TSCG, the model completed 56.6%<sup>[5]</sup> of the tasks.
3. The difference is -25.8 pp<sup>[6]</sup>. This difference is statistically significant.
4. TSCG was lower than Raw at every number of tools.
5. The model selected the correct tool almost every time in all formats. Raw: 96.2%<sup>[7]</sup>. TSCG: 97.0%<sup>[8]</sup>.
6. With TSCG, the model made more argument errors. For example, it gave the wrong type 71<sup>[9]</sup> times with TSCG and 7<sup>[10]</sup> times with Raw.
7. Raw-minified used fewer tokens than Raw. Its success rate (82.8%<sup>[11]</sup>) did not differ detectably from Raw.
8. Normalized (82.6%<sup>[12]</sup>) did not differ detectably from Raw.
9. TSCG-info was lower than Raw by -20.0 pp<sup>[13]</sup>.
10. TSCG was lower than TSCG-info by -5.8 pp<sup>[14]</sup>.
11. For tools with nested structure, the drop was large. Raw: 76.4%<sup>[15]</sup>. TSCG: 32.8%<sup>[16]</sup>.
12. For flat tools, the drop was smaller. Raw: 88.4%<sup>[17]</sup>. TSCG: 80.4%<sup>[18]</sup>.
13. More tools gave lower success. With Raw, success went from 92.0%<sup>[19]</sup> with 5 tools to 75.0%<sup>[20]</sup> with 100 tools.
14. The gap between TSCG and Raw did not change detectably as the number of tools increased.

## Interpretation
This section gives our explanation. It is less certain than the results above.

- TSCG removes parts of the schema. Examples are nested fields, some types, and some limits. Our audit found nested structure removed in 117<sup>[21]</sup> of 126<sup>[22]</sup> nested tools.
- Without this information, the model cannot build some arguments correctly. This explains most of the drop for nested tools.
- For flat tools, a smaller drop remains. The TSCG text layout itself seems to cause it.
- Fewer tokens alone did not help or hurt. Raw-minified shows this.

## What this result does not show
- It does not show that TSCG is worse for all models. We tested one small model.
- It does not show that TSCG is worse for all schemas. Half of our target tools have nested structure.
- It does not test other TSCG settings.
- It does not test real APIs. The schemas are real. The tasks and the mock execution are generated.
- It does not test tasks with many steps.

## Recommendation
- Do not use TSCG with this model when schemas have nested structure.
- A next experiment with a Blaze-derived format is reasonable only if that format keeps all schema information.
- Compare it with Raw-minified. Raw-minified keeps all information and uses fewer tokens.
- Test a second model before you make a general conclusion.


---
**Provenance.** Every number above is resolved automatically (`src/provenance.py`) from validated artifacts. Analysis file: `analysis/full-v2/results.json` (sha256 `5cb9d5311d61734e…`).

[1] `meta.n_tools`
[2] `meta.n_tasks`
[3] `meta.n_requests`
[4] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_a`
[5] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_b`
[6] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].diff_pp`
[7] `cmp[name=TSCG vs Raw, tool_correct, pooled].acc_a`
[8] `cmp[name=TSCG vs Raw, tool_correct, pooled].acc_b`
[9] `fail[arm=tscg|all].invalid argument type`
[10] `fail[arm=raw|all].invalid argument type`
[11] `cmp[name=Raw-minified vs Raw, E2E, pooled].acc_b`
[12] `cmp[name=Normalized vs Raw, E2E, pooled].acc_b`
[13] `cmp[name=TSCG-info JSON vs Raw, E2E, pooled].diff_pp`
[14] `cmp[name=TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled].diff_pp`
[15] `cmp[name=TSCG vs Raw, E2E, structured targets].acc_a`
[16] `cmp[name=TSCG vs Raw, E2E, structured targets].acc_b`
[17] `cmp[name=TSCG vs Raw, E2E, flat targets].acc_a`
[18] `cmp[name=TSCG vs Raw, E2E, flat targets].acc_b`
[19] `main[size=5,arm=raw].e2e`
[20] `main[size=100,arm=raw].e2e`
[21] `audit[structured].with_dropped_substructure`
[22] `audit[structured].n`
