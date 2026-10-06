# What we learned, what is new, and what to do next

*Companion to the representation experiment v1. The authoritative numbers are in
[`analysis/full-v2/REPORT.md`](analysis/full-v2/REPORT.md) and `results.json`. Every number quoted here is copied
from that report. Statements marked **(interpretation)** or **(proposal)** are not measured results.*

---

## 1. What we got (in one page)

**The question.** Does the *format* of tool schemas change how well a small model uses tools, when nothing else changes?

**The setup.**
- One model: Qwen3-1.7B, run locally with greedy decoding.
- 300 tools built from real JSONSchemaBench schemas.
- 100 frozen tasks.
- 5 representations: Raw, Raw-minified, Normalized, TSCG, and TSCG-info JSON.
- 5 catalog sizes (5–100 tools) × 10 catalog replicates.
- 3,000 paired requests, with every task scored under every condition.

**The answers.**

| Question | Answer (observed) |
|---|---|
| Does format change tool use at all? | **Yes, a lot.** E2E success ranged from 82–83% (Raw, Raw-minified, Normalized) down to 56.6% (TSCG). |
| Does TSCG help this model? | **No. It hurts.** Raw 82.4% vs TSCG 56.6%: −25.8 pp, 95% CI [−32.8, −18.2], p = 3.3e-30. |
| Does it affect choosing the tool? | **No.** Pooled selection was 96.2–98.2% in every format. The damage is in the **arguments**. |
| Is token count the cause? | **No.** Raw-minified had about 40% fewer tokens than Raw and the same success rate (+0.4 pp, n.s.). |
| What is the cause, then? | **Mostly missing information**, plus a smaller format effect. TSCG-info vs Raw: −20.0 pp. TSCG vs TSCG-info: −5.8 pp. |
| Where does it hurt most? | **Nested schemas.** Structured targets: Raw 76.4% vs TSCG 32.8%. Flat targets: 88.4% vs 80.4%. |
| Does more tools make things worse? | **Yes, for all formats.** Raw fell from 92.0% (5 tools) to 75.0% (100 tools); the first significant drop was at 20 tools. |
| Does TSCG's harm grow with catalog size? | **No detectable change.** The gap stays about 22–30 pp at every size. |

---

## 2. What is new here

1. **A failed replication of a published claim, under controlled conditions.** The TSCG authors report gains for small models on their own benchmarks. On real JSONSchemaBench schemas with Qwen3-1.7B and the `conservative` profile, we measured a large *loss*. This does not show TSCG is bad in general; it shows the claim does not hold for this setting.
2. **A decomposition that the literature usually skips.** The TSCG-info control separates *information removed* from *format change*. Most "compression helps" results cannot tell these apart.
3. **"Fewer tokens" is not the mechanism here.** Raw-minified cut tokens about 40% with no change in success. Below the context limit, this model was not limited by prompt length. It was limited by what the schema says.
4. **The bottleneck is argument construction, not tool selection.**
   - Even at 100 tools, selection stayed ≥92%.
   - The largest failure class in every format was "correct tool, wrong argument".
   - Under TSCG, wrong-type and missing-required-field errors appear; these are the fields TSCG hides.
5. **A reusable, audited benchmark harness.**
   - Frozen tool pool with a logged review of 631 candidates.
   - Nested paired catalogs.
   - Tasks with a leakage audit.
   - An evaluator with a failure taxonomy, tested against all gold answers.
   - Provenance-checked reporting: no number can be typed by hand.
   - A resumable, checkpointed CPU runner.

---

## 3. How this helps the research project

Mapping onto the proposal (`Research Proposal - API Orchestration at Scale.docx`):

- **H2 (representation hypothesis).**
  - Evidence that *representation matters*: yes, strongly.
  - Evidence that *a compressed representation helps*: no.
  - The hypothesis survives only in a refined form: a representation must **keep schema semantics** (nested types, enums behind `$ref`, required fields). Shortening is not enough.
- **Decision Gate 3** ("only proceed to representation-focused training if the representation produces a reproducible improvement beyond the strongest existing baseline").
  - The strongest baseline is now **Raw-minified**: same information as Raw, about 40% fewer tokens, equal accuracy.
  - TSCG did not pass that bar for this model. Any new representation, including a Blaze-derived one, must beat Raw-minified.
