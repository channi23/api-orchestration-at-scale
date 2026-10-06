# Results — full-v2

Requests analysed: 3000

## Selection + arguments + end-to-end (full catalog shown)

Proportions in %. E2E 95% CI = cluster bootstrap over catalog replicates. Latency = median wall-clock; 'cached' uses llama.cpp prompt-prefix caching (catalog shared across a cell's tasks), 'uncached' = median of the reduced SECONDARY/EXPLORATORY latency sub-run (2 tasks per cell; see latency section).

| Tools | Representation | n | Selection | Arg EM | Field Acc | Schema valid | E2E [95% CI] | E2E-strict | Input tokens | Output tokens | Latency cached (ms) | Latency uncached (ms) | Ctx fail |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | Raw | 100 | 97.0 | 79.0 | 95.4 | 96.0 | 92.0 [87.0, 96.0] | 81.0 | 1498 | 59.9 | 4633 | 16063 | 0 |
| 5 | Raw-minified | 100 | 99.0 | 82.0 | 96.0 | 96.0 | 89.0 [78.0, 97.0] | 83.0 | 925 | 55.0 | 3996 | 11807 | 0 |
| 5 | Normalized | 100 | 96.0 | 74.0 | 93.0 | 94.0 | 87.0 [82.0, 92.0] | 75.0 | 1418 | 60.1 | 4442 | 14908 | 0 |
| 5 | TSCG | 100 | 100.0 | 60.0 | 78.3 | 71.0 | 64.0 [54.0, 76.0] | 61.0 | 514 | 54.3 | 3375 | 7945 | 0 |
| 5 | TSCG-info JSON | 100 | 100.0 | 56.0 | 80.5 | 74.0 | 68.0 [58.0, 79.0] | 59.0 | 971 | 54.8 | 4087 | 12148 | 0 |
| 10 | Raw | 100 | 98.0 | 77.0 | 95.0 | 91.0 | 87.0 [81.0, 93.0] | 78.0 | 2933 | 56.0 | 6594 | 30679 | 0 |
| 10 | Raw-minified | 100 | 99.0 | 81.0 | 95.2 | 95.0 | 88.0 [82.0, 94.0] | 85.0 | 1759 | 59.7 | 5048 | 18195 | 0 |
| 10 | Normalized | 100 | 98.0 | 79.0 | 95.3 | 90.0 | 87.0 [80.0, 94.0] | 80.0 | 2796 | 56.7 | 6382 | 28418 | 0 |
| 10 | TSCG | 100 | 99.0 | 59.0 | 77.9 | 71.0 | 63.0 [52.0, 74.0] | 60.0 | 869 | 50.7 | 3659 | 11541 | 0 |
| 10 | TSCG-info JSON | 100 | 100.0 | 54.0 | 77.8 | 72.0 | 65.0 [55.0, 76.0] | 55.0 | 1767 | 54.5 | 4827 | 21387 | 0 |
| 20 | Raw | 100 | 97.0 | 71.0 | 91.9 | 90.0 | 80.0 [70.0, 89.0] | 72.0 | 5639 | 56.9 | 10107 | 61631 | 0 |
| 20 | Raw-minified | 100 | 96.0 | 78.0 | 91.5 | 91.0 | 82.0 [73.0, 90.0] | 79.0 | 3358 | 54.4 | 6804 | 32573 | 0 |
| 20 | Normalized | 100 | 98.0 | 73.0 | 92.7 | 91.0 | 82.0 [73.0, 90.0] | 75.0 | 5368 | 56.9 | 9737 | 56745 | 0 |
| 20 | TSCG | 100 | 98.0 | 55.0 | 75.3 | 67.0 | 58.0 [46.0, 72.0] | 56.0 | 1640 | 49.9 | 4719 | 18350 | 0 |
| 20 | TSCG-info JSON | 100 | 98.0 | 57.0 | 78.8 | 69.0 | 65.0 [55.0, 75.0] | 58.0 | 3399 | 54.6 | 6941 | 36621 | 0 |
| 50 | Raw | 100 | 97.0 | 66.0 | 90.2 | 90.0 | 78.0 [66.0, 88.0] | 71.0 | 13458 | 57.8 | 20454 | 204553 | 0 |
| 50 | Raw-minified | 100 | 100.0 | 72.0 | 92.2 | 92.0 | 81.0 [72.0, 89.0] | 75.0 | 7975 | 55.6 | 13012 | 94397 | 0 |
| 50 | Normalized | 100 | 97.0 | 68.0 | 91.0 | 91.0 | 76.0 [65.0, 86.0] | 71.0 | 12786 | 56.9 | 18934 | 192388 | 0 |
| 50 | TSCG | 100 | 96.0 | 52.0 | 72.7 | 66.0 | 53.0 [45.0, 60.0] | 53.0 | 3879 | 52.8 | 7318 | 38989 | 0 |
| 50 | TSCG-info JSON | 100 | 97.0 | 55.0 | 78.7 | 68.0 | 60.0 [49.0, 73.0] | 57.0 | 8265 | 53.8 | 12390 | 100735 | 0 |
| 100 | Raw | 100 | 92.0 | 67.0 | 86.1 | 87.0 | 75.0 [62.0, 86.0] | 71.0 | 27206 | 56.7 | 36241 | 674998 | 0 |
| 100 | Raw-minified | 100 | 97.0 | 64.0 | 90.0 | 90.0 | 74.0 [62.0, 86.0] | 66.0 | 16085 | 56.1 | 22337 | 282195 | 0 |
| 100 | Normalized | 100 | 95.0 | 72.0 | 90.0 | 91.0 | 81.0 [69.0, 91.0] | 74.0 | 25790 | 56.5 | 35194 | 619006 | 0 |
| 100 | TSCG | 100 | 92.0 | 43.0 | 65.5 | 61.0 | 45.0 [36.0, 54.0] | 44.0 | 7746 | 53.8 | 12233 | 98922 | 0 |
| 100 | TSCG-info JSON | 100 | 95.0 | 47.0 | 72.8 | 64.0 | 54.0 [43.0, 67.0] | 48.0 | 16573 | 57.6 | 23131 | 297278 | 0 |

## Argument generation (tool fixed; only the gold tool shown)

| Representation | n | JSON valid | Arg EM | Field Acc | Schema valid | Semantic correct | E2E | E2E-strict | Input tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Raw | 100 | 95.0 | 75.0 | 91.6 | 90.0 | 86.0 | 84.0 | 77.0 | 399 |
| Raw-minified | 100 | 98.0 | 79.0 | 93.3 | 92.0 | 86.0 | 86.0 | 80.0 | 285 |
| Normalized | 100 | 96.0 | 75.0 | 92.3 | 94.0 | 85.0 | 85.0 | 78.0 | 383 |
| TSCG | 100 | 99.0 | 60.0 | 75.2 | 71.0 | 64.0 | 62.0 | 60.0 | 200 |
| TSCG-info JSON | 100 | 99.0 | 57.0 | 79.2 | 70.0 | 68.0 | 65.0 | 58.0 | 293 |

## Paired comparisons (B − A)

Exact McNemar on discordant pairs; Holm-adjusted across all secondary comparisons (primary reported unadjusted).

| Comparison | A | B | n pairs | A % | B % | Δ pp [95% CI] | rel. % | A-only / B-only | p (exact) | p (Holm) | OR disc. [95% CI] |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PRIMARY: TSCG vs Raw, E2E, pooled sizes | Raw | TSCG | 500 | 82.4 | 56.6 | -25.8 [-32.8, -18.2] | -31.3 | 139 / 10 | 3.29e-30 | 3.29e-30 | 0.08 [0.04, 0.14] |
| TSCG vs Raw, tool_correct, pooled | Raw | TSCG | 500 | 96.2 | 97.0 | +0.8 [-1.8, +3.8] | 0.8 | 10 / 14 | 0.541 | 1 | 1.38 [0.62, 3.06] |
| TSCG vs Raw, arg_exact_match, pooled | Raw | TSCG | 500 | 72.0 | 53.8 | -18.2 [-24.8, -11.0] | -25.3 | 116 / 25 | 3.28e-15 | 6.89e-14 | 0.22 [0.14, 0.34] |
| TSCG vs Raw, schema_valid, pooled | Raw | TSCG | 500 | 90.8 | 67.2 | -23.6 [-33.4, -14.2] | -26.0 | 125 / 7 | 4.58e-29 | 1.19e-27 | 0.06 [0.03, 0.12] |
| Raw-minified vs Raw, E2E, pooled | Raw | Raw-minified | 500 | 82.4 | 82.8 | +0.4 [-1.6, +2.6] | 0.5 | 27 / 29 | 0.894 | 1 | 1.07 [0.64, 1.80] |
| Normalized vs Raw, E2E, pooled | Raw | Normalized | 500 | 82.4 | 82.6 | +0.2 [-1.6, +2.0] | 0.2 | 15 / 16 | 1 | 1 | 1.06 [0.53, 2.13] |
| TSCG-info JSON vs Raw, E2E, pooled | Raw | TSCG-info JSON | 500 | 82.4 | 62.4 | -20.0 [-30.0, -9.4] | -24.3 | 117 / 17 | 1.51e-19 | 3.48e-18 | 0.15 [0.09, 0.25] |
| TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled | TSCG-info JSON | TSCG | 500 | 62.4 | 56.6 | -5.8 [-10.0, -1.2] | -9.3 | 43 / 14 | 0.000154 | 0.002 | 0.33 [0.18, 0.60] |
| TSCG vs Raw-minified, E2E, pooled | Raw-minified | TSCG | 500 | 82.8 | 56.6 | -26.2 [-34.2, -17.4] | -31.6 | 145 / 14 | 1.27e-28 | 3.18e-27 | 0.10 [0.06, 0.17] |
| TSCG vs Raw, E2E-strict, pooled | Raw | TSCG | 500 | 74.6 | 54.8 | -19.8 [-26.4, -12.2] | -26.5 | 120 / 21 | 4.81e-18 | 1.06e-16 | 0.18 [0.11, 0.28] |
| TSCG vs Raw, E2E, size 5 | Raw | TSCG | 100 | 92.0 | 64.0 | -28.0 [-36.0, -18.0] | -30.4 | 29 / 1 | 5.77e-08 | 1.15e-06 | 0.05 [0.01, 0.26] |
| TSCG vs Raw, selection, size 5 | Raw | TSCG | 100 | 97.0 | 100.0 | +3.0 [+0.0, +6.0] | 3.1 | 0 / 3 | 0.25 | 1 | 7.00 [0.36, 135.52] |
| TSCG vs Raw, E2E, size 10 | Raw | TSCG | 100 | 87.0 | 63.0 | -24.0 [-33.0, -15.0] | -27.6 | 25 / 1 | 8.05e-07 | 1.29e-05 | 0.06 [0.01, 0.31] |
| TSCG vs Raw, selection, size 10 | Raw | TSCG | 100 | 98.0 | 99.0 | +1.0 [-2.0, +4.0] | 1.0 | 1 / 2 | 1 | 1 | 1.67 [0.22, 12.62] |
| TSCG vs Raw, E2E, size 20 | Raw | TSCG | 100 | 80.0 | 58.0 | -22.0 [-36.0, -6.0] | -27.5 | 26 / 4 | 5.95e-05 | 0.000833 | 0.17 [0.06, 0.46] |
| TSCG vs Raw, selection, size 20 | Raw | TSCG | 100 | 97.0 | 98.0 | +1.0 [-4.0, +8.0] | 1.0 | 2 / 3 | 1 | 1 | 1.40 [0.28, 7.10] |
| TSCG vs Raw, E2E, size 50 | Raw | TSCG | 100 | 78.0 | 53.0 | -25.0 [-33.0, -16.0] | -32.1 | 26 / 1 | 4.17e-07 | 7.09e-06 | 0.06 [0.01, 0.29] |
| TSCG vs Raw, selection, size 50 | Raw | TSCG | 100 | 97.0 | 96.0 | -1.0 [-5.0, +3.0] | -1.0 | 3 / 2 | 1 | 1 | 0.71 [0.14, 3.62] |
| TSCG vs Raw, E2E, size 100 | Raw | TSCG | 100 | 75.0 | 45.0 | -30.0 [-37.0, -23.0] | -40.0 | 33 / 3 | 2.27e-07 | 4.32e-06 | 0.10 [0.03, 0.31] |
| TSCG vs Raw, selection, size 100 | Raw | TSCG | 100 | 92.0 | 92.0 | +0.0 [-6.0, +6.0] | 0.0 | 4 / 4 | 1 | 1 | 1.00 [0.27, 3.69] |
| TSCG vs Raw, E2E, flat targets | Raw | TSCG | 250 | 88.4 | 80.4 | -8.0 [-11.5, -4.5] | -9.0 | 24 / 4 | 0.00018 | 0.00216 | 0.18 [0.07, 0.50] |
| TSCG vs TSCG-info, E2E, flat targets | TSCG-info JSON | TSCG | 250 | 91.6 | 80.4 | -11.2 [-15.4, -6.7] | -12.2 | 30 / 2 | 2.46e-07 | 4.43e-06 | 0.08 [0.02, 0.30] |
| TSCG vs Raw, E2E, structured targets | Raw | TSCG | 250 | 76.4 | 32.8 | -43.6 [-56.7, -29.1] | -57.1 | 115 / 6 | 3.05e-27 | 7.31e-26 | 0.06 [0.03, 0.12] |
| TSCG vs TSCG-info, E2E, structured targets | TSCG-info JSON | TSCG | 250 | 33.2 | 32.8 | -0.4 [-8.2, +6.2] | -1.2 | 13 / 12 | 1 | 1 | 0.93 [0.43, 2.00] |
| ARGGEN: TSCG vs Raw, E2E (tool fixed) | Raw | TSCG | 100 | 84.0 | 62.0 | -22.0 [-32.0, -10.0] | -26.2 | 25 / 3 | 2.74e-05 | 0.000412 | 0.14 [0.04, 0.42] |
| ARGGEN: TSCG vs Raw, arg EM (tool fixed) | Raw | TSCG | 100 | 75.0 | 60.0 | -15.0 [-27.0, -3.0] | -20.0 | 23 / 8 | 0.0107 | 0.117 | 0.36 [0.17, 0.79] |
| ARGGEN: TSCG vs TSCG-info, E2E (tool fixed) | TSCG-info JSON | TSCG | 100 | 65.0 | 62.0 | -3.0 [-8.0, +2.0] | -4.6 | 6 / 3 | 0.508 | 1 | 0.54 [0.15, 1.97] |

## Degradation vs smallest catalog (same tasks, E2E, Holm within arm)

| Representation | first size with significant drop | per-size Δ pp (Holm p) |
|---|---:|---|
| Raw | 20 | 10: -5.0 (0.12); 20: -12.0 (0.0039); 50: -14.0 (0.0039); 100: -17.0 (0.00089) |
| Raw-minified | 100 | 10: -1.0 (1); 20: -7.0 (0.12); 50: -8.0 (0.12); 100: -15.0 (0.006) |
| Normalized | none | 10: +0.0 (1); 20: -5.0 (0.54); 50: -11.0 (0.077); 100: -6.0 (0.54) |
| TSCG | 50 | 10: -1.0 (1); 20: -6.0 (0.062); 50: -11.0 (0.01); 100: -19.0 (8.4e-05) |
| TSCG-info JSON | 100 | 10: -3.0 (0.75); 20: -3.0 (0.75); 50: -8.0 (0.064); 100: -14.0 (0.00049) |

## Does the TSCG − Raw effect change with catalog size? (paired difference-in-differences)

per task: (TSCG - Raw E2E) at size k minus the same at the smallest size; exact sign test on non-zero changes; cluster-bootstrap CI over replicates; Holm across sizes.

| size k | effect at k (pp) | effect at 5 (pp) | DiD (pp) [95% CI] | tasks worse / better | sign-test p | Holm p |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | -24.0 | -28.0 | +4.0 [-2.0, +10.0] | 3 / 7 | 0.344 | 1 |
| 20 | -22.0 | -28.0 | +6.0 [-5.0, +17.0] | 7 / 13 | 0.263 | 1 |
| 50 | -25.0 | -28.0 | +3.0 [-6.0, +12.0] | 9 / 12 | 0.664 | 1 |
| 100 | -30.0 | -28.0 | -2.0 [-13.0, +10.0] | 16 / 14 | 0.856 | 1 |

## Latency — SECONDARY / EXPLORATORY

SECONDARY/EXPLORATORY: uncached sub-run reduced pre-run from 250 to 50 requests (2 fixed tasks per cell); not equivalent to the original design; no inferential claims.

Uncached wall-clock per request (prompt cache disabled). Individual observations and the per-cell median.

| Tools | Representation | n | observations (ms) | median (ms) | median prompt tokens |
|---:|---|---:|---|---:|---:|
| 5 | Raw | 2 | 17359, 14768 | 16063 | 1584 |
| 5 | Raw-minified | 2 | 12750, 10863 | 11807 | 970 |
| 5 | Normalized | 2 | 15997, 13818 | 14908 | 1466 |
| 5 | TSCG | 2 | 9041, 6848 | 7945 | 646 |
| 5 | TSCG-info JSON | 2 | 13218, 11078 | 12148 | 1174 |
| 10 | Raw | 2 | 32358, 28999 | 30679 | 3072 |
| 10 | Raw-minified | 2 | 19506, 16884 | 18195 | 1888 |
| 10 | Normalized | 2 | 29984, 26853 | 28418 | 2902 |
| 10 | TSCG | 2 | 12514, 10568 | 11541 | 1132 |
| 10 | TSCG-info JSON | 2 | 22644, 20130 | 21387 | 2126 |
| 20 | Raw | 2 | 63723, 59539 | 61631 | 5526 |
| 20 | Raw-minified | 2 | 33942, 31205 | 32573 | 3300 |
| 20 | Normalized | 2 | 58599, 54890 | 56745 | 5184 |
| 20 | TSCG | 2 | 19766, 16934 | 18350 | 1870 |
| 20 | TSCG-info JSON | 2 | 38865, 34377 | 36621 | 3626 |
| 50 | Raw | 2 | 207503, 201603 | 204553 | 13040 |
| 50 | Raw-minified | 2 | 97132, 91663 | 94397 | 7678 |
| 50 | Normalized | 2 | 193689, 191087 | 192388 | 12354 |
| 50 | TSCG | 2 | 39903, 38074 | 38989 | 3736 |
| 50 | TSCG-info JSON | 2 | 100667, 100803 | 100735 | 7928 |
| 100 | Raw | 2 | 684104, 665893 | 674998 | 26940 |
| 100 | Raw-minified | 2 | 285672, 278718 | 282195 | 15924 |
| 100 | Normalized | 2 | 626477, 611534 | 619006 | 25626 |
| 100 | TSCG | 2 | 100005, 97838 | 98922 | 7650 |
| 100 | TSCG-info JSON | 2 | 291546, 303011 | 297278 | 16304 |

## Token-count covariate model

E2E ~ log(input tokens) + arm (ref=raw); logit; cluster-robust SE by intent

| term | coef | SE | p |
|---|---:|---:|---:|
| const | +3.946 | 0.677 | 5.68e-09 |
| log_input_tokens | -0.272 | 0.068 | 5.55e-05 |
| arm[minified] | -0.112 | 0.126 | 0.375 |
| arm[normalized] | -0.000 | 0.067 | 0.999 |
| arm[tscg] | -1.628 | 0.234 | 3.08e-12 |
| arm[tscg_info] | -1.186 | 0.246 | 1.46e-06 |

## Primary failure categories (selection family, all sizes)

| Failure | Raw | Raw-minified | Normalized | TSCG | TSCG-info JSON |
|---|---:|---:|---:|---:|---:|
| wrong tool | 8 | 2 | 5 | 11 | 8 |
| multiple-tool confusion | 0 | 0 | 0 | 0 | 0 |
| correct tool, wrong argument | 42 | 50 | 44 | 53 | 35 |
| missing required argument | 11 | 19 | 9 | 56 | 47 |
| invalid argument type | 7 | 0 | 11 | 71 | 65 |
| invalid enum/value | 0 | 0 | 0 | 2 | 10 |
| hallucinated field | 0 | 0 | 0 | 10 | 8 |
| ignored schema constraint | 9 | 8 | 7 | 10 | 13 |
| context-length failure | 0 | 0 | 0 | 0 | 0 |
| malformed output | 11 | 7 | 11 | 4 | 2 |
| execution failure | 0 | 0 | 0 | 0 | 0 |
| semantic/task failure | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 0 |
