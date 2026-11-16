# Stage 05 — Task instances

## Overview

Stage 05 defines the **evaluation task instances** used by the stage 06 runner. Each instance pairs an intent (a natural-language goal) with a client version and contains:

- `client_native_request` — the request the client would send in its own API version
- `gold_calls` — the correct call(s) at the server version that the agent must issue
- `gold_backend_response` — the actual backend response obtained by running the gold call
- `gold_client_answer` — the response translated back into the client's version schema
- `change_tags_request / change_tags_response` — which catalogue kinds the task exercises
- `missing_info`, `missing_info_source` — server-version fields that are needed, absent from the native request and not derivable from it (07b A7), with the place where the client has each value
- `expected_refusal`, `refusal_predictable` — the refusal the gold call gets, if any (07b A8)

## Instance counts

| Set | L1 | L2 | L3 | Total |
|---|---|---|---|---|
| Stage 2 (versions_behind=0) | 30 | 30 | 30 | 90 |
| Stage 3 (versions_behind>0, main) | 60 | 120 | 150 | 330 |
| **Total main** | **90** | **150** | **180** | **420** |
| Pilot (all client versions subset) | 30 | 30 | 30 | 90 |
| **Grand total** | **120** | **180** | **210** | **510** |

**L1:** 2 client versions × 30 intents = 60 Stage 3 + 30 Stage 2 = 90 main; 10 pilot intents × 3 versions = 30 pilot  
**L2:** 4 client versions × 30 intents = 120 Stage 3 + 30 Stage 2 = 150 main; 10 pilot intents × 3 versions = 30 pilot  
**L3:** 5 client versions × 30 intents = 150 Stage 3 + 30 Stage 2 = 180 main; 10 pilot intents × 3 versions = 30 pilot  

## Intent composition

### L1 (30 main, 10 pilot)

