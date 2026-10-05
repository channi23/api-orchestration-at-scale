# Representation experiment v1 — final report

**Run:** `full-v2` (main, 3,000<sup>[1]</sup> requests) + `latency-v2` (secondary/exploratory, 50 requests).
**Authoritative numbers:** `analysis/full-v2/RESULTS.md` and `results.json`. Every number in this report is
resolved from `results.json` (or from the frozen artifacts) by `src/render_text.py`; see the provenance list at the end.

**Label:** compact-model experiment (Qwen3-1.7B, Q8_0, llama.cpp, CPU). This is not an external/frontier-model reproduction.

## 1. What was tested
- One fixed model saw the same 100<sup>[2]</sup> tasks (50<sup>[3]</sup> intents × 2 paraphrases) under five schema representations: Raw JSON, Raw-minified JSON, Normalized JSON, official TSCG 1.4.3 (`conservative`), and a TSCG-information JSON control.
- The tasks were evaluated in 50<sup>[4]</sup> nested catalogs: 10<sup>[5]</sup> replicates × 5 sizes (5, 10, 20, 50, 100 tools).
- Each task is paired across all representations and all sizes.
- The tool pool comes from 9,558<sup>[6]</sup> real JSONSchemaBench schemas, which were audited down to 4,219<sup>[7]</sup> eligible schemas and then 300<sup>[8]</sup> reviewed tools.
- The tasks and mock execution are generated. The benchmark is therefore real schemas with a generated workload, not a real API workload.
- Primary outcome (pre-registered): **end-to-end (E2E) success** = valid JSON ∧ correct tool ∧ arguments valid against the raw schema ∧ requested values correct ∧ mock receipt matches.

## 2. Main results (observed)

**Primary comparison — TSCG vs Raw, E2E, all sizes pooled (500<sup>[9]</sup> paired requests):**
- Raw scored 82.4%<sup>[10]</sup> and TSCG 56.6%<sup>[11]</sup>.
- Difference: -25.8 pp<sup>[12]</sup>, 95% CI [-32.8, -18.2]<sup>[13]</sup> pp.
- Exact McNemar p = 3.3e-30<sup>[14]</sup>.
- Discordant pairs: 139<sup>[15]</sup> where only Raw succeeded, 10<sup>[16]</sup> where only TSCG succeeded.

E2E by catalog size (Raw / Raw-minified / Normalized / TSCG / TSCG-info):

| tools | Raw | Raw-minified | Normalized | TSCG | TSCG-info |
|---:|---:|---:|---:|---:|---:|
| 5 | 92.0%<sup>[17]</sup> | 89.0%<sup>[18]</sup> | 87.0%<sup>[19]</sup> | 64.0%<sup>[20]</sup> | 68.0%<sup>[21]</sup> |
| 10 | 87.0%<sup>[22]</sup> | 88.0%<sup>[23]</sup> | 87.0%<sup>[24]</sup> | 63.0%<sup>[25]</sup> | 65.0%<sup>[26]</sup> |
| 20 | 80.0%<sup>[27]</sup> | 82.0%<sup>[28]</sup> | 82.0%<sup>[29]</sup> | 58.0%<sup>[30]</sup> | 65.0%<sup>[31]</sup> |
| 50 | 78.0%<sup>[32]</sup> | 81.0%<sup>[33]</sup> | 76.0%<sup>[34]</sup> | 53.0%<sup>[35]</sup> | 60.0%<sup>[36]</sup> |
| 100 | 75.0%<sup>[37]</sup> | 74.0%<sup>[38]</sup> | 81.0%<sup>[39]</sup> | 45.0%<sup>[40]</sup> | 54.0%<sup>[41]</sup> |

Each cell has n = 100 requests. CIs and all other metrics are in `RESULTS.md`.

## 3. Answers to the ten research questions

