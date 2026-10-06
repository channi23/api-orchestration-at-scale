# Summary: does the schema format change tool use?

*Controlled-language summary (about 80% of ASD-STE100 style). The full report (`REPORT.md`) is the authoritative source.*

## Purpose
We tested one question.
Does the format of a tool schema change how well a small model uses tools?

## Method
We used one model: Qwen3-1.7B.
We used real schemas from JSONSchemaBench.
We made {{meta.n_tools}} tools from these schemas.
We wrote {{meta.n_tasks}} tasks for these tools.
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
We ran {{meta.n_requests}} requests in the main run.

We counted a task as a success only when all of these were true:
- The output was valid JSON.
- The model selected the correct tool.
- The arguments obeyed the original schema.
- The requested values were correct.

## Observed results
These are measurements. They are not explanations.

1. With Raw, the model completed {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_a}} of the tasks.
2. With TSCG, the model completed {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_b}} of the tasks.
3. The difference is {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].diff_pp}}. This difference is statistically significant.
4. TSCG was lower than Raw at every number of tools.
5. The model selected the correct tool almost every time in all formats. Raw: {{cmp[name=TSCG vs Raw, tool_correct, pooled].acc_a}}. TSCG: {{cmp[name=TSCG vs Raw, tool_correct, pooled].acc_b}}.
6. With TSCG, the model made more argument errors. For example, it gave the wrong type {{fail[arm=tscg|all].invalid argument type}} times with TSCG and {{fail[arm=raw|all].invalid argument type}} times with Raw.
7. Raw-minified used fewer tokens than Raw. Its success rate ({{cmp[name=Raw-minified vs Raw, E2E, pooled].acc_b}}) did not differ detectably from Raw.
8. Normalized ({{cmp[name=Normalized vs Raw, E2E, pooled].acc_b}}) did not differ detectably from Raw.
9. TSCG-info was lower than Raw by {{cmp[name=TSCG-info JSON vs Raw, E2E, pooled].diff_pp}}.
10. TSCG was lower than TSCG-info by {{cmp[name=TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled].diff_pp}}.
11. For tools with nested structure, the drop was large. Raw: {{cmp[name=TSCG vs Raw, E2E, structured targets].acc_a}}. TSCG: {{cmp[name=TSCG vs Raw, E2E, structured targets].acc_b}}.
12. For flat tools, the drop was smaller. Raw: {{cmp[name=TSCG vs Raw, E2E, flat targets].acc_a}}. TSCG: {{cmp[name=TSCG vs Raw, E2E, flat targets].acc_b}}.
13. More tools gave lower success. With Raw, success went from {{main[size=5,arm=raw].e2e}} with 5 tools to {{main[size=100,arm=raw].e2e}} with 100 tools.
14. The gap between TSCG and Raw did not change detectably as the number of tools increased.

## Interpretation
This section gives our explanation. It is less certain than the results above.

- TSCG removes parts of the schema. Examples are nested fields, some types, and some limits. Our audit found nested structure removed in {{audit[structured].with_dropped_substructure}} of {{audit[structured].n}} nested tools.
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
