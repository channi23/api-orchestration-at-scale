# Representation experiment v1 — final report

**Run:** `full-v2` (main, {{meta.n_requests}} requests) + `latency-v2` (secondary/exploratory, 50 requests).
**Authoritative numbers:** `analysis/full-v2/RESULTS.md` and `results.json`. Every number in this report is
resolved from `results.json` (or from the frozen artifacts) by `src/render_text.py`; see the provenance list at the end.

**Label:** compact-model experiment (Qwen3-1.7B, Q8_0, llama.cpp, CPU). This is not an external/frontier-model reproduction.

## 1. What was tested
- One fixed model saw the same {{meta.n_tasks}} tasks ({{meta.n_intents}} intents × 2 paraphrases) under five schema representations: Raw JSON, Raw-minified JSON, Normalized JSON, official TSCG 1.4.3 (`conservative`), and a TSCG-information JSON control.
- The tasks were evaluated in {{meta.n_catalogs}} nested catalogs: {{meta.n_replicates}} replicates × 5 sizes (5, 10, 20, 50, 100 tools).
- Each task is paired across all representations and all sizes.
- The tool pool comes from {{meta.n_schemas}} real JSONSchemaBench schemas, which were audited down to {{meta.n_eligible}} eligible schemas and then {{meta.n_tools}} reviewed tools.
- The tasks and mock execution are generated. The benchmark is therefore real schemas with a generated workload, not a real API workload.
- Primary outcome (pre-registered): **end-to-end (E2E) success** = valid JSON ∧ correct tool ∧ arguments valid against the raw schema ∧ requested values correct ∧ mock receipt matches.

## 2. Main results (observed)

**Primary comparison — TSCG vs Raw, E2E, all sizes pooled ({{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].n_pairs}} paired requests):**
- Raw scored {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_a}} and TSCG {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_b}}.
- Difference: {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].diff_pp}}, 95% CI {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].ci95_diff_pp}} pp.
- Exact McNemar p = {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].mcnemar_exact_p}}.
- Discordant pairs: {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].discordant_a_only}} where only Raw succeeded, {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].discordant_b_only}} where only TSCG succeeded.

E2E by catalog size (Raw / Raw-minified / Normalized / TSCG / TSCG-info):

| tools | Raw | Raw-minified | Normalized | TSCG | TSCG-info |
|---:|---:|---:|---:|---:|---:|
| 5 | {{main[size=5,arm=raw].e2e}} | {{main[size=5,arm=minified].e2e}} | {{main[size=5,arm=normalized].e2e}} | {{main[size=5,arm=tscg].e2e}} | {{main[size=5,arm=tscg_info].e2e}} |
| 10 | {{main[size=10,arm=raw].e2e}} | {{main[size=10,arm=minified].e2e}} | {{main[size=10,arm=normalized].e2e}} | {{main[size=10,arm=tscg].e2e}} | {{main[size=10,arm=tscg_info].e2e}} |
| 20 | {{main[size=20,arm=raw].e2e}} | {{main[size=20,arm=minified].e2e}} | {{main[size=20,arm=normalized].e2e}} | {{main[size=20,arm=tscg].e2e}} | {{main[size=20,arm=tscg_info].e2e}} |
| 50 | {{main[size=50,arm=raw].e2e}} | {{main[size=50,arm=minified].e2e}} | {{main[size=50,arm=normalized].e2e}} | {{main[size=50,arm=tscg].e2e}} | {{main[size=50,arm=tscg_info].e2e}} |
| 100 | {{main[size=100,arm=raw].e2e}} | {{main[size=100,arm=minified].e2e}} | {{main[size=100,arm=normalized].e2e}} | {{main[size=100,arm=tscg].e2e}} | {{main[size=100,arm=tscg_info].e2e}} |

Each cell has n = 100 requests. CIs and all other metrics are in `RESULTS.md`.

## 3. Answers to the ten research questions