**Q1. Does TSCG improve tool selection?**
No improvement was detected.
- Pooled selection accuracy: Raw 96.2%<sup>[42]</sup>, TSCG 97.0%<sup>[43]</sup>.
- Difference: +0.8 pp<sup>[44]</sup>, 95% CI [-1.8, +3.8]<sup>[45]</sup>, Holm p = 1<sup>[46]</sup>.
- Selection is near ceiling for every representation at every size (lowest cell: 92.0%<sup>[47]</sup>).
- The CI excludes large effects but cannot show the two are equal.

**Q2. Does TSCG improve argument generation?**
No. It is worse.
- With the tool fixed (only the gold tool shown): E2E Raw 84.0%<sup>[48]</sup> vs TSCG 62.0%<sup>[49]</sup>. Difference -22.0 pp<sup>[50]</sup>, Holm p = 0.00041<sup>[51]</sup>.
- Field accuracy: Raw 91.6%<sup>[52]</sup> vs TSCG 75.2%<sup>[53]</sup>.
- In the full-catalog task, argument exact match is Raw 72.0%<sup>[54]</sup> vs TSCG 53.8%<sup>[55]</sup> (Holm p = 6.9e-14<sup>[56]</sup>).
- Schema validity is Raw 90.8%<sup>[57]</sup> vs TSCG 67.2%<sup>[58]</sup>.

**Q3. Does TSCG improve end-to-end task success?**
No. It lowers E2E success with this model and benchmark.
- The primary comparison shows -25.8 pp<sup>[12]</sup>.
- The direction is the same at every size: -28.0 pp<sup>[59]</sup> at 5 tools, -22.0 pp<sup>[60]</sup> at 20 and -30.0 pp<sup>[61]</sup> at 100.
- All per-size differences are significant after Holm correction.
- The secondary E2E-strict metric agrees: -19.8 pp<sup>[62]</sup>.

**Q4. Does the effect increase with tool count?**
No evidence that it does. The paired difference-in-differences tests whether the TSCG − Raw gap at size k differs from the gap at size 5:

| size k | change in the gap vs size 5 | Holm p |
|---:|---:|---:|
| 10 | +4.0 pp<sup>[63]</sup> | 1<sup>[64]</sup> |
| 20 | +6.0 pp<sup>[65]</sup> | 1<sup>[66]</sup> |
| 50 | +3.0 pp<sup>[67]</sup> | 1<sup>[68]</sup> |
| 100 | -2.0 pp<sup>[69]</sup> | 1<sup>[70]</sup> |

The gap is roughly constant across 5–100 tools. The CIs are wide (see `RESULTS.md`), so moderate size-dependence cannot be ruled out.

**Q5. Is the improvement explained primarily by token reduction?**
There was no improvement to explain; TSCG lowered success. The data also show that **token reduction alone did not change E2E**:
- Raw-minified carries the same information as Raw with fewer tokens (median per-tool compression 40.1<sup>[71]</sup>%). Its E2E was 82.8%<sup>[72]</sup> vs Raw 82.4%<sup>[73]</sup>: a difference of +0.4 pp<sup>[74]</sup>, Holm p = 1<sup>[75]</sup>.
- In a logistic model with log input tokens as a covariate, longer prompts were associated with lower success (coefficient -0.27<sup>[76]</sup>, p = 5.6e-05<sup>[77]</sup>).
- The TSCG effect remained after adjusting for tokens: coefficient -1.63<sup>[78]</sup> vs Raw, p = 3.1e-12<sup>[79]</sup>.

The two controls split the TSCG deficit into parts:
- *Information removed* — TSCG-info vs Raw: -20.0 pp<sup>[80]</sup> (Holm p = 3.5e-18<sup>[81]</sup>).
- *TSCG text format at fixed information* — TSCG vs TSCG-info: -5.8 pp<sup>[82]</sup> (Holm p = 0.002<sup>[83]</sup>).
- *By schema stratum:*
  - Structured targets: TSCG 32.8%<sup>[84]</sup> vs Raw 76.4%<sup>[85]</sup>. TSCG and TSCG-info do not differ here (-0.4 pp<sup>[86]</sup>, Holm p = 1<sup>[87]</sup>).
  - Flat targets: the gap is smaller (TSCG 80.4%<sup>[88]</sup> vs Raw 88.4%<sup>[89]</sup>), and TSCG is below TSCG-info (-11.2 pp<sup>[90]</sup>, Holm p = 4.4e-06<sup>[91]</sup>).