- **Identifier distribution:** 10 phone_number, 10 IPv4+port, 8 IPv6, 2 NAI-only
- **Reachability states covered:** DATA_SMS, DATA_ONLY, SMS_ONLY (via world D01–D30)
- **prompt_half:** true for m01, m03, m05, … m29 (odd-numbered)
- **NAI-only intents:** m23 and m30 (gold `done` through the fact's identifier, 07b A1)

### L2 (30 main, 10 pilot)

- **Identifier distribution:** 10 phone_number, 10 IPv4+port, 8 IPv6, 2 NAI-only
- **Area radii:** 2000–3000 m (07b A3: the v0.1.0 `accuracy` minimum is 2 km; all within the coverage box lat 35–60, lon -12 to 25)
- **maxAge intents:** m09 (600s), m16 (0s), m26 (300s), m27 (3600s), m30 (0s) — 5 intents
- **UNABLE_TO_LOCATE devices:** D03, D11, D19, D27 (m03, m11, m19, m27); no fact tells the agents this (07b A6)
- **Expected outcomes:** TRUE, FALSE, PARTIAL, and UNABLE_TO_LOCATE across the 30 intents
- **prompt_half:** true for odd-numbered

### L3 (30 main, 10 pilot)

| Operation | Main intents | Pilot intents |
|---|---|---|
| createSession | 22 (m01–m22) | 7 (p01–p02, p05–p07, p10) |
| getSession | 4 (m23–m26) | 2 (p03, p08) |
| deleteSession | 4 (m27–m30) | 2 (p04, p09) |

- **QoS profiles used:** QOS_E (8×), QOS_M (7×), QOS_L (5×), QOS_S (5×) in creates
- **Notification (sink) intents:** m07, m10, m12, m15, m17, m18, m19, m20 (8 of 22 creates)
- **NAI-only intents:** m16 and m21 (gold `done` through the fact's identifier, 07b A1)
- **Duration-profile conflicts:** m01 (QOS_E+1h → gold uses QOS_M), m11 (QOS_E+2h → gold uses QOS_M); the fact only states the preference (07b A6)
- **prompt_half:** true for odd-numbered

## Change tag coverage

Stage 3 main instances with at least one tag of the kind in either direction, **prompt-half count in brackets** (07b A9: tags follow the fields and values an instance exercises, so declined instances have no response tags and the phone tag only appears where the rendered form differs).

| API | renamed | restructured | unit_format | newly_required | changed_meaning | removed |
|---|---|---|---|---|---|---|
| L1 | 30 (15) | 60 (30) | 5 (0) | 0 (0) | 0 (0) | 0 (0) |
| L2 | 30 (15) | 30 (15) | 30 (15) | 105 (48) | 37 (23) | 0 (0) |
| L3 | 44 (23) | 40 (21) | 96 (49) | 78 (39) | 8 (4) | 0 (0) |

**Prompt-half counts below 5** (the Stage 3 ablation needs at least 5 per kind): **L3 `changed_meaning` has 4.** All 8 instances are the notification URL at v0.8.1, and only 4 of the 8 intents with a notification URL are odd-numbered. This is reported to Petr. L1 `unit_format` has 5 instances and **0 in the prompt half**: the 5 odd-numbered phone intents keep their "+", so no rendered form differs. Both are structural.

**Structural gaps:** L1 has no `newly_required`, `changed_meaning` or `removed` entry; L2 and L3 have no `removed` entry that a task can exercise.

## Gold answer distribution

`gold_client_answer.status` of the main instances (420), before and after the 07b corrections. `declined` now means no result because the server declined or the service refused. The L1 and L3 declines of the first version were the NAI-only intents (now `done`, A1); the L2 changes follow the radii and the removed facts (A3, A6).

| API | Stage | Status | Before 07b | After 07b |
|---|---|---|---|---|
| L1 | 2 | `done` | 28 | 30 |
| L1 | 2 | `declined` | 2 | 0 |
| L1 | 3 | `done` | 56 | 60 |
| L1 | 3 | `declined` | 4 | 0 |
| L2 | 2 | `done` | 23 | 25 |
| L2 | 2 | `declined` | 7 | 5 |
| L2 | 3 | `done` | 92 | 99 |
| L2 | 3 | `declined` | 16 | 8 |
| L2 | 3 | `unrepresentable` | 12 | 13 |
| L3 | 2 | `done` | 28 | 30 |
| L3 | 2 | `declined` | 2 | 0 |
| L3 | 3 | `done` | 140 | 150 |
| L3 | 3 | `declined` | 10 | 0 |

## Instances without change tags

After 07b A9 an instance has no tag when it exercises no changed field or value:

1. L3 getSession and deleteSession (path parameter `sessionId`, unchanged), and the L3 v0.8.1 delete whose empty answer has no field;
2. L3 createSession at v0.11.0 and v1.0.0 without a notification URL (only `sink` changed);
3. declined L2 instances at v0.2.0 to v2.0.0 (the refusal is the expected result; response tags would describe fields that no answer has).

`catalogue_breaking_crossed` is the number of breaking catalogue entries behind an instance's own tags: 0 for these instances.

## Validation tests

`tests/test_tasks.py` runs on **all 510 instances** (07b A11):

- `test_native_request_and_gold_answer_are_valid_for_the_client_version`: strict validation against the client version's own specification, `additionalProperties: false` throughout (`nlipeval/tasks/strict.py`). It found the wrong base paths of L1 v0.6.0, L2 v0.2.0 and L3 v0.8.1 to v0.10.0, and `maxAge: 0` at L2 v0.2.0, whose minimum is 60.
- `test_every_gold_value_is_reachable`: every leaf of every gold call is in the intent text, the facts, the native request, or is the server constant `areaType`.
- `test_gold_durations_ages_and_profiles_follow_the_intent`, `test_intent_text_agrees_with_native_request`, `test_fact_lint`, `test_missing_info_definition`, `test_nai_only_and_ipv4_gold_alternatives`, `test_phone_without_plus_in_even_numbered_intents`.
- `test_gold_call_round_trip`: every gold alternative is accepted by the backend with the stored response, and `render_answer` gives `gold_client_answer`.
- `test_tags_follow_what_the_instance_exercises`, `test_catalogue_breaking_crossed_is_per_instance`, `test_declined_refusal_fields`.
- `test_l2_area_constraints`: every radius, main and pilot, is at least 2000 m.

## Review documents

- [`reports/review-renderer-rules.md`](review-renderer-rules.md): Derivability rules and the per-API renderer rules
- [`reports/review-tasks.md`](review-tasks.md): All 90 intents (30 per API) with native requests, gold calls, and gold client answers by version

## Files produced

| File | Description |
|---|---|
| `config/intents/L1.yaml` | 30 main + 10 pilot L1 intents |
| `config/intents/L2.yaml` | 30 main + 10 pilot L2 intents |
| `config/intents/L3.yaml` | 30 main + 10 pilot L3 intents |
| `config/answer_schemas/L1.yaml` | Client answer schemas for L1 |
| `config/answer_schemas/L2.yaml` | Client answer schemas for L2 |
| `config/answer_schemas/L3.yaml` | Client answer schemas for L3 |
| `nlipeval/tasks/render/__init__.py` | Render package marker |
| `nlipeval/tasks/render/l1.py` | L1 request/answer renderer |
| `nlipeval/tasks/render/l2.py` | L2 request/answer renderer |
| `nlipeval/tasks/render/l3.py` | L3 request/answer renderer |
| `nlipeval/tasks/generate.py` | Task instance generator (all APIs) |
| `nlipeval/tasks/coverage.py` | Coverage table generator |
| `nlipeval/tasks/review_tasks.py` | Review tasks doc generator |
| `tasks/L1/*.json` (120) | L1 task instance JSON files |
| `tasks/L2/*.json` (180) | L2 task instance JSON files |
| `tasks/L3/*.json` (210) | L3 task instance JSON files |
| `tasks/INDEX.csv` | Index of all 510 task instances |
| `results/tasks/coverage.csv` | Stage 3 coverage per kind per API |
| `tests/test_tasks.py` | 73 validation tests |
| `reports/review-renderer-rules.md` | Renderer rules review |
| `reports/review-tasks.md` | Intent details review |
| `reports/stage-05-tasks.md` | This document |
