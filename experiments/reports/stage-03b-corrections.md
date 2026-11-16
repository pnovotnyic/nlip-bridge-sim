# Stage 03b: corrections to stages 01–03

Date: 2026-11-13. Applies decisions D1–D11, S1–S5 and speed-ups 1–11 from `bob_plan/reviews/`.
Nothing was sent to maintainers and no issue was opened.

## Status

| Item | State |
|---|---|
| A. Stage 01 | done; A6 (key rotation) is not being done, by Petr's decision |
| B. Stage 02 | done |
| C. Stage 03 | done |
| R5 (Claude Opus 5.5) | disabled in main runs (`enabled_in_main_runs: false`); deferred to stage 14. Not re-run |

## A. Stage 01 changes

| Change | File |
|---|---|
| `reasoning_text` captured (`reasoning_content` or `reasoning`), cached and logged in each call record | `nlipeval/models/adapter.py` |
| Timeout policy: first attempt 120 s, later attempts the rung's `timeout_s`; each attempt's timeout logged in `attempts` | `nlipeval/models/adapter.py` |
| 4 new adapter tests (both reasoning field names, absent reasoning, timeout policy) | `tests/test_adapter.py` |
| `max_concurrency: 8` for R2–R4; R1 `max_concurrency: 2` and a `serving:` block (flash attention, q8_0 KV cache, `NUM_PARALLEL=2`, `KEEP_ALIVE=-1`); R5 `enabled_in_main_runs: false` and `effort_note`; R1–R4 `enabled_in_main_runs: true` | `config/models.yaml` |
| New section "Starting Ollama for R1" | `README.md` |
| Schema changes (new fields) | `reports/schema-changes.md` (new) |
| Smoke results re-run on fresh caches; earlier copies kept | `results/stage01/smoke_R1..R4.json`, `results/stage01/before-03b/` |

### Smoke tests 1–4

R1–R4 all pass with the new settings. `max_concurrency: 8` was tested live on R2–R4 with no 429s.

`reasoning_text` in the fresh smoke calls: R1 12/12, R3 12/13. R2 and R4 return none (R4 replies carry `reasoning: null`).

### R1 serving and latency (A1/A4)

Server started with `OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_NUM_PARALLEL=2 OLLAMA_KEEP_ALIVE=-1`. `ollama ps`: 13 GB, 100% GPU, context 65536, "Forever". The long-context (about 20k tokens) test passed, so the revert rule did **not** trigger.

| R1 measure | Earlier session (defaults) | Tuned |
|---|---|---|
| 4k-prompt median | 14.8 s | 19.0 s |
| structured-output median | 11.9 s | 13.45 s |
| 20k long-context call | 74.9 s | 108.9 s |

**These do not show a speed-up; the tuned figures are slower, but the comparison is confounded.** A same-session A/B gave:

- concurrency 1: about 3.2 calls/min tuned versus 3.16 calls/min with defaults (about 18.5–19 s per call);
- concurrency 2: about 3.4 calls/min, with per-call time doubling to 35–38 s.

So the slowdown between sessions is machine-state drift, not the flags, and `NUM_PARALLEL=2` with concurrency 2 gives **no measurable throughput gain** on this Mac (M1 Max, 64 GB). The 20k figures are noisy (a default-server 20k call took 25.6 s in one repeat, so the 74.9 s and 108.9 s values are not reliable). A clean tuned-versus-default 20k comparison was not completed. The settings were applied as decided, since they pass the tests and fit in memory. For Petr: setting both back to 1 costs nothing measurable.

The Ollama menu-bar app respawns its own server (no env vars, `-np 1`). To run the tuned server, quit the app and start `ollama serve` with the variables above (see `README.md`). The app has been restarted and is now running with default settings.

## B. Stage 02 changes