*Interpretation:*
- For structured schemas the deficit is consistent with information loss. TSCG drops nested structure in 117<sup>[92]</sup> of 126<sup>[93]</sup> structured tools.
- For flat schemas, a smaller format-related deficit remains.
- The TSCG-info control also differs from Raw in token count, so it does not separate information from length perfectly.

**Q6. Which failure modes disappear with TSCG?**
None clearly disappears.
- Malformed output was less frequent under TSCG (4<sup>[94]</sup> vs 11<sup>[95]</sup> for Raw, out of 500 each).
- The counts are small and this difference was not tested.
- Wrong-tool errors did not decrease (11<sup>[96]</sup> vs 8<sup>[97]</sup>).

**Q7. Which failure modes remain (or appear)?**
TSCG mainly adds argument-structure failures (counts per 500 requests, TSCG vs Raw):

| primary failure | TSCG | Raw |
|---|---:|---:|
| invalid argument type | 71<sup>[98]</sup> | 7<sup>[99]</sup> |
| missing required argument | 56<sup>[100]</sup> | 11<sup>[101]</sup> |
| hallucinated field | 10<sup>[102]</sup> | 0<sup>[103]</sup> |

The leading failure in all arms remains "correct tool, wrong argument" (TSCG 53<sup>[104]</sup>, Raw 42<sup>[105]</sup>).

These new failures match the information audit:
- types shown incorrectly in 14<sup>[106]</sup> tools;
- nested structure dropped in 117<sup>[107]</sup> tools;
- required fields hidden in 3<sup>[108]</sup> tools.

**Q8. At what tool count does performance begin degrading?**
For Raw, E2E is first significantly below the 5-tool level at **20<sup>[109]</sup> tools** (same tasks, Holm-corrected within arm). Other arms:
- Raw-minified: first significant drop at 100<sup>[110]</sup> tools.
- Normalized: no significant drop up to 100 tools.
- TSCG: first significant drop at 50<sup>[111]</sup> tools.
- TSCG-info: first significant drop at 100<sup>[112]</sup> tools.

Selection accuracy stays high up to 100 tools. Most of the decline comes from argument errors. "First significant drop" depends on power, and differences between arms in this value were not formally tested.

**Q9. Does TSCG move that degradation point?**
No evidence that it does.
- TSCG E2E is lower than Raw at every size.
- The TSCG − Raw gap does not change detectably with size (Q4).
- TSCG's first significant drop (50<sup>[111]</sup>) is not earlier or later than Raw's in any tested sense.

**Q10. Is there enough evidence to justify a second experiment with Blaze-derived representations?**
*Partly, with conditions.* The results show that what the representation contains changes performance a lot (structured targets: -43.6 pp<sup>[113]</sup> under TSCG). In this experiment, removing schema information lowered success. The results do **not** show that any compact representation beats Raw: Normalized and Raw-minified did not differ detectably from Raw, and TSCG was worse. A Blaze-derived experiment is justified only as a targeted test with these conditions:
- the representation preserves full schema semantics (nested types, enums behind `$ref`, required fields, constraints);
- the main baseline is Raw-minified (equal information, fewer tokens);
- it focuses on structured schemas and on argument correctness, where the remaining errors are;
- it includes a second model, so that a model-specific result is not generalized.

## 4. Secondary results
- **Tokens** (model tokenizer): mean prompt at 100 tools is Raw 27,206<sup>[114]</sup>, Raw-minified 16,085<sup>[115]</sup>, TSCG 7,746<sup>[116]</sup> and TSCG-info 16,573<sup>[117]</sup>. Median per-tool TSCG compression: 71.7<sup>[118]</sup>%.
- **Latency (SECONDARY/EXPLORATORY; 2 uncached requests per cell):** median at 100 tools is Raw 674,998<sup>[119]</sup> ms, TSCG 98,922<sup>[120]</sup> ms and Raw-minified 282,195<sup>[121]</sup> ms. Latency follows prompt length; this sample supports no inferential claim.
- **Transformation time:** median per tool is TSCG 0.02<sup>[122]</sup> ms and Normalized 0.01<sup>[123]</sup> ms (negligible next to model latency).

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


