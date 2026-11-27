# Follow-up API source candidates

**2026-11-25.** Independent checks of the two suggested projects. Both were compared with the
same 2,288 prior schema IDs used for the official API pilot. On the 2,002 IDs mapped to an
indexed GitHub project, neither organization appears. The remaining 286 IDs have only
collection-level provenance. These findings support trying both sources in development.

## DigitalOcean first

The [pinned OpenAPI root](https://github.com/digitalocean/openapi/blob/0644e10b56a1ea9eff4e221ff35758db5037510a/specification/DigitalOcean-public.v2.yaml)
is OpenAPI 3.0.0, API version 2.0. The repository notice and OpenAPI metadata both identify
Apache 2.0. I resolved the local file and parameter references for the suggested operations
from the pinned source tree.

| GET operation | Source input check |
| --- | --- |
| Droplet CPU, available-memory and five-minute load metrics | The three query schemas have the same required string fields `host_id`, `start` and `end`. Choose the tool by the requested metric. |
| Droplet bandwidth metrics | Requires the same three fields plus `interface` (`private` or `public`) and `direction` (`inbound` or `outbound`). |
| List Droplets | Optional `page`, `per_page`, `tag_name`, `name` and `type`. Both pagination fields have a minimum of 1, `per_page` has a maximum of 200, and `type` has two allowed values. |

The list operation's descriptions say a tag filter cannot be combined with a name filter or
a type filter. The unchanged parameter schemas accept both combinations under local validation.
Use a satisfiable tag-only request to test whether the model follows the visible descriptions.
A conflicting request would need a separate refusal contract. Any later translation of this
prose into JSON Schema belongs in a separately labelled derived control. Metric times remain
strings as the source declares. [Pinned list operation](https://github.com/digitalocean/openapi/blob/0644e10b56a1ea9eff4e221ff35758db5037510a/specification/resources/droplets/droplets_list.yml)

The root file has SHA-256 `077698af2ea18b9713399901725ed1f142200d6a1882fc213144b39c649b186e`.
The [licence file](https://github.com/digitalocean/openapi/blob/0644e10b56a1ea9eff4e221ff35758db5037510a/LICENSE)
has SHA-256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
The root hash identifies only that file. A reusable intake needs to pin the source tree and
record the resolved input dependencies. These checks cover five operations. Upstream bundle
parity remains unverified.

## Twilio for a later tranche

[Tag 2.11.1](https://github.com/twilio/twilio-oai/tree/2.11.1) resolves to
`090e1654f5ca1f6a01b6a117fbec5f75c44f44d7`. The five listed GET operations are present in the
[pinned core spec](https://github.com/twilio/twilio-oai/blob/090e1654f5ca1f6a01b6a117fbec5f75c44f44d7/spec/json/twilio_api_v2010.json).
The route family is `2010-04-01`. The OpenAPI version is 3.0.1 and its `info.version` is 1.0.0.

All five require the account path parameter. Calls and messages share `To` and `From`. Calls
and conferences use distinct referenced status enums with eight and three values, respectively.
Conferences and recordings use distinct date and date-time formats for their creation filters.
Names such as `DateSent<` are literal keys in the source. Preserve these in a raw-schema
experiment and test transport compatibility before defining a transformation.

The spec hash is `f5efc0ed7078b035f675e04aa2774eaea43a0606c1d699b1fd35759258e5ddc6`.
The [repository licence](https://github.com/twilio/twilio-oai/blob/090e1654f5ca1f6a01b6a117fbec5f75c44f44d7/LICENSE)
identifies MIT and has SHA-256 `282418d5a4ca0a6cd3476637c41bb229e592fc289156d22fbfa188cec1169ff3`.
The spec's own metadata identifies Apache 2.0. Record both and resolve which terms apply to the
spec before incorporating its text or schema extracts into a distributed packet.

## Disposition

Prioritize a small DigitalOcean development packet with two separate targets for review: metric
selection with identical arguments and an argument contract whose exclusion rule lives in prose.
The existing adapter handles inline parameters, so it needs a scoped local-reference resolver
for this source. The existing Stripe/PokéAPI review can proceed in parallel. The two candidates
remain at the scouting stage, with no API calls or approved test tasks.
