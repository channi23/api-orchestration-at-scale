# Report — run `e0-clean-v1`

Evidence kind: benchmark. Status: COMPLETE. Requests: 1200/1200. Infrastructure failures: 0. Evaluation is against the raw schema. Engine refusals are counted separately from model errors.

Cached sequential latency is descriptive. Taxonomy excludes request failures. p99 appears in JSON only for cells with at least 200 responses.

| Family | Tools | Arm | n | Tool % | Schema valid % | Semantic % | E2E % | E2E % (engine ok) | Engine errors | CD truncated | malformed | wrong tool | invalid only | invalid+wrong | valid, wrong | In tok | Out tok | p50 ms | p95 ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| select | 5 | A_raw_free | 100 | 97.0 | 96.0 | 91.0 | 91.0 | 91.0 | 0 | 0 | 3 | 0 | 0 | 1 | 5 | 1498 | 60 | 1299 | 2774 |
| select | 5 | B_raw_cd | 100 | 86.0 | 86.0 | 76.0 | 76.0 | 76.0 | 0 | 14 | 0 | 0 | 0 | 0 | 10 | 1498 | 119 | 1363 | 11560 |
| select | 5 | A2_min_free | 100 | 99.0 | 95.0 | 88.0 | 88.0 | 88.0 | 0 | 0 | 1 | 0 | 0 | 4 | 7 | 925 | 55 | 1248 | 2295 |
| select | 5 | B2_min_cd | 100 | 84.0 | 84.0 | 74.0 | 74.0 | 74.0 | 0 | 16 | 0 | 0 | 0 | 0 | 10 | 925 | 128 | 1299 | 11179 |
| select | 20 | A_raw_free | 100 | 97.0 | 90.0 | 81.0 | 80.0 | 80.0 | 0 | 0 | 3 | 0 | 1 | 6 | 10 | 5639 | 57 | 1612 | 8181 |
| select | 20 | B_raw_cd | 100 | 83.0 | 83.0 | 65.0 | 65.0 | 65.0 | 0 | 17 | 0 | 0 | 0 | 0 | 18 | 5639 | 133 | 1739 | 14226 |
| select | 20 | A2_min_free | 100 | 97.0 | 91.0 | 84.0 | 84.0 | 84.0 | 0 | 0 | 3 | 0 | 0 | 6 | 7 | 3358 | 54 | 1429 | 4921 |
| select | 20 | B2_min_cd | 100 | 85.0 | 85.0 | 65.0 | 65.0 | 65.0 | 0 | 15 | 0 | 0 | 0 | 0 | 20 | 3358 | 123 | 1553 | 12913 |
| arggen | 1 | A_raw_free | 100 | 94.0 | 90.0 | 87.0 | 85.0 | 85.0 | 0 | 0 | 6 | 0 | 2 | 2 | 5 | 399 | 55 | 1245 | 2254 |
| arggen | 1 | B_raw_cd | 100 | 83.0 | 83.0 | 70.0 | 70.0 | 70.0 | 0 | 17 | 0 | 0 | 0 | 0 | 13 | 399 | 133 | 1429 | 10664 |
| arggen | 1 | A2_min_free | 100 | 97.0 | 93.0 | 87.0 | 87.0 | 87.0 | 0 | 0 | 3 | 0 | 0 | 4 | 6 | 285 | 56 | 1191 | 2156 |
| arggen | 1 | B2_min_cd | 100 | 84.0 | 84.0 | 73.0 | 73.0 | 73.0 | 0 | 16 | 0 | 0 | 0 | 0 | 11 | 285 | 128 | 1274 | 10475 |

## Paired comparisons (B − A, E2E)

