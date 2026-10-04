# Decision log (representation-v1)

## Approved by the user (2026-10-04)
- Compact model: Qwen3-1.7B run locally. No Claude or Haiku reproduction.
- TSCG `conservative` profile, fixed for every catalog size.
- Tool names, descriptions and tasks are created once, frozen and versioned.
- **5 arms:** raw, raw-minified, normalized, TSCG, TSCG-information JSON control (chosen over a 4-arm option).
- **100 tasks in total**, each evaluated at all catalog sizes (the paired design), chosen over 100 tasks per catalog.
- Catalog sizes 5/10/20/50/100, 10 replicates, pilot first.

## Pre-run methodological decisions (approved by the user before the full run, 2026-10-04)
- **Latency sub-run reduced from 250 to 50 requests.**
  - *Original plan:* uncached latency for replicate 0, paraphrase 0, all 10 tasks per cell: 5 sizes × 5 representations × 10 tasks = 250 requests.
  - *New design:* 2 fixed tasks per catalog-size × representation cell (`T106_p0` flat, `T103_p0` structured), i.e. 5 × 5 × 2 = **50 requests** (`config/runs/latency.json`).
  - *Reason:* latency is a secondary metric. Uncached latency is nearly deterministic for a fixed prompt length (prefill dominates; measured 132 tok/s prefill, 14 tok/s decode). The reduced design still covers every catalog-size × representation cell, and cuts estimated runtime from about 5–6 h to about 1.5 h (a 100-tool raw prompt is about 28k tokens, roughly 5 min uncached).
  - *Reporting consequence:* latency is reported as individual observations plus the median per cell, and labelled **secondary/exploratory**. It is not equivalent to the original 250-request design and is not used for inferential claims.
  - Nothing else changed: the 3,000-request cached full run, the primary metric (E2E) and all other metrics are as planned.
- **Pilot outcome (pilot-v1, 300 requests; pilot-uncached-v1, 50 requests).**
  - The pipeline was validated end to end.
  - Determinism (cached vs uncached prompt evaluation, same 50 requests): **48/50 outputs byte-identical; 50/50 identical E2E outcomes.** The 2 differing outputs differ only in an unrequested free-text value and in a field that fails either way.
- **Pilot-driven fixes (before the full run).**
  - Tasks v1.1: T151 paraphrase 1 quotes the description. In v1, the next sentence could legitimately be read as part of it.
  - A secondary metric, E2E-strict, was added: E2E plus no invented non-empty values in unrequested fields. Re-scoring the pilot left primary E2E unchanged in all 300 rows.

## Implementation choices within the approved plan (flagged for review)
1. **Size cap 2,500 → 1,500 pretty-printed chars.**
   - The plan set the cap so that 100 raw tools fit the 32k context.
   - Measured with the Qwen BPE vocabulary (`qwen.tiktoken` from the dashscope wheel, used only as a planning estimate), a 2,000-char cap already reaches about 30k tokens for 100 tools.
   - 1,500 gives an estimated maximum of about 27k. The real tokenizer re-checks this before the full run (`src/count_tokens.py`).
2. **Plausibility review of candidate schemas.**
   - Many eligible schemas are test or toy schemas, opaque fragments, or system responses. A natural-language task cannot be written for them unambiguously.
   - Candidates are reviewed strictly in seeded rank order. Each gets a recorded decision code (OPAQUE, TOY, NO_USER_VALUES, SEMANTIC_DUPLICATE, PII).
   - 631 candidates were reviewed to reach 300 accepted tools.
3. **Function families.** Tools with overlapping purposes are either rejected (SEMANTIC_DUPLICATE) or share a family label. A catalog holds at most one tool per family, so the correct tool stays unambiguous.
4. **Paraphrases.** Each target has 2 paraphrases with **the same** gold arguments, following the brief's "paraphrases of the same intent". Statistics treat the paired task as the unit, and the cluster bootstrap resamples replicates.
5. **Tool order.** Presentation order is a seeded shuffle per (replicate, size), identical across arms. Under `conservative`, TSCG does not reorder tools (verified).
6. **TSCG invocation.** The official package is applied per tool and joined with blank lines. For all 50 catalogs this was verified byte-identical to `compress(catalog)`.
7. **TSCG-information control.** Built from the official `compressDescriptions()` output (SDM-rewritten descriptions), keeping exactly the fields `normalizeToInternal` keeps. A missing type becomes `"string"`, as in TSCG.
8. **Format assertion.** JSON Schema `format` is treated as an annotation and not asserted, as the spec's default. Upstream also renamed many `format` keys to `_format`.
9. **Output contract.** Every arm puts the catalog in the system prompt and asks for `{"tool":…, "arguments":…}`. The native tool-calling API is not used, because it only accepts JSON Schema and would make the conditions differ.
   - The parser accepts code fences and common key aliases. It records when it used them (`json_strict`, `format_alias_used`).
10. **Semantic comparison.**
    - Strings: casefold and whitespace-normalized.
    - Numbers: numeric equality. Enums and booleans: exact.
    - Arrays: unordered only where declared.
    - Cross-type scalars count as semantically equal for **field accuracy** (`"300"` ≈ `300`), but such outputs still fail **schema validity**, and therefore E2E.
11. **E2E with single-call mocks.** E2E reduces to: JSON valid ∧ correct tool ∧ schema-valid ∧ semantically correct arguments. The mock adds no independent semantic oracle; this is stated in the report.
12. **Latency.** The main runs use llama.cpp prompt-prefix caching (the catalog is shared across a cell's tasks), which makes them CPU-feasible. Latency is reported from a separate uncached sub-run. The pilot checks that cached and uncached greedy outputs are identical.

## Known confounders recorded up front
- TSCG removes information for structured schemas (`representations/tscg/information_audit.v1.summary.json`):
  - 117 of 126 structured tools lose sub-structure;
  - 14 tools have types shown incorrectly;
  - 140 of 300 tools lose constraints;
  - SDM rewrites parameter descriptions for 114 tools.
- Tool names and descriptions are written by the experimenter (identical across arms). They affect absolute accuracy and external validity, not the paired contrast.
- This benchmark consists of real schemas with generated tasks and generated mocks. It is **not** a real API workload.
- One model and one tokenizer, so no cross-model claim is possible.
- Some raw schemas include `$id` URLs or example values (part of "raw" by definition). The task prompts were audited so they don't reuse those example values (T106 was fixed).
