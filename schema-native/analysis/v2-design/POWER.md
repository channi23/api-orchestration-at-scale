# v2 sample-size planning

**Design only, 2026-11-25. No inference, training or rescoring.**

Reproduce: `python schema-native/analysis/v2-design/power.py --check`.

## Published-row audit

Each contrast has 200 select rows but only 50 intent clusters, with four rows per intent.

| Contrast | B-only correct | A-only correct | Difference | Descriptive design effect |
| --- | ---: | ---: | ---: | ---: |
| C2 − C1 | 37 | 1 | 18.0 pp | 3.095 |
| V − F0 | 5 | 0 | 2.5 pp | 1.354 |

Design effect compares variance of the equal-weight intent mean with a naive row-independent mean; it is descriptive, not an inflation factor transferable to v2.

## Independent-pair sensitivity: a true 5-point improvement

Two-sided normal approximation, 80% target power against zero; q is the assumed fraction of discordant independent binary pairs.
Alpha .025 is a conservative first-step threshold for two Holm tests, not a change to historical multiplicity.

| Assumed q | n at alpha .05 | n at alpha .025 |
| --- | ---: | ---: |
| 0.05 | 155 | 188 |
| 0.10 | 312 | 378 |
| 0.19 | 595 | 720 |
| 0.20 | 626 | 758 |
| 0.30 | 940 | 1139 |

For D∈{−1,0,+1}, E[D]=δ and Var[D]=q−δ²:

`n ≈ ceil((z_(1−alpha/2) sqrt(q) + z_.8 sqrt(q−δ²))² / δ²)`.

The JSON also contains 3/8-point scenarios and whole-intent resampling simulations. Those simulations preserve the observed four-row dependence by sampling intent means; they estimate detecting the observed effect under a normal z rule. They do not predict a future training gain or validate the planned family/intent bootstrap.

## Planning consequence

The 250 unused tools are an authoring seed, not a sufficient independent test-set guarantee. Propose 800 locked-test intents plus 200 development intents, subject to provenance and family audits. At q=.20, a single 5-point binary-pair contrast needs approximately 626 independent pairs; a conservative two-test threshold needs 758. At q=.30 even 800 may be insufficient (940/1,139).

Do not multiply paraphrases, two catalog sizes, pair members, or renamed schemas into the independent n. Recompute power using development-set cluster sizes and variance before freezing any campaign. No current dataset or campaign is launch-ready.

## Limits

- Only 50 observed independent intents; no family-level sampling frame.
- The order contrast cannot predict a semantic training effect.
- Row discordance is not independent-intent discordance.
- Simulations use observed intent effects and a normal z rule, not the proposed hierarchical analysis.
- Only four pilot intents show V gains; resampling cannot create unseen regressions and may be optimistic. Do not size v2 from that simulation.
- 800 test intents is a provisional authoring target, not guaranteed power.
- A 5-point effect scenario does not power a 5-point threshold at 80% if the true effect is exactly 5 points.

Source uncompressed SHA-256: `b439a463e53cae55fa38cd1a62399332602fd97b2d779e28195120e99c5baf90`.