| Comparison | Family | A | B | pairs | A % | B % | Δ pp [95% CI] | A-only / B-only | p (exact) | p (Holm) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| PRIMARY: constrained vs free, raw (tools=pooled) | select | A_raw_free | B_raw_cd | 200 | 85.5 | 70.5 | -15.0 [-25.5, -5.0] | 37 / 7 | 5.3e-06 | primary |
| PRIMARY: constrained vs free, raw (tools=5) | select | A_raw_free | B_raw_cd | 100 | 91.0 | 76.0 | -15.0 [-27.0, -4.0] | 18 / 3 | 0.00149 | 0.0194 |
| PRIMARY: constrained vs free, raw (tools=20) | select | A_raw_free | B_raw_cd | 100 | 80.0 | 65.0 | -15.0 [-25.0, -4.0] | 19 / 4 | 0.0026 | 0.0309 |
| PRIMARY: constrained vs free, raw (tools=1) | arggen | A_raw_free | B_raw_cd | 100 | 85.0 | 70.0 | -15.0 [-23.0, -8.0] | 21 / 6 | 0.00592 | 0.0592 |
| constrained vs free, minified (tools=pooled) | select | A2_min_free | B2_min_cd | 200 | 86.0 | 69.5 | -16.5 [-25.0, -9.0] | 39 / 6 | 5.42e-07 | 8.13e-06 |
| constrained vs free, minified (tools=5) | select | A2_min_free | B2_min_cd | 100 | 88.0 | 74.0 | -14.0 [-22.0, -6.0] | 17 / 3 | 0.00258 | 0.0309 |
| constrained vs free, minified (tools=20) | select | A2_min_free | B2_min_cd | 100 | 84.0 | 65.0 | -19.0 [-28.0, -12.0] | 22 / 3 | 0.000157 | 0.00219 |
| constrained vs free, minified (tools=1) | arggen | A2_min_free | B2_min_cd | 100 | 87.0 | 73.0 | -14.0 [-25.0, -3.0] | 19 / 5 | 0.00661 | 0.0595 |
| minified vs raw, free (replication of the finished experiment) (tools=pooled) | select | A_raw_free | A2_min_free | 200 | 85.5 | 86.0 | +0.5 [-3.0, +3.5] | 8 / 9 | 1 | 1 |
| minified vs raw, free (replication of the finished experiment) (tools=5) | select | A_raw_free | A2_min_free | 100 | 91.0 | 88.0 | -3.0 [-10.0, +2.0] | 6 / 3 | 0.508 | 1 |
| minified vs raw, free (replication of the finished experiment) (tools=20) | select | A_raw_free | A2_min_free | 100 | 80.0 | 84.0 | +4.0 [+0.0, +9.0] | 2 / 6 | 0.289 | 1 |
| minified vs raw, free (replication of the finished experiment) (tools=1) | arggen | A_raw_free | A2_min_free | 100 | 85.0 | 87.0 | +2.0 [-4.0, +8.0] | 5 / 7 | 0.774 | 1 |
| minified vs raw, constrained (tools=pooled) | select | B_raw_cd | B2_min_cd | 200 | 70.5 | 69.5 | -1.0 [-5.0, +2.5] | 8 / 6 | 0.791 | 1 |
| minified vs raw, constrained (tools=5) | select | B_raw_cd | B2_min_cd | 100 | 76.0 | 74.0 | -2.0 [-8.0, +3.0] | 4 / 2 | 0.688 | 1 |
| minified vs raw, constrained (tools=20) | select | B_raw_cd | B2_min_cd | 100 | 65.0 | 65.0 | +0.0 [-4.0, +4.0] | 4 / 4 | 1 | 1 |
| minified vs raw, constrained (tools=1) | arggen | B_raw_cd | B2_min_cd | 100 | 70.0 | 73.0 | +3.0 [-6.0, +11.0] | 4 / 7 | 0.549 | 1 |

## Exact and field metrics

| Family | Tools | Arm | Argument exact match % | Field accuracy % | Strict E2E % |
|---|---:|---|---:|---:|---:|
| select | 5 | A_raw_free | 78.0 | 95.2 | 79.0 |
| select | 5 | B_raw_cd | 67.0 | 82.6 | 67.0 |
| select | 5 | A2_min_free | 82.0 | 95.7 | 83.0 |
| select | 5 | B2_min_cd | 68.0 | 80.8 | 68.0 |
| select | 20 | A_raw_free | 72.0 | 91.9 | 73.0 |
| select | 20 | B_raw_cd | 59.0 | 77.1 | 60.0 |
| select | 20 | A2_min_free | 80.0 | 92.7 | 81.0 |
| select | 20 | B2_min_cd | 62.0 | 77.4 | 62.0 |
| arggen | 1 | A_raw_free | 76.0 | 91.4 | 78.0 |
| arggen | 1 | B_raw_cd | 62.0 | 76.7 | 63.0 |
| arggen | 1 | A2_min_free | 81.0 | 94.3 | 82.0 |
| arggen | 1 | B2_min_cd | 64.0 | 79.8 | 65.0 |

