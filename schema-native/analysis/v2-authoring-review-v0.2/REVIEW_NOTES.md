# Blind review notes — v2-authoring-v0.2 (32 tasks)

## Disclosure and method

- Source used: only `v2-authoring-v0.2-blind-review.zip` (REVIEW_INSTRUCTIONS.md, SYSTEM_POLICY.txt, tasks.jsonl). I did not open the PR, repository, gold, earlier reviews or earlier conversations, and I did not open any memory files.
- Context note: this session starts with an automatic user-profile snapshot (name, job history, a list of unrelated memory file titles). None of it refers to these tasks. I did not use it.
- Prior exposure: I have no record in this context of seeing these tasks or answers. I cannot rule out exposure to the underlying public JSON Schemas (Snowplow, OCPP, ANS, Esri, etc.) during pretraining.
- No tools from the tasks were run. No model was loaded. The only code run was a local JSON Schema (Draft 4) check of my own answers. All 32 answers pass their schemas. That shows schema validity only; it does not show that the request is satisfied.
- `system_policy` is identical in all 32 records and matches SYSTEM_POLICY.txt.

## Cross-cutting findings

1. **Benchmark scaffolding leaks into requests.** Several requests contain author instructions, not user speech: "Preserve the listed order of values" (V2B_08d0b9115ec8), "Preserve the quoted HTML" (V2B_51686a29d711), "These are fictional benchmark paths; only produce a tool call" (V2B_7cb23e7a63ed), "both in the same currency" (V2B_fca075eb27e3), "Both prices are per unit in the same currency" (V2B_3cb8ce9d349b), "Both times are local wall-clock times in the same time zone" (V2B_d5eb59cc179f), "Treat both as literal patterns" (V2B_c8fbab190e91). These tell the model what the grader checks. They also look unnatural. Consider moving them to author metadata.
2. **Requests echo tool descriptions.** Many requests reuse the tool's wording ("data-source retention lifespan", "temporal averaging filter", "sex code F", "badge assertion … priority", "record identifier"). This makes routing a keyword match. Paraphrase more.
3. **Catalog reuse across paired tasks.** Some pairs share almost the same catalog and swap the gold tool: poll vs MCQ (005a / 5168), start vs reserve charging (151f / 88b4), convert vs record temperature (b94e / dee3), meeting vs booking resource (d5eb / 5043), hotel / flight / restaurant search (243e / 9c21 / fca0). This is a good contrast design. But if both sides of a pair are in the same eval, keep them; if split across train/test, it leaks.
4. **Weak distractors.** About half the catalogs have only one real near miss, or none (see table). Many fillers are from unrelated domains (Snowplow storage configs, Spanish travel-package grouping, PlanetWars, Weave fabric).
5. **Schema defects that weaken validation.** Several schemas accept `{}` or almost anything because nothing is required (push_chart_update, create_geo_path, select_country, set_video_subtitles, track_share_event, set_annotation_filter, submit_badge_list is fine). Others have type bugs (see per-task). Validation alone will pass many wrong answers.
6. **Free-text enum-like values with no documented vocabulary** (share `method`, transaction `channel`, subtitle `format`, poll `end`). Graders should accept reasonable variants or the docs should fix the vocabulary.

## Per-task notes

Format: answer chosen · issues · near-miss count (genuinely plausible competing tools, not just same-domain).

**V2B_005a8720962b — create_poll**
- No issues with tool choice. `end` has no format; I used the ISO string as given. Omitted `votes`, `_id`, `icon`.
- Near misses: create_multiple_choice_question (1). submit_ballot and create_calendar_event are weak. **Below 2.**

**V2B_08d0b9115ec8 — push_chart_update**
- "Preserve the listed order of values" is scaffolding. Schema has no `required`, so `{}` validates.
- Near misses: update_map_chart_points (1). create_timeline_diagram is weak. **Below 2.**

**V2B_151fe38eddb1 — start_charging_transaction**
- Clean. `meterStart` unit (Wh in OCPP) is not documented; 18420 used as given.
- Near misses: reserve_charging_connector, authorize_id_tag, send_connector_status, trigger_charger_message. **Strong (4).**

**V2B_1e3ff6263df1 — create_geo_path**
- "Save a route" vs "path" is a fair paraphrase. Schema has no `required`.
- Near misses: create_place (single point), calculate_distance (takes exactly two lat/long pairs — a real lexical lure). **2, borderline.**
- Note: create_place's `geo.anyOf` branches are not valid sub-schemas (they list property names at the top level), so they constrain nothing.

**V2B_1f9830117b99 — set_data_retention**
- Wording copies the description. Trivial mapping.
- Near misses: none real. Redshift/Elasticsearch storage, persistent volume, content owner are domain-adjacent at most. **0 — catalog gap.**

**V2B_243ee0e3507c — search_hotels**
- "Find lodging" → search, not book. book_hotel also needs `room_type`, which is missing (would require invention). Included optional `number_of_guests: 3` because it was requested.
- Near misses: book_hotel (1). book_flight, group_travel_packages, search_restaurants are weak. **Below 2.**

