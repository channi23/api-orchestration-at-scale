# Official API source pilot wording review

**2026-11-25.** The original Stripe/PokéAPI review matched all six tools and arguments.
The adjudication checksum matched the preserved first-solve answers byte for byte. The
reviewer worked in an existing session and reported no prior packet or gold exposure.
Adjudication SHA-256:
`2c6720345990fff87244f5438cae0dba72e8029edc839c8ea3cd19a4b1f9374c`.

This version revises two requests:

| Parent task | Clarification |
| --- | --- |
| `V2OS_1ba2415ada23` | Specify that the first item is position zero. The gold still asks for 20 items after skipping the first 40. |
| `V2OS_0ab308de31c1` | Explicitly request only currently active codes for the given coupon. |

Both cases use the original five-tool catalogs in the same order, with the same schemas,
policy and expected calls. The visual-form case still depends on the requested resource and
tool descriptions, since more than one tool accepts the slug. It stays in the original packet.
The other requests also stay there. The two revised rows have new task IDs and keep their
underlying intent lineages. These are two follow-up development reviews with zero test approvals.

The two first answers matched their inherited gold and validated on the selected tools.
The reviewer reported working with the ZIP alone and saved answers before gold access.
The supplied schemas resolve the requested active-only filter through the Boolean `active`
field. Expiry and redemption limits are separate questions outside this call contract.
The paging case specifies the index base. Continuing the same list assumes that the first
page and requested page follow the same ordering. The alternative Pokédex lookup takes a
single identifier and offers no pagination. Gold adjudication is pending.

## Reproduce

From `schema-native/`, reuse the v0.1 review ZIP produced by the
[original pilot](../v2-official-sources-v0.1/README.md):

```bash
.venv/bin/python -m sn.v2_official_wording \
  --parent-zip /path/to/v2-official-sources-v0.1-blind-review.zip \
  --out /tmp/v2-official-sources-v0.2-wording-review.zip
```

The exporter verifies the parent ZIP hash and preserves its licence files. The local
follow-up packet has SHA-256
`17151c73e0f50f39c3f86e1da033787b4bf57dea3625e3b2ab18d6004e2f7d38`.
Give the ZIP alone to a fresh reviewer for a wording check. E1 and E2 remain gated.