**Q1. Does TSCG improve tool selection?**
No improvement was detected.
- Pooled selection accuracy: Raw {{cmp[name=TSCG vs Raw, tool_correct, pooled].acc_a}}, TSCG {{cmp[name=TSCG vs Raw, tool_correct, pooled].acc_b}}.
- Difference: {{cmp[name=TSCG vs Raw, tool_correct, pooled].diff_pp}}, 95% CI {{cmp[name=TSCG vs Raw, tool_correct, pooled].ci95_diff_pp}}, Holm p = {{cmp[name=TSCG vs Raw, tool_correct, pooled].holm_p}}.
- Selection is near ceiling for every representation at every size (lowest cell: {{main[size=100,arm=raw].selection}}).
- The CI excludes large effects but cannot show the two are equal.

**Q2. Does TSCG improve argument generation?**
No. It is worse.
- With the tool fixed (only the gold tool shown): E2E Raw {{arggen[arm=raw].e2e}} vs TSCG {{arggen[arm=tscg].e2e}}. Difference {{cmp[name=ARGGEN: TSCG vs Raw, E2E (tool fixed)].diff_pp}}, Holm p = {{cmp[name=ARGGEN: TSCG vs Raw, E2E (tool fixed)].holm_p}}.
- Field accuracy: Raw {{arggen[arm=raw].field_acc}} vs TSCG {{arggen[arm=tscg].field_acc}}.
- In the full-catalog task, argument exact match is Raw {{cmp[name=TSCG vs Raw, arg_exact_match, pooled].acc_a}} vs TSCG {{cmp[name=TSCG vs Raw, arg_exact_match, pooled].acc_b}} (Holm p = {{cmp[name=TSCG vs Raw, arg_exact_match, pooled].holm_p}}).
- Schema validity is Raw {{cmp[name=TSCG vs Raw, schema_valid, pooled].acc_a}} vs TSCG {{cmp[name=TSCG vs Raw, schema_valid, pooled].acc_b}}.

**Q3. Does TSCG improve end-to-end task success?**
No. It lowers E2E success with this model and benchmark.
- The primary comparison shows {{cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].diff_pp}}.
- The direction is the same at every size: {{cmp[name=TSCG vs Raw, E2E, size 5].diff_pp}} at 5 tools, {{cmp[name=TSCG vs Raw, E2E, size 20].diff_pp}} at 20 and {{cmp[name=TSCG vs Raw, E2E, size 100].diff_pp}} at 100.
- All per-size differences are significant after Holm correction.
- The secondary E2E-strict metric agrees: {{cmp[name=TSCG vs Raw, E2E-strict, pooled].diff_pp}}.

**Q4. Does the effect increase with tool count?**
No evidence that it does. The paired difference-in-differences tests whether the TSCG − Raw gap at size k differs from the gap at size 5:

| size k | change in the gap vs size 5 | Holm p |
|---:|---:|---:|
| 10 | {{inter[size=10].did_pp}} | {{inter[size=10].holm_p}} |
| 20 | {{inter[size=20].did_pp}} | {{inter[size=20].holm_p}} |
| 50 | {{inter[size=50].did_pp}} | {{inter[size=50].holm_p}} |
| 100 | {{inter[size=100].did_pp}} | {{inter[size=100].holm_p}} |

The gap is roughly constant across 5–100 tools. The CIs are wide (see `RESULTS.md`), so moderate size-dependence cannot be ruled out.

**Q5. Is the improvement explained primarily by token reduction?**
There was no improvement to explain; TSCG lowered success. The data also show that **token reduction alone did not change E2E**:
- Raw-minified carries the same information as Raw with fewer tokens (median per-tool compression {{tok[minified/all].median_compression_pct}}%). Its E2E was {{cmp[name=Raw-minified vs Raw, E2E, pooled].acc_b}} vs Raw {{cmp[name=Raw-minified vs Raw, E2E, pooled].acc_a}}: a difference of {{cmp[name=Raw-minified vs Raw, E2E, pooled].diff_pp}}, Holm p = {{cmp[name=Raw-minified vs Raw, E2E, pooled].holm_p}}.
- In a logistic model with log input tokens as a covariate, longer prompts were associated with lower success (coefficient {{glm[log_input_tokens].coef}}, p = {{glm[log_input_tokens].p}}).
- The TSCG effect remained after adjusting for tokens: coefficient {{glm[arm[tscg]].coef}} vs Raw, p = {{glm[arm[tscg]].p}}.