**V2B_363bd0409596 — set_temporal_filter**
- "Combine 7 images per output image" is a fair paraphrase of averaging.
- Near misses: set_spatial_filter (1). Network and dimensioning tools are same-device but not plausible. **Below 2.**

**V2B_398e2201ba23 — set_full_name**
- No person identifier is given; acceptable because set_full_name has none either. "Record" is vague but fine.
- Near misses: update_person_profile (single `name`), update_user_names (DISPLAY_NAME), create_team_user. **Strong (3).**

**V2B_3c0655d94e31 — track_calories**
- Assumption: `serving_size` for Apple is "1 medium apple" (verbatim). "1 medium" is also defensible. Grader should decide whether the noun is kept.
- Near misses: analyze_health_data (weak; needs timestamps). Others unrelated. **0–1 — catalog gap.**

**V2B_3cb8ce9d349b — generate_invoice**
- Assumption: item names are "Desk lamp" and "Cable tray" (dropping "units"). Price 12 sent as number 12. The currency sentence is scaffolding; no currency field exists.
- Near misses: add_order_item (one item, needs currency), track_transaction, submit_order_addresses. **Strong (3).**

**V2B_3e2345e939ab — configure_sprite_animation**
- Ambiguity: "frame 3 through frame 18" vs schema "index of the starting/ending frame". I used 3 and 18 directly. If frames are counted from 1 and indices from 0, the answer would be 2 and 17. Inclusive/exclusive end is also not documented. `loop: false` included because "playing once" asks for it (default is true).
- Near misses: set_loop_animation (has style "sprite" and repeat count — strong lure for "playing once"), define_keyframe. **Strong (2).**

**V2B_50438e445044 — create_booking_resource**
- "A moderator must approve its bookings" → `validation: true`. Clean.
- Near misses: none real. schedule_meeting, create_calendar_event, book_hotel only share the word "book/room". **0 — catalog gap.**

**V2B_51686a29d711 — create_multiple_choice_question**
- "Preserve the quoted HTML" is scaffolding. Omitted min/max/number fields.
- Near misses: create_poll (needs `end`, missing) (1). create_course, submit_ballot, add_document_link weak. **Below 2.**

**V2B_776ea3d84fa2 — select_country**
- `country` is optional with default "Panama"; included because the request names Costa Rica. Good omission-policy probe. Schema has no `required`, so `{}` validates but fails the request.
- Near misses: set_shipment_address, create_place — weak (need many fields). **0–1 — catalog gap.**

**V2B_7cb23e7a63ed — send_email**
- Body kept with the final period ("Please review the agenda."). The sentence "These are fictional benchmark paths; only produce a tool call" is clearly scaffolding and should be removed.
- Near misses: request_data_export (email field), configure_chat_webhook (message text). track_email_bounce weak. **2, borderline.**

**V2B_88b4ef7b9c33 — reserve_charging_connector**
- "Hold" is a good non-keyword verb. Omitted `parentIdTag`.
- Near misses: start_charging_transaction, authorize_id_tag, send_connector_status (status "Reserved"). **Strong (3).**

**V2B_8905a631b42b — set_smart_light**
- Undocumented mapping: brightness → `power` (only the field description says "Brightness"). Scale of 42 is not stated (percent? 0–255?).
- Ambiguity: the request uses the name to *identify* the lamp; the tool describes `name` as a value to *set*. There is no separate selector, so I put "Reading nook" in `name`.
- Near misses: set_led_states (on/off by ID) (1). set_rgba_color, set_scene_lighting, set_color_modulation weak. **Below 2.**

**V2B_8c5bffd77d25 — configure_camera_network**
- Subnet mask and `UseDHCP: false` equal the defaults, but both are required and requested, so included. Omitted MACAddress/NetworkSpeed.
- Near misses: configure_pod_network (1). Other camera tools not plausible. **Below 2.**

**V2B_98d28f13b4af — set_video_subtitles**
- Format strings "WEB_VTT" and "SRT" come from the field's example list, not an enum. `subtitle_url` has no `required` and no type.
- Near misses: none real. Other video tools (conversion, metadata, GA4 video_start, watermark) are domain-adjacent. **0 — catalog gap.**

**V2B_9bdae199ecd4 — track_share_event**
- Assumptions: `method: "email"` (lowercase; vocabulary undocumented) and `content_type: "article"` (the request says "the article", and policy says to preserve representable details). A grader that expects only method + item_id would mark `content_type` as extra.
- Near misses: track_link_click, track_page_view, record_social_post. **Moderate (2–3).**

**V2B_9c21f559ffc3 — book_flight**
- "One-way" → omit `return_date`. Good omission probe. Airport codes as given.
- Near misses: add_flight_listing (1). Others weak. **Below 2.**