| Change | File |
|---|---|
| Per-operation `oasdiff` columns (`--match-path`): `breaking_err_ops`, `breaking_warn_ops`; patch check v0.10.0 → v0.10.1 (D10) | `nlipeval/tasks/specs.py`, `results/specs/breaking_changes.csv`, `breaking_crossed.csv`, `breaking_patch_v0.10.1.csv` |
| Catalogue corrections D6–D8, `changed_meaning` definition in header, `status: reviewed` | `nlipeval/tasks/build_catalogue.py`, `specs/changes/L1.yaml`, `L2.yaml`, `L3.yaml` |
| Prompt excerpts without examples, as compact JSON and YAML | `specs/excerpts_prompt/<api>/<version>.{json,yaml}` (`specs/excerpts/` unchanged) |
| Token sizes per version on R1–R4 | `nlipeval/tasks/prompt_sizes.py`, `results/specs/prompt_excerpt_sizes.csv` (112 rows) |
| 5 new tests | `tests/test_specs_catalogue.py` |

### Breaking-change columns

`breaking_ops` counts only operations that exist in both versions. Some counts differ from the all-paths figures, for example L3 v0.8.1 crossed 21 → 14 operations, and L1 v0.5.1 step 1 6 → 1 error operations. The D10 optional check, L3 v0.10.0 → v0.10.1: 0 ERR, 11 WARN, 18 changes.

### Catalogue counts (entries carrying each kind, before → after)

| API | Kind | Before | After |
|---|---|---|---|
| L1 | changed_meaning | 2 | 0 |
| L1 | restructured | 4 | 4 (as primary kind 2 → 4) |
| L2 | changed_meaning | 2 | 4 |
| L2 | removed | 3 | 0 |
| L3 | changed_meaning | 2 | 2 (`notificationUrl`, request and response; unchanged) |

Other kinds are unchanged. L3 entries now carry response-side relaxation notes for `startedAt` and `expiresAt` (optional from v0.11.0). The `changed_meaning` tests assert L3 has only `notificationUrl` and L2 has `verificationResult` and `verificationResult=UNKNOWN`.

### Prompt excerpt sizes (tokens, sum over 14 versions per rung)

| | R1 | R2 | R3 | R4 | All four |
|---|---|---|---|---|---|
| compact JSON | 80,982 | 83,064 | 79,865 (not re-measured) | 83,234 | 327,145 |
| YAML | 93,566 | 100,563 | 91,472 (not re-measured) | 93,104 | 378,705 |

Stage 07b re-measured R1, R2 and R4 after the callback summaries were added to the L3 excerpts (JSON +134, +145 and +163 tokens; before: 80,848, 82,919 and 83,071). The R3 endpoint was unreachable at that time, so the R3 column is still the stage 03b figure. The R3 rows should be re-measured with `uv run python -m nlipeval.tasks.prompt_sizes R3` once it is back.

Decision: use **compact JSON** for all prompts (fewer tokens). The largest prompt, L3 v1.1.0, is 14.0–14.6k tokens in JSON, 16–17.5k in YAML, and about 29.6k (approximate) for the reference excerpt. Sizes were measured with R1 on the app-default server; the tokenizer is the same either way. The L3 server prompt no longer includes the QoS Profiles excerpt (stage 06).

## C. Stage 03 changes

| Change | File |
|---|---|
| Headline table redone (S2, S3), plus Table 1A (flagged checks) and Table 1B (all checks); "Not tested" note (S4) | `stage1/harness/tables.py`, `reports/stage-03-conformance.md` |
| Deviations written for maintainers (not sent) | `reports/deviations-for-maintainers.md` (new) |
| Readings of A1–A7, with verdicts | `reports/review-readings-A1-A7.md` (new) |

Headline, 32 unflagged checks: `nlip_sdk` 17/23, `nlip_server` minimal app 20/24, TypeScript client 6/9, echo app 20/24, ours 32/32. All 49 checks: `nlip_sdk` 17/27, `nlip_server` 21/40, echo app 27/40, TypeScript client 6/9, ours 49/49. A3, A4 and A6 remain in the headline, as noted in the readings.

## D. Validation

`experiments/.venv/bin/python -m pytest -q`: 114 passed.