The two controls split the TSCG deficit into parts:
- *Information removed* — TSCG-info vs Raw: {{cmp[name=TSCG-info JSON vs Raw, E2E, pooled].diff_pp}} (Holm p = {{cmp[name=TSCG-info JSON vs Raw, E2E, pooled].holm_p}}).
- *TSCG text format at fixed information* — TSCG vs TSCG-info: {{cmp[name=TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled].diff_pp}} (Holm p = {{cmp[name=TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled].holm_p}}).
- *By schema stratum:*
  - Structured targets: TSCG {{cmp[name=TSCG vs Raw, E2E, structured targets].acc_b}} vs Raw {{cmp[name=TSCG vs Raw, E2E, structured targets].acc_a}}. TSCG and TSCG-info do not differ here ({{cmp[name=TSCG vs TSCG-info, E2E, structured targets].diff_pp}}, Holm p = {{cmp[name=TSCG vs TSCG-info, E2E, structured targets].holm_p}}).
  - Flat targets: the gap is smaller (TSCG {{cmp[name=TSCG vs Raw, E2E, flat targets].acc_b}} vs Raw {{cmp[name=TSCG vs Raw, E2E, flat targets].acc_a}}), and TSCG is below TSCG-info ({{cmp[name=TSCG vs TSCG-info, E2E, flat targets].diff_pp}}, Holm p = {{cmp[name=TSCG vs TSCG-info, E2E, flat targets].holm_p}}).

*Interpretation:*
- For structured schemas the deficit is consistent with information loss. TSCG drops nested structure in {{audit[structured].with_dropped_substructure}} of {{audit[structured].n}} structured tools.
- For flat schemas, a smaller format-related deficit remains.
- The TSCG-info control also differs from Raw in token count, so it does not separate information from length perfectly.

**Q6. Which failure modes disappear with TSCG?**
None clearly disappears.
- Malformed output was less frequent under TSCG ({{fail[arm=tscg|all].malformed output}} vs {{fail[arm=raw|all].malformed output}} for Raw, out of 500 each).
- The counts are small and this difference was not tested.
- Wrong-tool errors did not decrease ({{fail[arm=tscg|all].wrong tool}} vs {{fail[arm=raw|all].wrong tool}}).

**Q7. Which failure modes remain (or appear)?**
TSCG mainly adds argument-structure failures (counts per 500 requests, TSCG vs Raw):

| primary failure | TSCG | Raw |
|---|---:|---:|
| invalid argument type | {{fail[arm=tscg|all].invalid argument type}} | {{fail[arm=raw|all].invalid argument type}} |
| missing required argument | {{fail[arm=tscg|all].missing required argument}} | {{fail[arm=raw|all].missing required argument}} |
| hallucinated field | {{fail[arm=tscg|all].hallucinated field}} | {{fail[arm=raw|all].hallucinated field}} |

The leading failure in all arms remains "correct tool, wrong argument" (TSCG {{fail[arm=tscg|all].correct tool, wrong argument}}, Raw {{fail[arm=raw|all].correct tool, wrong argument}}).

These new failures match the information audit:
- types shown incorrectly in {{audit[all].with_type_changes}} tools;
- nested structure dropped in {{audit[all].with_dropped_substructure}} tools;
- required fields hidden in {{audit[all].with_required_not_in_properties}} tools.

**Q8. At what tool count does performance begin degrading?**
For Raw, E2E is first significantly below the 5-tool level at **{{deg[arm=raw].first_significant_drop_size}} tools** (same tasks, Holm-corrected within arm). Other arms:
- Raw-minified: first significant drop at {{deg[arm=minified].first_significant_drop_size}} tools.
- Normalized: no significant drop up to 100 tools.
- TSCG: first significant drop at {{deg[arm=tscg].first_significant_drop_size}} tools.
- TSCG-info: first significant drop at {{deg[arm=tscg_info].first_significant_drop_size}} tools.

