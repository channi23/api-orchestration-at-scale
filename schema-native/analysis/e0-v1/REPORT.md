# Report — run `e0-v1`

Evidence kind: benchmark. Status: PARTIAL: no paired inference. Requests: 588/1200. Infrastructure failures: 120. Evaluation is against the raw schema. Engine refusals are counted separately from model errors.

Cached sequential latency is descriptive. Taxonomy excludes request failures. p99 appears in JSON only for cells with at least 200 responses.

| Family | Tools | Arm | n | Tool % | Schema valid % | Semantic % | E2E % | E2E % (engine ok) | Engine errors | malformed | wrong tool | invalid only | invalid+wrong | valid, wrong | In tok | Out tok | p50 ms | p95 ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| select | 5 | A_raw_free | 80 | 96.2 | 95.0 | 90.0 | 90.0 | 90.0 | 0 | 3 | 0 | 0 | 1 | 4 | 1501 | 61 | 1257 | 2772 |
| select | 5 | B_raw_cd | 80 | 91.2 | 90.0 | 77.5 | 57.5 | 76.7 | 20 | 5 | 0 | 0 | 0 | 9 | 1501 | 90 | 1263 | 11228 |
| select | 5 | A2_min_free | 78 | 98.7 | 93.6 | 85.9 | 85.9 | 85.9 | 0 | 1 | 0 | 0 | 4 | 6 | 921 | 55 | 1279 | 2351 |
| select | 5 | B2_min_cd | 70 | 87.1 | 85.7 | 71.4 | 47.1 | 66.0 | 20 | 8 | 0 | 0 | 0 | 9 | 905 | 107 | 1082 | 10987 |
| select | 20 | A_raw_free | 70 | 100.0 | 91.4 | 81.4 | 80.0 | 80.0 | 0 | 0 | 0 | 1 | 5 | 8 | 5599 | 56 | 1594 | 8645 |
| select | 20 | B_raw_cd | 70 | 94.3 | 90.0 | 77.1 | 31.4 | 73.3 | 40 | 4 | 0 | 0 | 0 | 4 | 5599 | 81 | 1273 | 15058 |
| select | 20 | A2_min_free | 70 | 98.6 | 90.0 | 84.3 | 84.3 | 84.3 | 0 | 1 | 0 | 0 | 6 | 4 | 3333 | 53 | 1354 | 5062 |
| select | 20 | B2_min_cd | 70 | 95.7 | 91.4 | 78.6 | 31.4 | 73.3 | 40 | 2 | 0 | 0 | 0 | 6 | 3333 | 67 | 1130 | 12413 |

## Exact and field metrics

| Family | Tools | Arm | Argument exact match % | Field accuracy % | Strict E2E % |
|---|---:|---|---:|---:|---:|
| select | 5 | A_raw_free | 76.2 | 94.2 | 77.5 |
| select | 5 | B_raw_cd | 66.2 | 86.2 | 47.5 |
| select | 5 | A2_min_free | 78.2 | 94.7 | 79.5 |
| select | 5 | B2_min_cd | 65.7 | 81.6 | 42.9 |
| select | 20 | A_raw_free | 72.9 | 93.8 | 74.3 |
| select | 20 | B_raw_cd | 70.0 | 88.3 | 27.1 |
| select | 20 | A2_min_free | 78.6 | 93.2 | 80.0 |
| select | 20 | B2_min_cd | 72.9 | 88.9 | 27.1 |

## Request failures and truncation

| Family | Tools | Arm | Request errors by kind | Truncated outputs |
|---|---:|---|---|---:|
| select | 5 | A_raw_free | {} | 1 |
| select | 5 | B_raw_cd | {"engine_error": 20} | 6 |
| select | 5 | A2_min_free | {} | 0 |
| select | 5 | B2_min_cd | {"engine_error": 20} | 8 |
| select | 20 | A_raw_free | {} | 0 |
| select | 20 | B_raw_cd | {"engine_error": 40} | 4 |
| select | 20 | A2_min_free | {} | 0 |
| select | 20 | B2_min_cd | {"engine_error": 40} | 2 |

Server peak RSS: 3907026944 bytes. See JSON memory_note for scope.

E1 remains gated on a complete, infrastructure-clean E0 readout, inspection of engine errors, and unseen-schema v2/stress tasks. E2 is deferred until those datasets exist.
