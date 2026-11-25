# DigitalOcean development pilot

**2026-11-25.** Five assistant-authored requests each use a five-tool catalog derived from the
[official OpenAPI tree](https://github.com/digitalocean/openapi/tree/0644e10b56a1ea9eff4e221ff35758db5037510a/specification).
The packet is for semantic review. Zero test intents are approved.

| Check | Result |
| --- | --- |
| Source pin and dependencies | Commit `0644e10b56a1ea9eff4e221ff35758db5037510a`, ten file hashes including the root, selected operation files, shared parameters and licence |
| Prior source screen | Zero digitalocean organization matches across 2,002 indexed schema IDs. Another 286 IDs have collection-level provenance only. |
| Prior schema screen | Zero exact canonical matches to the 2,288 prior schema IDs screened |
| Author gold validity | All five calls validate on their selected tool |
| Tool selection | CPU, available memory and five-minute load each take the same required string arguments. Their gold arguments validate on all three tools. |
| Tighter parameter contract | The bandwidth operation also requires the interface and direction enums. |
| Description-based constraint | The tag-only call satisfies the request. Adding the proposed name filter produces a schema-valid call that violates the documented exclusion. |

The flat argument adapter reads the pinned repository archive without extracting it or fetching
references over the network. It resolves relative paths and JSON Pointer fragments only within
the specification tree and records every file read. It keeps source field names, enum values,
optional defaults and descriptions. It closes the outer argument object and leaves query time
values as strings, as declared upstream. The packet includes the unmodified
[Apache 2.0 licence text](https://github.com/digitalocean/openapi/blob/0644e10b56a1ea9eff4e221ff35758db5037510a/LICENSE).

The source [Droplet list operation](https://github.com/digitalocean/openapi/blob/0644e10b56a1ea9eff4e221ff35758db5037510a/specification/resources/droplets/droplets_list.yml)
describes the tag/name restriction in parameter prose. The audit preserves this distinction by
recording a candidate that passes the offline validator and fails the user's request under the
documented contract. The two possibilities differ by one argument. A future control with an
added schema assertion would require its own version and equivalence scope. Server response
behavior, live API compatibility and full upstream bundler parity were outside these checks.

## Review and adjudication

All five first answers matched the authored tool and arguments. Adjudication confirmed the
matches and the recorded checksums of the unchanged answers and notes. The reviewer disclosed
seeing other review filenames while locating the ZIP and reported opening only this packet
before solving. The adjudication SHA-256 is
`694fc03a04ba107ff0f16776a7176809e0d1009c033141f0673b4ac78c1a6b9c`.

For the tag task, the request prioritizes the tag and makes the optional name contingent on
support. The parameter descriptions state the exclusion, so the correct call omits `name`.
The request expressly asks for page 1. The current policy requires preserving requested
values, so the correct call includes `page: 1`. The schema also accepts omission because
`page` is optional. The reviewer identified that overlap as a wording concern.

Use this clarification in future packets: “Keep an explicitly requested value even when
it equals the schema default. Omit unrequested defaults.” This keeps the scorer focused on
what the request asked for. The existing packet and exact comparison continue to use their
published contract.

The five reviewed tasks stay in development and DigitalOcean is now an exposed development
group. Zero held-out test intents are approved. E1 and E2 stay gated.

## Reproduce

From `schema-native/`, use the existing environment with PyYAML 6.0.3. The main command verifies
the generated audit against the recorded dependency and input bytes before producing a packet.

```bash
source_dir="$(mktemp -d)"
curl -fsSL https://codeload.github.com/digitalocean/openapi/tar.gz/0644e10b56a1ea9eff4e221ff35758db5037510a \
  -o "$source_dir/digitalocean.tar.gz"
curl -fsSL https://raw.githubusercontent.com/sdbs-uni-p/json-schema-corpus/79f808b10c9e3269ea57f5c7c64fd663eadf2703/repos_fullpath.csv \
  -o "$source_dir/source-index.csv"
.venv/bin/python -m sn.v2_digitalocean --archive "$source_dir/digitalocean.tar.gz" \
  --source-index "$source_dir/source-index.csv" --check
.venv/bin/python -m sn.v2_digitalocean --archive "$source_dir/digitalocean.tar.gz" \
  --source-index "$source_dir/source-index.csv" --export-review "$source_dir/blind-review.zip"
```

The exported review ZIP has SHA-256
`2ccf9926b271f9a1f6f73a4aa20e89ec39a28b396963e706cfd73d31de60e40a`.
Both this import and the Stripe/PokéAPI import reproduced. All 240 tests passed
(220 package, 12 evaluator and eight power-planning). Send only the ZIP to a fresh review
session.
