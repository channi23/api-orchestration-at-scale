# Results — pilot-v1

Requests analysed: 300

## Selection + arguments + end-to-end (full catalog shown)

Proportions in %. E2E 95% CI = cluster bootstrap over catalog replicates. Latency = median wall-clock; 'cached' uses llama.cpp prompt-prefix caching (catalog shared across a cell's tasks), 'uncached' from the latency sub-run.

| Tools | Representation | n | Selection | Arg EM | Field Acc | Schema valid | E2E [95% CI] | E2E-strict | Input tokens | Output tokens | Latency cached (ms) | Latency uncached (ms) | Ctx fail |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | Raw | 20 | 95.0 | 85.0 | 92.0 | 90.0 | 90.0 [80.0, 100.0] | 90.0 | 1473 | 55.0 | 4225 |  | 0 |
| 5 | Raw-minified | 20 | 100.0 | 90.0 | 96.3 | 95.0 | 90.0 [80.0, 100.0] | 90.0 | 911 | 55.6 | 3732 |  | 0 |
| 5 | Normalized | 20 | 95.0 | 85.0 | 92.0 | 90.0 | 90.0 [80.0, 100.0] | 90.0 | 1340 | 55.0 | 4369 |  | 0 |
| 5 | TSCG | 20 | 100.0 | 60.0 | 89.6 | 80.0 | 70.0 [70.0, 70.0] | 65.0 | 564 | 54.6 | 3616 |  | 0 |
| 5 | TSCG-info JSON | 20 | 100.0 | 65.0 | 90.3 | 80.0 | 75.0 [70.0, 80.0] | 65.0 | 1037 | 58.0 | 3700 |  | 0 |
| 20 | Raw | 20 | 100.0 | 80.0 | 94.0 | 90.0 | 90.0 [80.0, 100.0] | 85.0 | 5636 | 55.8 | 9732 |  | 0 |
| 20 | Raw-minified | 20 | 95.0 | 80.0 | 92.0 | 90.0 | 90.0 [80.0, 100.0] | 85.0 | 3386 | 55.8 | 6925 |  | 0 |
| 20 | Normalized | 20 | 100.0 | 80.0 | 94.0 | 90.0 | 90.0 [80.0, 100.0] | 85.0 | 5376 | 55.8 | 9454 |  | 0 |
| 20 | TSCG | 20 | 95.0 | 50.0 | 82.8 | 75.0 | 60.0 [50.0, 70.0] | 55.0 | 1745 | 55.0 | 4915 |  | 0 |
| 20 | TSCG-info JSON | 20 | 100.0 | 60.0 | 89.0 | 75.0 | 70.0 [60.0, 80.0] | 65.0 | 3509 | 57.2 | 7917 |  | 0 |

## Argument generation (tool fixed; only the gold tool shown)

| Representation | n | JSON valid | Arg EM | Field Acc | Schema valid | Semantic correct | E2E | E2E-strict | Input tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Raw | 20 | 95.0 | 80.0 | 91.3 | 90.0 | 85.0 | 85.0 | 80.0 | 397 |
| Raw-minified | 20 | 100.0 | 85.0 | 97.0 | 95.0 | 95.0 | 95.0 | 85.0 | 286 |
| Normalized | 20 | 95.0 | 80.0 | 91.3 | 90.0 | 85.0 | 85.0 | 80.0 | 371 |
| TSCG | 20 | 100.0 | 55.0 | 80.0 | 80.0 | 70.0 | 60.0 | 55.0 | 214 |
| TSCG-info JSON | 20 | 100.0 | 55.0 | 84.5 | 75.0 | 75.0 | 60.0 | 60.0 | 310 |

## Paired comparisons (B − A)

Exact McNemar on discordant pairs; Holm-adjusted across all secondary comparisons (primary reported unadjusted).

| Comparison | A | B | n pairs | A % | B % | Δ pp [95% CI] | rel. % | A-only / B-only | p (exact) | p (Holm) | OR disc. [95% CI] |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PRIMARY: TSCG vs Raw, E2E, pooled sizes | Raw | TSCG | 40 | 90.0 | 65.0 | -25.0 [-30.0, -20.0] | -27.8 | 10 / 0 | 0.00195 | 0.00195 | 0.05 [0.00, 0.81] |
| TSCG vs Raw, tool_correct, pooled | Raw | TSCG | 40 | 97.5 | 97.5 | +0.0 [+0.0, +0.0] | 0.0 | 1 / 1 | 1 | 1 | 1.00 [0.10, 9.61] |
| TSCG vs Raw, arg_exact_match, pooled | Raw | TSCG | 40 | 82.5 | 55.0 | -27.5 [-35.0, -20.0] | -33.3 | 11 / 0 | 0.000977 | 0.0195 | 0.04 [0.00, 0.74] |
| TSCG vs Raw, schema_valid, pooled | Raw | TSCG | 40 | 90.0 | 77.5 | -12.5 [-20.0, -5.0] | -13.9 | 5 / 0 | 0.0625 | 0.875 | 0.09 [0.01, 1.64] |
| Raw-minified vs Raw, E2E, pooled | Raw | Raw-minified | 40 | 90.0 | 90.0 | +0.0 [+0.0, +0.0] | 0.0 | 1 / 1 | 1 | 1 | 1.00 [0.10, 9.61] |
| Normalized vs Raw, E2E, pooled | Raw | Normalized | 40 | 90.0 | 90.0 | +0.0 [+0.0, +0.0] | 0.0 | 0 / 0 | 1 | 1 | 1.00 [0.02, 50.40] |
| TSCG-info JSON vs Raw, E2E, pooled | Raw | TSCG-info JSON | 40 | 90.0 | 72.5 | -17.5 [-35.0, +0.0] | -19.4 | 7 / 0 | 0.0156 | 0.266 | 0.07 [0.00, 1.17] |
| TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled | TSCG-info JSON | TSCG | 40 | 72.5 | 65.0 | -7.5 [-20.0, +5.0] | -10.3 | 4 / 1 | 0.375 | 1 | 0.33 [0.05, 2.12] |
| TSCG vs Raw-minified, E2E, pooled | Raw-minified | TSCG | 40 | 90.0 | 65.0 | -25.0 [-30.0, -20.0] | -27.8 | 11 / 1 | 0.00635 | 0.114 | 0.13 [0.02, 0.72] |
| TSCG vs Raw, E2E-strict, pooled | Raw | TSCG | 40 | 87.5 | 60.0 | -27.5 [-35.0, -20.0] | -31.4 | 11 / 0 | 0.000977 | 0.0195 | 0.04 [0.00, 0.74] |
| TSCG vs Raw, E2E, size 5 | Raw | TSCG | 20 | 90.0 | 70.0 | -20.0 [-30.0, -10.0] | -22.2 | 4 / 0 | 0.125 | 1 | 0.11 [0.01, 2.06] |
| TSCG vs Raw, selection, size 5 | Raw | TSCG | 20 | 95.0 | 100.0 | +5.0 [+0.0, +10.0] | 5.3 | 0 / 1 | 1 | 1 | 3.00 [0.12, 73.65] |
| TSCG vs Raw, E2E, size 20 | Raw | TSCG | 20 | 90.0 | 60.0 | -30.0 [-30.0, -30.0] | -33.3 | 6 / 0 | 0.0312 | 0.5 | 0.08 [0.00, 1.37] |
| TSCG vs Raw, selection, size 20 | Raw | TSCG | 20 | 100.0 | 95.0 | -5.0 [-10.0, +0.0] | -5.0 | 1 / 0 | 1 | 1 | 0.33 [0.01, 8.18] |
| TSCG vs Raw, E2E, flat targets | Raw | TSCG | 20 | 100.0 | 80.0 | -20.0 [-33.3, +0.0] | -20.0 | 4 / 0 | 0.125 | 1 | 0.11 [0.01, 2.06] |
| TSCG vs TSCG-info, E2E, flat targets | TSCG-info JSON | TSCG | 20 | 100.0 | 80.0 | -20.0 [-33.3, +0.0] | -20.0 | 4 / 0 | 0.125 | 1 | 0.11 [0.01, 2.06] |
| TSCG vs Raw, E2E, structured targets | Raw | TSCG | 20 | 80.0 | 50.0 | -30.0 [-50.0, +0.0] | -37.5 | 6 / 0 | 0.0312 | 0.5 | 0.08 [0.00, 1.37] |
| TSCG vs TSCG-info, E2E, structured targets | TSCG-info JSON | TSCG | 20 | 45.0 | 50.0 | +5.0 [+0.0, +8.3] | 11.1 | 0 / 1 | 1 | 1 | 3.00 [0.12, 73.65] |
| ARGGEN: TSCG vs Raw, E2E (tool fixed) | Raw | TSCG | 20 | 85.0 | 60.0 | -25.0 [-40.0, -10.0] | -29.4 | 5 / 0 | 0.0625 | 0.875 | 0.09 [0.01, 1.64] |
| ARGGEN: TSCG vs Raw, arg EM (tool fixed) | Raw | TSCG | 20 | 80.0 | 55.0 | -25.0 [-50.0, +0.0] | -31.2 | 6 / 1 | 0.125 | 1 | 0.23 [0.04, 1.36] |
| ARGGEN: TSCG vs TSCG-info, E2E (tool fixed) | TSCG-info JSON | TSCG | 20 | 60.0 | 60.0 | +0.0 [+0.0, +0.0] | 0.0 | 1 / 1 | 1 | 1 | 1.00 [0.10, 9.61] |

## Degradation vs smallest catalog (same tasks, E2E, Holm within arm)

| Representation | first size with significant drop | per-size Δ pp (Holm p) |
|---|---:|---|
| Raw | none | 20: +0.0 (1) |
| Raw-minified | none | 20: +0.0 (1) |
| Normalized | none | 20: +0.0 (1) |
| TSCG | none | 20: -10.0 (0.5) |
| TSCG-info JSON | none | 20: -5.0 (1) |

## Token-count covariate model

E2E ~ log(input tokens) + arm (ref=raw); logit; cluster-robust SE by intent

| term | coef | SE | p |
|---|---:|---:|---:|
| const | +3.607 | 1.499 | 0.0162 |
| log_input_tokens | -0.176 | 0.153 | 0.249 |
| arm[minified] | -0.087 | 0.384 | 0.82 |
| arm[normalized] | -0.012 | 0.010 | 0.234 |
| arm[tscg] | -1.771 | 0.929 | 0.0566 |
| arm[tscg_info] | -1.304 | 0.869 | 0.134 |

## Primary failure categories (selection family, all sizes)

| Failure | Raw | Raw-minified | Normalized | TSCG | TSCG-info JSON |
|---|---:|---:|---:|---:|---:|
| wrong tool | 0 | 0 | 0 | 1 | 0 |
| multiple-tool confusion | 0 | 0 | 0 | 0 | 0 |
| correct tool, wrong argument | 0 | 1 | 0 | 5 | 2 |
| missing required argument | 0 | 0 | 0 | 0 | 0 |
| invalid argument type | 0 | 0 | 0 | 4 | 5 |
| invalid enum/value | 0 | 0 | 0 | 0 | 0 |
| hallucinated field | 0 | 0 | 0 | 0 | 0 |
| ignored schema constraint | 3 | 2 | 3 | 4 | 4 |
| context-length failure | 0 | 0 | 0 | 0 | 0 |
| malformed output | 1 | 1 | 1 | 0 | 0 |
| execution failure | 0 | 0 | 0 | 0 | 0 |
| semantic/task failure | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 0 |