- **RQ3 (dominant failure mode).** For single-call tasks with ≤100 tools shown in full, the dominant failure is **argument construction**, not discovery or selection. **(interpretation)** This points future work towards argument correctness (schema semantics, constrained decoding, verifier feedback) rather than towards selection.
- **H4 / scaling.** Performance falls with catalog size even with every tool in context, and it starts by 20 tools for Raw. This is the baseline that retrieval / progressive discovery (proposal Stage 4) must improve on.
- **Practical guidance (for this model).** Use Raw-minified JSON: it is cheaper and just as accurate. Do not use TSCG when schemas contain nested structure.

---

## 4. More we can learn from the existing data (no new model runs)

The 3,000 stored outputs support further analysis at zero compute cost. Each item below is a **(proposal)**:

| # | Analysis | What it would tell us |
|---|---|---|
| A1 | Failure rate vs **schema features** (depth, `$ref`, unions, enums, constraints, required count) — logistic model per arm | Which schema properties cause errors, and which TSCG removes |
| A2 | **Per-tool** difficulty ranking across arms | Whether a few hard tools drive the effect (e.g. `register_quantum_backend`, `render_rating_component`) |
| A3 | Effect of the **gold tool's position** in the catalog (recorded for every request) | Position bias ("lost in the middle") at 50–100 tools |
| A4 | **Paraphrase sensitivity**: agreement between the two paraphrases of each intent | How much wording, not representation, drives outcomes |
| A5 | **Wrong-tool confusion** pairs (which tool was chosen instead) | Whether confusions follow description similarity, i.e. a selection-quality signal for discovery work |
| A6 | **Invented-value** analysis (E2E vs E2E-strict gap) by arm | How often the model fills unrequested optional fields, and whether format affects it |
| A7 | **Argument-error drill-down** for flat tools under TSCG vs TSCG-info | What exactly the TSCG text format causes when information is equal |

---

## 5. Recommended next experiments (ranked)

Each is a **(proposal)** with a rough cost on the same 4-CPU container (the v1 main run took about 19 h).

1. **Second model, same design** (highest value). Repeat with one more compact model (e.g. Qwen3-4B, or a different family) on the same frozen catalogs, tasks and evaluator. This tests whether the TSCG loss and the "argument bottleneck" are model-specific. The pipeline needs only a new `config/model.json`. Cost: about 1–2× v1 runtime per model.
2. **Information-preserving compact representation** (the Blaze-derived test from the proposal, now well-defined).
   - Design a readable format that keeps nested types, enums, `$ref` targets, required fields and key constraints.
   - The required baseline is **Raw-minified**; also keep Raw and TSCG-info.
   - Focus the analysis on **structured** schemas, where the information loss happened.
   - Success criterion: beat Raw-minified on argument correctness, at equal or lower tokens.
3. **Constrained decoding as an argument-correctness control.** Grammar-constrained JSON from the raw schema (llama.cpp supports JSON-schema grammars). If constrained decoding removes most remaining errors, representation work matters less for validity and more for semantic values.
4. **Retrieval / progressive discovery baseline** (proposal Stage 4). Show only the top-k retrieved tools from the 100-tool catalogs. Measure retrieval recall and E2E against the full-context curve measured here. It reuses the same tasks and evaluator.
5. **Larger catalogs** (250–500 tools). These need more context than the 32k native window (YaRN or a larger-context model). Use Raw-minified and TSCG to stay within budget. This tests whether the size trend continues or breaks.
6. **Multi-step tasks** (proposal L1–L2: 2–5 dependent calls). The current mocks are single-call. Stateful mocks would test whether argument errors compound across steps.
7. **Other TSCG profiles** (`balanced`, explicit principles). This would complete the TSCG picture fairly. Use pinned, explicit principles so the configuration does not change with catalog size.

**Suggested immediate step:** run A1–A7 (no compute), then Experiment 1 (second model). These two decide whether Experiment 2 (Blaze-derived) is worth building.

---

## 6. Lessons for running these experiments

- **Memory:** llama.cpp's default host-RAM prompt cache caused an out-of-memory kill. Run with `--cache-ram 0`.
- **Long prompts are slow on CPU:** prefill fell to about 42 tok/s at 28k tokens, versus 132 tok/s for short prompts. Budget for this; 100-tool raw catalogs dominate runtime.
- **Containers restart:** keep runs resumable and push checkpoints. Both saved this run.
- **Pilot first, then a review of every failure.** The pilot found one ambiguous task and motivated the E2E-strict metric, both before the main run.
- **Keep timing runs isolated:** the latency sub-run must have the CPU to itself.
