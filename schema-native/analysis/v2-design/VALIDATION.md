# v2 design verification

**2026-11-25. Model-free design delivery on docs/v2-benchmark-design.**
Base: main `778c1c1e11c14867b4ed3e3c1cbf8acd3353f0a6`.
Scope: [V2_DESIGN.md](../../V2_DESIGN.md), sample-size planning and its tests. No v2 tasks were authored.

## Verified

- Issue #6 and its existing attachment comment were read. The issue remains open for design review.
- Published E0b `results.jsonl.gz` SHA-256 is
  `d7baf37717a16b87d1d69a0bde6e363ad658bc5ac387c3853dd2498431f9e686`.
  Its uncompressed SHA-256 matches publication:
  `b439a463e53cae55fa38cd1a62399332602fd97b2d779e28195120e99c5baf90`.
- There are 1,562 saved records: 1,500 final arm rows, 30 determinism records and 32 retry records.
  The planning code matches final keys exactly, excluding controls/retries rather than treating
  all same-arm records as extra samples. Both audited contrasts contain 200 final select units,
  50 intents and four observations per intent.
- Stored scores reproduce C2−C1's 37 improvements/one regression and V−F0's five improvements/no
  regressions. No raw output is re-parsed or rescored. These are the historical evaluator's outcomes,
  not newly evaluated v2 outcomes. Existing reports, decisions and confidence intervals are unchanged.
- The pool has 300 tools and v1 targets 50 distinct tools, leaving 250 candidate target tools;
  independence, provenance and eligibility of those 250 have **not** been established.
- Independent-pair normal approximation: for a true five-point effect, q=.20, 80% target power,
  approximate n is 626 at two-sided alpha .05 and 758 at alpha .025. The full q/effect grid and
  explicitly conditional whole-intent simulations are in power.json. Proposed n=800 is provisional.
- The external stress-fixtures-0.4.zip SHA-256 matches
  `8bb8ab2ac1553bf7bc3ae068e615e23d776ddb0a8c2550d4cde82e206fad1132`.
  Its README was read to preserve its example-only status and limitations. No archive code was
  executed or copied, and no optional engine library was installed or invoked for this design.
- All tracked `experiment/`, E0/E0b publications, model configs, runtime code and scripts are unchanged
  relative to the base. Existing untracked duplicate files were not staged, modified or removed.

## Checks and exact commands

Run from the repository root unless noted:

```bash
python3 schema-native/analysis/v2-design/power.py --check
python3 -m unittest discover -s schema-native/analysis/v2-design -p test_power.py -v
schema-native/.venv/bin/python -m pytest -q experiment/tests/test_evaluate.py
git diff --check
```

The tracked package suite was run from schema-native/ using a Python subprocess argument list,
so untracked files with duplicate names are not accidentally collected:

```python
import subprocess
files = subprocess.check_output(
    ["git", "ls-files", "tests/test_*.py"], text=True
).splitlines()
raise SystemExit(subprocess.call([".venv/bin/python", "-m", "pytest", "-q", *files]))
```

**178 tests pass:** 158 existing package tests, 12 original evaluator tests, eight new standalone
planning tests. The new tests cover duplicate/control exclusion, strict pair alignment, whole-intent
aggregation without score mutation, rejection of unbalanced clusters, formula values and invalid
assumptions, and seeded simulations. Generated power artifacts reproduce byte-for-byte with --check.
No dependency install was required.

## Not verified and next gate

- No larger held-out dataset exists yet. No new API source, licence audit, family graph, independent
  gold review, source holdout, renamed variant, or candidate-task difficulty has been verified.
- The sensitivity calculation does not establish power under future family correlations, nor does
  resampling four gain-bearing pilot intents predict future training gains. Exact/hierarchical
  power calibration and false-positive checks are deferred to a separately approved development plan.
- No new engine capability, live endpoint, native build, request grammar, model behavior or resource
  profile was tested. Existing PyPI stress-engine findings were not reproduced.
- No inference, model loading, weight edit, training, cost comparison or training-data generation
  occurred. No old campaign was resumed and no saved request charge was changed.

**Stop at design review.** Task authoring, dataset implementation, a development pilot and any
E1/E2 or cost campaign require later scope and explicit authorization. The PR proposes a design;
it does not make the benchmark launch-ready or close issue #6 as implemented.