## Request failures and truncation

| Family | Tools | Arm | Request errors by kind | Truncated outputs |
|---|---:|---|---|---:|
| select | 5 | A_raw_free | {} | 1 |
| select | 5 | B_raw_cd | {} | 14 |
| select | 5 | A2_min_free | {} | 0 |
| select | 5 | B2_min_cd | {} | 16 |
| select | 20 | A_raw_free | {} | 0 |
| select | 20 | B_raw_cd | {} | 17 |
| select | 20 | A2_min_free | {} | 0 |
| select | 20 | B2_min_cd | {} | 15 |
| arggen | 1 | A_raw_free | {} | 0 |
| arggen | 1 | B_raw_cd | {} | 17 |
| arggen | 1 | A2_min_free | {} | 0 |
| arggen | 1 | B2_min_cd | {} | 16 |

## Truncation sensitivity (descriptive only)

The primary comparison above includes every pair. The subset below conditions on both outputs finishing; it is biased by output behavior and is not a causal estimate.

| Comparison | Family | Tools | A truncated | B truncated | Both finished pairs | A E2E % | B E2E % |
|---|---|---:|---:|---:|---:|---:|---:|
| PRIMARY: constrained vs free, raw | select | pooled | 1 | 31 | 168 | 87.5 | 83.3 |
| PRIMARY: constrained vs free, raw | select | 5 | 1 | 14 | 85 | 91.8 | 88.2 |
| PRIMARY: constrained vs free, raw | select | 20 | 0 | 17 | 83 | 83.1 | 78.3 |
| PRIMARY: constrained vs free, raw | arggen | 1 | 0 | 17 | 83 | 88.0 | 84.3 |
| constrained vs free, minified | select | pooled | 0 | 31 | 169 | 85.8 | 82.2 |
| constrained vs free, minified | select | 5 | 0 | 16 | 84 | 89.3 | 88.1 |
| constrained vs free, minified | select | 20 | 0 | 15 | 85 | 82.4 | 76.5 |
| constrained vs free, minified | arggen | 1 | 0 | 16 | 84 | 88.1 | 86.9 |
| minified vs raw, free (replication of the finished experiment) | select | pooled | 1 | 0 | 199 | 85.4 | 86.4 |
| minified vs raw, free (replication of the finished experiment) | select | 5 | 1 | 0 | 99 | 90.9 | 88.9 |
| minified vs raw, free (replication of the finished experiment) | select | 20 | 0 | 0 | 100 | 80.0 | 84.0 |
| minified vs raw, free (replication of the finished experiment) | arggen | 1 | 0 | 0 | 100 | 85.0 | 87.0 |
| minified vs raw, constrained | select | pooled | 31 | 31 | 159 | 87.4 | 83.6 |
| minified vs raw, constrained | select | 5 | 14 | 16 | 82 | 91.5 | 87.8 |
| minified vs raw, constrained | select | 20 | 17 | 15 | 77 | 83.1 | 79.2 |
| minified vs raw, constrained | arggen | 1 | 17 | 16 | 77 | 87.0 | 88.3 |

## Post-hoc exact-engine key-order audit

Strict-contract JSON checked: 501/515 free-correct outputs. Remaining outputs are excluded from this diagnostic, not from benchmark accuracy. Byte-token reachability is not model-token sampling or causal proof.

| Free output category | Constrained correct | Constrained wrong | Constrained truncated |
|---|---:|---:|---:|
| accepted_original_order | 249 | 0 | 0 |
| order_only_rejection | 140 | 40 | 72 |
| other_rejection | 0 | 0 | 0 |

Server peak RSS: 2980265984 bytes. See JSON memory_note for scope.

E1 remains gated on a complete, infrastructure-clean E0 readout, inspection of engine errors, and unseen-schema v2/stress tasks. E2 is deferred until those datasets exist.