Selection accuracy stays high up to 100 tools. Most of the decline comes from argument errors. "First significant drop" depends on power, and differences between arms in this value were not formally tested.

**Q9. Does TSCG move that degradation point?**
No evidence that it does.
- TSCG E2E is lower than Raw at every size.
- The TSCG − Raw gap does not change detectably with size (Q4).
- TSCG's first significant drop ({{deg[arm=tscg].first_significant_drop_size}}) is not earlier or later than Raw's in any tested sense.

**Q10. Is there enough evidence to justify a second experiment with Blaze-derived representations?**
*Partly, with conditions.* The results show that what the representation contains changes performance a lot (structured targets: {{cmp[name=TSCG vs Raw, E2E, structured targets].diff_pp}} under TSCG). In this experiment, removing schema information lowered success. The results do **not** show that any compact representation beats Raw: Normalized and Raw-minified did not differ detectably from Raw, and TSCG was worse. A Blaze-derived experiment is justified only as a targeted test with these conditions:
- the representation preserves full schema semantics (nested types, enums behind `$ref`, required fields, constraints);
- the main baseline is Raw-minified (equal information, fewer tokens);
- it focuses on structured schemas and on argument correctness, where the remaining errors are;
- it includes a second model, so that a model-specific result is not generalized.

## 4. Secondary results
- **Tokens** (model tokenizer): mean prompt at 100 tools is Raw {{main[size=100,arm=raw].input_tokens}}, Raw-minified {{main[size=100,arm=minified].input_tokens}}, TSCG {{main[size=100,arm=tscg].input_tokens}} and TSCG-info {{main[size=100,arm=tscg_info].input_tokens}}. Median per-tool TSCG compression: {{tok[tscg/all].median_compression_pct}}%.
- **Latency (SECONDARY/EXPLORATORY; 2 uncached requests per cell):** median at 100 tools is Raw {{lat[size=100,arm=raw].median_ms}} ms, TSCG {{lat[size=100,arm=tscg].median_ms}} ms and Raw-minified {{lat[size=100,arm=minified].median_ms}} ms. Latency follows prompt length; this sample supports no inferential claim.
- **Transformation time:** median per tool is TSCG {{tok[tscg/all].median_transform_ms}} ms and Normalized {{tok[normalized/all].median_transform_ms}} ms (negligible next to model latency).

## 5. Limitations and alternative explanations
- **One model.** Results are specific to Qwen3-1.7B (Q8_0) with greedy decoding. The TSCG authors report gains on other models and benchmarks; this experiment neither reproduces nor refutes those results in general.
- **One TSCG profile** (`conservative`, fixed by design). Other profiles were not tested.
- **The benchmark** consists of real schemas with generated tasks and single-call mocks. E2E reduces to "valid call with correct requested values". Multi-step orchestration was not tested.
- **Schema mix:** half the targets are structured (nested objects, arrays, `$ref`). TSCG drops this structure, so the pooled result depends on this mix. On flat targets alone the TSCG deficit is smaller.
- **Tasks:** 50 intents × 2 paraphrases sharing one gold answer. Paraphrase pairs are correlated, and CIs resample whole replicates.
- **Authored metadata:** tool names, descriptions and tasks were written by the experimenter. They are identical across arms but affect absolute levels.
- **Token covariate:** the information-matched control is not token-matched to TSCG. Information and length are only partly separated.
- **Execution artefacts** (all documented in `DECISIONS.md`):
  - Prompt-prefix caching was used. The pilot found 48/50 byte-identical outputs and 50/50 identical E2E outcomes between cached and uncached runs.
  - One container restart was resumed with the identical server configuration.
  - An earlier run (`full-v1-aborted`) was discarded after an out-of-memory kill.
  - 4 of 3,000 outputs hit the 512-token cap. In 3 of them the call was still recovered and scored as correct.
- **Statistics:** many secondary comparisons were made (Holm-corrected). Stratum results are post-hoc splits of a pre-specified factor.