**V2B_9d7e69c4b46e — register_youth_athlete**
- "Sex code F" copies the schema. Content involves a minor's personal data; fictional, but worth noting for data policy.
- Near misses: set_full_name, create_team_user, update_person_profile — they can hold the name but not age/sex. **2, weak.**

**V2B_a4d79419f6c8 — update_scoreboard**
- All six fields are required; values are not defaults, so no omission conflict. "Falcon / Owl" kept verbatim.
- Near misses: none. Rating component, game variant, PlanetWars, charging are unrelated. **0 — catalog gap.**

**V2B_b94e21f53f2e — convert_temperature**
- Clean. A model might compute 71.6 and call record_temperature_event; that is the intended trap.
- Near misses: record_temperature_event (strong) (1). define_observed_property weak. **Below 2.**

**V2B_b9cdc6285489 — enable_table_stream**
- "Before-change and after-change item images" → NEW_AND_OLD_IMAGES. Good paraphrase.
- Near misses: configure_dynamodb_storage (table name field), set_subscription ("updates"). **2.**

**V2B_c8fbab190e91 — set_annotation_filter**
- **Ambiguous sentence:** "Treat both as literal patterns." Reading A: keep the strings exactly as written (do not double-escape or alter). Reading B: treat them as literal text, not regex — which contradicts "using regular expressions". I used Reading A with `regex: true`. Recommend rewording.
- Schema defect: `regex` has `type: boolean` but `default: "false"` (a string).
- JSON escaping: the stored strings are `^public\.` and `^internal\.` (one backslash each).
- Near misses: set_vulnerability_whitelist (allow/ignore list), apply_selector_changes, configure_api_diff_report — all weak. **0–1 — catalog gap.**

**V2B_d5eb59cc179f — schedule_meeting**
- "Put … on the calendar" pulls toward create_calendar_event, but that tool requires `location` (missing) and cannot hold participants. Good lexical trap. The time-zone sentence is scaffolding.
- Near misses: create_calendar_event (strong), create_festival_event. **Strong (2).**

**V2B_d63dc99be3d6 — create_team_user**
- "Active" → `Active: true`. "Numeric identifier" → integer 204.
- Schema defect: `Role` enum contains `null` while `type` is string.
- Near misses: invite_org_member (role enum lacks Operations), add_employees, update_person_profile, register_user_device. **Strong (3+).**

**V2B_dee36871406d — record_temperature_event**
- "Environmental sensor" matches the schema title EnvSensor4. 68 differs from the default 75, so required and explicit.
- Near misses: convert_temperature, define_observed_property, analyze_health_data. **Strong (3).**

**V2B_ef5659105261 — submit_badge_list**
- "List the badge assertion …" reads like a read/list query, not a submission. Unnatural.
- Near misses: add_badge_signature, add_document_link, create_content_reference. **Moderate (2–3).**

**V2B_f29fbf3ea11c — record_channel_transactions**
- Undocumented vocabulary: `channel: "telephone"` (could be "phone"). "Daily report" → `period: "day"`. Timestamp and `_id` used verbatim.
- Near misses: record_award_applications (same shape: _id/_timestamp/period/count — strong), track_transaction. **Strong (2).**

**V2B_fca075eb27e3 — search_restaurants**
- Meaning of the price range (per person? per meal? tier?) is not documented. The "same currency" note is scaffolding.
- Near misses: search_products (min/max price range) (1). search_recipes_by_ingredients ("Korean") and search_hotels ("Seattle") are lexical only. **1–2, borderline.**

## Catalog summary

| Near-miss strength | Tasks |
|---|---|
| Strong (2+ real competitors) | 151f, 398e, 3cb8, 3e23, 88b4, d5eb, d63d, dee3, f29f |
| Moderate / borderline 2 | 1e3f, 7cb2, 9bda, 9d7e, b9cd, ef56, fca0 |
| Only 1 real competitor | 005a, 08d0, 243e, 363b, 5168, 8905, 8c5b, 9c21, b94e |
| None (catalog gap) | 1f98, 3c06, 5043, 776e, 98d2, a4d7, c8fb |

So about 16 of 32 catalogs meet the "at least two plausible competing tools" bar, and 7 have no real near miss.

## Answers that rest on an assumption

| Task | Assumption |
|---|---|
| 3c06 | serving_size "1 medium apple" kept verbatim |
| 3cb8 | item names drop "units" |
| 3e23 | frame numbers used directly as indices |
| 8905 | brightness → `power`; name used as identifier |
| 9bda | method "email"; content_type "article" included |
| c8fb | "literal patterns" = keep strings verbatim; regex true |
| f29f | channel "telephone" |
| 98d2 | format strings "WEB_VTT", "SRT" |

## Readiness view

These are usable draft tasks. They are not benchmark-ready yet: remove scaffolding sentences, fix the c8fb wording, document the free-text vocabularies, and add real near misses to the 7 gap catalogs. Agreement with gold would not fix these issues.
