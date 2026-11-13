# API orchestration at scale

Research on how schema representations, decoding constraints and small models affect API tool use.

- **[Representation experiment](experiment/README.md):** the original frozen Qwen3-1.7B experiment,
  its tasks, catalogs, evaluator and stored results. This experiment is preserved unchanged.
- **[Schema-native E0](schema-native/README.md):** raw/minified × free/constrained JSON Schema
  decoding, with paired frozen tasks, runtime preflight, resumable runs and failure reporting.
- **[Research plan](schema-native/PLAN.md)** and **[validation record](schema-native/analysis/e0-readiness/VALIDATION.md)**:
  predictions, reproducibility checks, observed engine limits and gates before training.

E0 runs locally on a 16 GB Apple Silicon Mac. See the E0 README for exact setup and run commands.
The first real benchmark is in progress. LoRA (E1) and contrastive training (E2) remain deferred
until the decoding/engine issues and unseen-schema evaluation datasets are ready.
