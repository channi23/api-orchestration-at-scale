# What constrained decoding could fix — run `full-v2`

Computed from the stored outputs of the finished run. No model was called.

- **CD conservative**: success if only the failures that already had every requested value right become successes.
- **CD upper bound**: success if every malformed or schema-invalid output becomes a success. This assumes the engine is sound and complete and that forcing validity never changes a correct answer.
- **valid, wrong value** outputs already satisfy the raw schema. A grammar cannot change them.

## Arm: raw

| Slice | n | E2E % | malformed | wrong tool | invalid only | invalid + wrong value | valid, wrong value | CD conservative % | CD upper bound % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| select, all sizes | 500 | 82.4 | 11 | 8 | 3 | 24 | 42 | 83.0 | 90.0 |
| select, 5 tools | 100 | 92.0 | 3 | 0 | 0 | 1 | 4 | 92.0 | 96.0 |
| select, 10 tools | 100 | 87.0 | 2 | 0 | 2 | 5 | 4 | 89.0 | 96.0 |
| select, 20 tools | 100 | 80.0 | 3 | 0 | 1 | 6 | 10 | 81.0 | 90.0 |
| select, 50 tools | 100 | 78.0 | 1 | 2 | 0 | 7 | 12 | 78.0 | 86.0 |
| select, 100 tools | 100 | 75.0 | 2 | 6 | 0 | 5 | 12 | 75.0 | 82.0 |
| select, flat targets | 250 | 88.4 | 0 | 2 | 0 | 4 | 23 | 88.4 | 90.0 |
| select, structured targets | 250 | 76.4 | 11 | 6 | 3 | 20 | 19 | 77.6 | 90.0 |
| arggen (tool fixed) | 100 | 84.0 | 5 | 0 | 2 | 3 | 6 | 86.0 | 94.0 |

Clustering: 50 target tools, intra-tool correlation 0.44, design effect 4.9, effective sample size 102 of 500. 24 tools have at least one failure; the 5 worst tools hold 47% of all failures.

## Arm: minified

| Slice | n | E2E % | malformed | wrong tool | invalid only | invalid + wrong value | valid, wrong value | CD conservative % | CD upper bound % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| select, all sizes | 500 | 82.8 | 7 | 2 | 0 | 27 | 50 | 82.8 | 89.6 |
| select, 5 tools | 100 | 89.0 | 1 | 0 | 0 | 3 | 7 | 89.0 | 93.0 |
| select, 10 tools | 100 | 88.0 | 1 | 0 | 0 | 4 | 7 | 88.0 | 93.0 |
| select, 20 tools | 100 | 82.0 | 4 | 0 | 0 | 5 | 9 | 82.0 | 91.0 |
| select, 50 tools | 100 | 81.0 | 0 | 0 | 0 | 8 | 11 | 81.0 | 89.0 |
| select, 100 tools | 100 | 74.0 | 1 | 2 | 0 | 7 | 16 | 74.0 | 82.0 |
| select, flat targets | 250 | 85.6 | 0 | 1 | 0 | 6 | 29 | 85.6 | 88.0 |
| select, structured targets | 250 | 80.0 | 7 | 1 | 0 | 21 | 21 | 80.0 | 91.2 |
| arggen (tool fixed) | 100 | 86.0 | 4 | 0 | 0 | 4 | 6 | 86.0 | 94.0 |

Clustering: 50 target tools, intra-tool correlation 0.49, design effect 5.4, effective sample size 93 of 500. 22 tools have at least one failure; the 5 worst tools hold 50% of all failures.

## Arm: normalized

| Slice | n | E2E % | malformed | wrong tool | invalid only | invalid + wrong value | valid, wrong value | CD conservative % | CD upper bound % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| select, all sizes | 500 | 82.6 | 11 | 5 | 5 | 22 | 44 | 83.6 | 90.2 |
| select, 5 tools | 100 | 87.0 | 4 | 0 | 1 | 1 | 7 | 88.0 | 93.0 |
| select, 10 tools | 100 | 87.0 | 2 | 0 | 3 | 5 | 3 | 90.0 | 97.0 |
| select, 20 tools | 100 | 82.0 | 2 | 0 | 0 | 7 | 9 | 82.0 | 91.0 |
| select, 50 tools | 100 | 76.0 | 2 | 1 | 1 | 5 | 15 | 77.0 | 84.0 |
| select, 100 tools | 100 | 81.0 | 1 | 4 | 0 | 4 | 10 | 81.0 | 86.0 |
| select, flat targets | 250 | 88.4 | 0 | 1 | 0 | 6 | 22 | 88.4 | 90.8 |
| select, structured targets | 250 | 76.8 | 11 | 4 | 5 | 16 | 22 | 78.8 | 89.6 |
| arggen (tool fixed) | 100 | 85.0 | 4 | 0 | 0 | 2 | 9 | 85.0 | 91.0 |

Clustering: 50 target tools, intra-tool correlation 0.45, design effect 5.1, effective sample size 99 of 500. 23 tools have at least one failure; the 5 worst tools hold 47% of all failures.

## Power of a paired comparison

Pairs needed for 80% power at two-sided 5% (McNemar, normal approximation). 'Requests at measured design effect' inflates this by the clustering measured above, which applies if the extra requests reuse the same 50 target tools. New, independent target tools do not pay that penalty.

| Difference to detect (pp) | Discordant share | Independent pairs | Requests at measured design effect |
|---:|---:|---:|---:|
| 3 | 0.10 | 869 | 4275 |
| 3 | 0.20 | 1740 | 8561 |
| 5 | 0.10 | 312 | 1532 |
| 5 | 0.20 | 625 | 3075 |
| 8 | 0.10 | 121 | 592 |
| 8 | 0.20 | 243 | 1194 |
| 10 | 0.10 | 77 | 374 |
| 10 | 0.20 | 155 | 760 |
