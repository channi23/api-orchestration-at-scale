# Source candidate audit, not a blind task solve

Review the eight source-candidates.jsonl rows. Each includes the unmodified source schema,
proposed offline argument binding, JSON-pointer purpose evidence, sample and limitation. These
are source-derived adapters, not established callable production endpoints. No API is executed.

For each card, record in SOURCE_REVIEW.md:

- Which proposed purpose is supported by the raw schema and which part is inferred or unknown.
- Whether the binding preserves dialect, local references and validation meaning. For a value
  wrapper, interpret the content-addressed resource URI as that row's source_schema, not a network
  URL. Flag runner/engine integration concerns separately from raw-schema validity.
- Whether it is a credible potential competitor for its proposed target kind, merely related,
  or unsuitable. A full request/catalog is not supplied, so do not certify a near miss or unique
  correct tool from this packet. Suggest what evidence/request distinction would be needed.
- Any family overlap, missing source/licence evidence, unsupported assumptions, units or behavior.
  Do not infer TTL units, pattern semantics, unsupported backend fields or current country-code
  standards from names alone. Do not invent new API operations to make a candidate fit.

This audit is explicitly nonblind. An existing reviewer may do it. It does not approve tasks,
freeze a split, authorize model inference or lift E1/E2 gates. Do not execute tools or alter source
schemas. Report unresolved questions and stop.
