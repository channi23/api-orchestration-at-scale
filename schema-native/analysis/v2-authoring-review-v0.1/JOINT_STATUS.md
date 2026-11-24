# Joint adjudication receipt and v0.2 disposition

**2026-11-25. Answer agreement resolved; task approval remains open.**

[ADJUDICATION.md](ADJUDICATION.md) is the reviewer's unmodified, now-unblinded response. It matches
the uploaded and local copies byte-for-byte. Its separate receipt records its hash and the hash
of the original blind-review receipt; neither the original notes nor first solve was rewritten.
The reviewer independently reports confirming all 32 tool/argument matches against the gold.

Both sides agree that mismatching defaults and ineffective null enum entries are legal schemas,
that two target tools use $ref, and that "about half don't need a schema" is an unmeasured judgement.
Both sides agree that the batch is not approved for testing. No new model result follows.

## Implemented in a separate version

[v0.2](../../data/v2-authoring-v0.2/README.md) quotes the email body, clarifies one chart call,
rewrites the restaurant request, removes poll votes and quiz counts, and removes avoidable hints.
Only poll and quiz gold change. Source schemas and all v0.1 artifacts remain unchanged.
The omit-unrequested-defaults policy is now explicit in the prospective model/reviewer prompt,
with a separate limited-scope extra-default diagnostic and tests that preserve other mapping errors.

Each original request/gold is retained as a paired control under the same **new** catalog and policy.
Catalog repetition is capped at three distractor appearances per tool. Ten tasks still lack two
author-nominated near misses, and all nominations need independent review. This is reported as an
unmet gate, not hidden by declaring unrelated tools near misses.

## Two methodological qualifications

1. **The proposed aggregate wording gap is not a direct pure-scaffolding measure.** Poll/quiz
   have different gold obligations, restaurant drops unsupported semantics, and some changes repair
   ambiguity. Even same-gold wording changes can alter clarity or lexical overlap. Label this as
   wording sensitivity, separate change types, and independently review any truly minimal hint-only
   subset before making a stronger causal claim. Two unchanged pairs are controls, not hint effects.
2. **A future schema ablation must define what remains visible.** A useful comparison could retain
   the same tool names/descriptions and output contract, while removing only parameter schemas,
   using free decoding in both arms. A schema-informed decoder in the nominal no-schema arm would
   still supply schema information. Such an ablation needs a separately approved protocol, not an
   ad-hoc run or a claim inferred from this review.

The original reviewer has seen the gold. A fresh reviewer/context receives only the v0.2 blind packet,
preserves first answers and ambiguity notes, and discloses prior access. A fresh session does not
itself prove independence or lack of pretraining exposure. No same-context review is counted blind.

**Approved test tasks: 0. Fresh v0.2 reviews: 0. E1/E2 remain gated.** Dataset scale, native engine
coverage, family/source/licence checks and the separate hard-keyword track remain unresolved.