---
**Provenance.** Every number above is resolved automatically (`src/provenance.py`) from validated artifacts. Analysis file: `analysis/full-v2/results.json` (sha256 `5cb9d5311d61734e…`).

[1] `meta.n_requests`
[2] `meta.n_tasks`
[3] `meta.n_intents`
[4] `meta.n_catalogs`
[5] `meta.n_replicates`
[6] `meta.n_schemas`
[7] `meta.n_eligible`
[8] `meta.n_tools`
[9] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].n_pairs`
[10] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_a`
[11] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].acc_b`
[12] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].diff_pp`
[13] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].ci95_diff_pp`
[14] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].mcnemar_exact_p`
[15] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].discordant_a_only`
[16] `cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].discordant_b_only`
[17] `main[size=5,arm=raw].e2e`
[18] `main[size=5,arm=minified].e2e`
[19] `main[size=5,arm=normalized].e2e`
[20] `main[size=5,arm=tscg].e2e`
[21] `main[size=5,arm=tscg_info].e2e`
[22] `main[size=10,arm=raw].e2e`
[23] `main[size=10,arm=minified].e2e`
[24] `main[size=10,arm=normalized].e2e`
[25] `main[size=10,arm=tscg].e2e`
[26] `main[size=10,arm=tscg_info].e2e`
[27] `main[size=20,arm=raw].e2e`
[28] `main[size=20,arm=minified].e2e`
[29] `main[size=20,arm=normalized].e2e`
[30] `main[size=20,arm=tscg].e2e`
[31] `main[size=20,arm=tscg_info].e2e`
[32] `main[size=50,arm=raw].e2e`
[33] `main[size=50,arm=minified].e2e`
[34] `main[size=50,arm=normalized].e2e`
[35] `main[size=50,arm=tscg].e2e`
[36] `main[size=50,arm=tscg_info].e2e`
[37] `main[size=100,arm=raw].e2e`
[38] `main[size=100,arm=minified].e2e`
[39] `main[size=100,arm=normalized].e2e`
[40] `main[size=100,arm=tscg].e2e`
[41] `main[size=100,arm=tscg_info].e2e`
[42] `cmp[name=TSCG vs Raw, tool_correct, pooled].acc_a`
[43] `cmp[name=TSCG vs Raw, tool_correct, pooled].acc_b`
[44] `cmp[name=TSCG vs Raw, tool_correct, pooled].diff_pp`
[45] `cmp[name=TSCG vs Raw, tool_correct, pooled].ci95_diff_pp`
[46] `cmp[name=TSCG vs Raw, tool_correct, pooled].holm_p`
[47] `main[size=100,arm=raw].selection`
[48] `arggen[arm=raw].e2e`
[49] `arggen[arm=tscg].e2e`
[50] `cmp[name=ARGGEN: TSCG vs Raw, E2E (tool fixed)].diff_pp`
[51] `cmp[name=ARGGEN: TSCG vs Raw, E2E (tool fixed)].holm_p`
[52] `arggen[arm=raw].field_acc`
[53] `arggen[arm=tscg].field_acc`
[54] `cmp[name=TSCG vs Raw, arg_exact_match, pooled].acc_a`
[55] `cmp[name=TSCG vs Raw, arg_exact_match, pooled].acc_b`
[56] `cmp[name=TSCG vs Raw, arg_exact_match, pooled].holm_p`
[57] `cmp[name=TSCG vs Raw, schema_valid, pooled].acc_a`
[58] `cmp[name=TSCG vs Raw, schema_valid, pooled].acc_b`
[59] `cmp[name=TSCG vs Raw, E2E, size 5].diff_pp`
[60] `cmp[name=TSCG vs Raw, E2E, size 20].diff_pp`
[61] `cmp[name=TSCG vs Raw, E2E, size 100].diff_pp`
[62] `cmp[name=TSCG vs Raw, E2E-strict, pooled].diff_pp`
[63] `inter[size=10].did_pp`
[64] `inter[size=10].holm_p`
[65] `inter[size=20].did_pp`
[66] `inter[size=20].holm_p`
[67] `inter[size=50].did_pp`
[68] `inter[size=50].holm_p`
[69] `inter[size=100].did_pp`
[70] `inter[size=100].holm_p`
[71] `tok[minified/all].median_compression_pct`
[72] `cmp[name=Raw-minified vs Raw, E2E, pooled].acc_b`
[73] `cmp[name=Raw-minified vs Raw, E2E, pooled].acc_a`
[74] `cmp[name=Raw-minified vs Raw, E2E, pooled].diff_pp`
[75] `cmp[name=Raw-minified vs Raw, E2E, pooled].holm_p`
[76] `glm[log_input_tokens].coef`
[77] `glm[log_input_tokens].p`
[78] `glm[arm[tscg]].coef`
[79] `glm[arm[tscg]].p`
[80] `cmp[name=TSCG-info JSON vs Raw, E2E, pooled].diff_pp`
[81] `cmp[name=TSCG-info JSON vs Raw, E2E, pooled].holm_p`
[82] `cmp[name=TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled].diff_pp`
[83] `cmp[name=TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled].holm_p`
[84] `cmp[name=TSCG vs Raw, E2E, structured targets].acc_b`
[85] `cmp[name=TSCG vs Raw, E2E, structured targets].acc_a`
[86] `cmp[name=TSCG vs TSCG-info, E2E, structured targets].diff_pp`
[87] `cmp[name=TSCG vs TSCG-info, E2E, structured targets].holm_p`
[88] `cmp[name=TSCG vs Raw, E2E, flat targets].acc_b`
[89] `cmp[name=TSCG vs Raw, E2E, flat targets].acc_a`
[90] `cmp[name=TSCG vs TSCG-info, E2E, flat targets].diff_pp`
[91] `cmp[name=TSCG vs TSCG-info, E2E, flat targets].holm_p`
[92] `audit[structured].with_dropped_substructure`
[93] `audit[structured].n`
[94] `fail[arm=tscg|all].malformed output`
[95] `fail[arm=raw|all].malformed output`
[96] `fail[arm=tscg|all].wrong tool`
[97] `fail[arm=raw|all].wrong tool`
[98] `fail[arm=tscg|all].invalid argument type`
[99] `fail[arm=raw|all].invalid argument type`
[100] `fail[arm=tscg|all].missing required argument`
[101] `fail[arm=raw|all].missing required argument`
[102] `fail[arm=tscg|all].hallucinated field`
[103] `fail[arm=raw|all].hallucinated field`
[104] `fail[arm=tscg|all].correct tool, wrong argument`
[105] `fail[arm=raw|all].correct tool, wrong argument`
[106] `audit[all].with_type_changes`
[107] `audit[all].with_dropped_substructure`
[108] `audit[all].with_required_not_in_properties`
[109] `deg[arm=raw].first_significant_drop_size`
[110] `deg[arm=minified].first_significant_drop_size`
[111] `deg[arm=tscg].first_significant_drop_size`
[112] `deg[arm=tscg_info].first_significant_drop_size`
[113] `cmp[name=TSCG vs Raw, E2E, structured targets].diff_pp`
[114] `main[size=100,arm=raw].input_tokens`
[115] `main[size=100,arm=minified].input_tokens`
[116] `main[size=100,arm=tscg].input_tokens`
[117] `main[size=100,arm=tscg_info].input_tokens`
[118] `tok[tscg/all].median_compression_pct`
[119] `lat[size=100,arm=raw].median_ms`
[120] `lat[size=100,arm=tscg].median_ms`
[121] `lat[size=100,arm=minified].median_ms`
[122] `tok[tscg/all].median_transform_ms`
[123] `tok[normalized/all].median_transform_ms`
