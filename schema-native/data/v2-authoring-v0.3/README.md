# v0.3 wording adjudication and source-pool search

**2026-11-25. Provisional review material; zero approved test tasks.**

This version follows the unblinded [v0.2 adjudication](../../analysis/v2-authoring-review-v0.2/ADJUDICATION.md).
It changes ten requests, leaves 22 unchanged, and preserves **all 32 v0.2 gold answers**. The raw
schemas, authored tool descriptions, v0.1/v0.2 sources, first solves and receipts are untouched.
All variants remain descendants of 32 intent lineages, not additional independent observations.

## Supported fixes and one qualification

- Serving strings are quoted, including the existing `"1 medium apple"`. This takes the permitted
  quoting option rather than silently changing gold to `"1 medium"`.
- Invoice item names are quoted with explicit quantities and prices "each". The redundant currency
  sentence is removed while the per-unit meaning stays visible.
- Animation inputs are explicitly frame indices 3 and 18. This asks for those input values without
  assuming an index origin or inclusive/exclusive playback behavior.
- The light request now explicitly **sets** the friendly name. The schema does not establish that
  name selects a device, so the suggested description rewrite was not adopted. No selector, lookup
  behavior, brightness scale or new source semantics are invented.
- Regex wording is "Use these regular expressions exactly as written"; there is no literal-text
  versus regex contradiction. User-oriented email/chart/HTML requests drop redundant grader asides.
- The meeting retains the necessary convention as a concise "local time" request. Needed semantics
  stay model-visible rather than being moved into hidden metadata.

The model/reviewer policy explicitly requires exact supplied strings, including case, with **no
synonym/casing aliases**. Semantic mappings still use schema enum labels, such as before/after
images to NEW_AND_OLD_IMAGES. No aliases are added after model output. Numeric values compare
mathematically, booleans remain distinct, arrays keep order and object-key order is irrelevant.
This policy is prospective v2 material, not an amendment to frozen E0/E0b or an E1 authorization.

## Catalog gaps are not solved by wording

All catalogs are deliberately held identical to v0.2, with the same three-appearance distractor cap.
Only nine were clearly strong according to the **v0.2** reviewer; seven were borderline, nine had
one competing tool, and seven had none. Those ratings are not new blind v0.3 results. Wording can
also affect perceived tool competition, so no automatic rating transfer or approval is claimed.

`source-pool-probe.json` searches all 300 existing pool tools for the seven requested kinds of peers.
It records exact patterns, matched documentation/property snippets and paths, schema IDs and hashes.
It does not create tools or promote text matches to near misses. No full raw schema files are newly
copied into Git; the matched metadata snippets remain source-attributed through IDs and hashes.

| Target gap | Other text-matched tools | What that count means |
| --- | ---: | --- |
| Retention / TTL | 9 | Includes request timeout and appliance expiry; expiry units and API behavior require source review. |
| Meal / calorie logger | 1 | The hit is assign_pantry_role, not a nutrition logger. |
| Booking resource | 6 | Includes charging reservations and unrelated uses of moderation; no peer is certified. |
| Country selector | 27 | Broad state/location words produce many false positives, not 27 geographic selectors. |
| Caption / text track | 0 | No other match under this recorded search in the 300-tool pool; not proof about all upstream schemas/APIs. |
| Score recorder | 1 | The hit is tag_named_entity, not a single-player score updater. |
| Include/exclude filter | 15 | Includes filters and file-glob configuration requiring independent semantic review. |

These results show why the requested peer types cannot simply be asserted to exist in the current
catalogs. A broader curated source-pool search/expansion and actual source documentation may be needed.
The probe omits enum/default/example instance data and is only a text heuristic; it is not an
exhaustive semantic search or an impossibility proof. No catalog is changed from a probe hit.

## Reproduction and review

From schema-native/:

```bash
.venv/bin/python -m sn.v2_v03 audit --check
.venv/bin/python -m sn.v2_revision audit --check
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_v03.py
```

`sn.v2_v03 audit` without --check regenerates only v0.3 artifacts from wording.jsonl and the alias
policy. Parent artifacts must reproduce before use; overrides cannot supply gold or tool descriptions.
The inherited root-property default diagnostic remains limited in scope; no taxonomy was generalized.

Export a local packet with only cleaned requests, raw catalog tools, the visible policy and neutral
review instructions:

```bash
.venv/bin/python -m sn.v2_v03 export-review --out /tmp/v2-authoring-v0.3-blind-review.zip
```

Give only that packet to a fresh reviewer/context with no task/gold-bearing history or retrieved
memories. Disclose prior exposure. The previous reviewer has seen the gold and is now unblinded.
The packet is suitable for another wording check, **not a claim that catalog readiness is achieved**.
After a first solve is preserved, `sn.v2_v03 check-review` accepts --responses, --reviewer and a new
--out path, reusing the existing strict comparator without automatic approval.

`pairs.jsonl` keeps each v0.2 request beside v0.3 under identical catalogs and the new shared policy.
Old solves are not new results under that policy. A future score gap would show sensitivity to the
specified wording/policy context, not uniquely identify scaffolding or schema understanding.
In particular, name setting, serving boundaries and frame indices select an intended reading;
they are not established meaning-preserving transformations merely because the gold stays equal.

No local model load, inference, training, new native capability check or source-schema edit occurred.
Hard-keyword tracks, source/family/licence clearance, catalog improvements and the larger 800/200
intent dataset remain incomplete. **E1/E2 stay gated.**
