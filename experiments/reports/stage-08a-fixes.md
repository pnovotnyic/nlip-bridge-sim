# Stage 08a: fixes before the pilot

Status: parts A–E and G done, and the review fixes H1–H6 (`bob_plan/reviews/review-stage-08a.md`). F14 done. **Petr approved the prompts (A1–A4), the renderer rules, the task sheet and the P3 notes on 18 November.** F15–F17 are next. Nothing of the pilot has been run with the new code.

Every fix applies to every rung alike. The evidence is the R1 test runs `20261117-2329-stage8-pilot-r1` (63 sessions, old repository) and `20261118-1905-stage8-pilot-r1` (here); see `bob_plan/reviews/review-stage-07b-and-pilot-start.md` §2. The fixes are also to be recorded in `reports/stage-08-pilot.md`, with this evidence, when that report is written.

## Hashes

| | Before | After |
|---|---|---|
| `prompts_hash` | `7f0909b2…57` (test run manifest) | `703fb282007f5b4fc3215b87954ace3c2c4a7643279544e8439dc9bdcef28141` |
| `tasks_hash` | `4fed2c44…36a` (test run manifest) | `85356e0cd72d8b544b2b2da1cb1f2045e6e70d677537725a3ad2cc0602e3aac8` |
| `SCORER_VERSION` | 1.1.0 | 1.2.0 |

## Fixes

### A. Turn contract (templates in `prompts/`)

| # | Fix | Files | Evidence |
|---|---|---|---|
| A1 | A `restate` ends by asking the client to confirm or correct; an `ask` ends with a question. The client is told that a described call is waiting for `confirm` or `correct`, and never to send `request` again. | `server_P1/P2/P3.txt`, `client_P1/P2/P3.txt` (not NLIP-0: it has no restatements) | 12 of 30 NLIP sessions on the 17th and 7 of 9 on the 18th ended `error_model` after a repeated `request` |
| A2 | Server: a `report` gives every field and value, or the error status and code (all four server templates). Client: put in `result` only what the server reported (all four client templates). | all 8 templates | invented timestamps from 2023 and 2024 |
| A3 | Server: the harness sets every header; the plan holds `method`, `path`, `body`; never decline for a missing header. | all 4 server templates | "the request requires a correlation ID header" |
| A4 | The setting, appended to the role line of every template. Server: "Your clients may have been built against older versions of this API. Serve their requests with your own version's interface." Client: "The server may implement a different version of this API than yours." | all 8 templates | a server declined with "implements L2 v3.0.0, not v0.1.0" |
| A5 | Prompts re-rendered; `prompts_hash` recomputed; `reports/review-prompts.md` regenerated (`scripts/gen_review_prompts.py`); sizes re-measured on R1–R4 (`results/prompts/prompt_sizes.csv`, largest prompt now 15,707 / 16,333 / 15,625 / 16,252 tokens on R1/R2/R3/R4, all client L3 v1.1.0 P3). | `results/prompts/prompt_sizes.csv` | |

A4 stays unless Petr decides otherwise at the prompt review.

### B. Session state machine

| # | Fix | Files |
|---|---|---|
| B6 | One repair for a disallowed action, in every state of the table of §B (client: first turn, after ask, after restate, final turn; server NLIP: after request/answer/correct, after execution; server NLIP-0: after request, after execution and the retry). The message is "Your reply used action `<x>`, which is not allowed now. Allowed: `<list>`. Reply again." and the call is logged with purpose `repair`. A second disallowed action ends the session `error_model` (`action_failure` is a model failure in `_fail`). `n_action_repairs_client` and `n_action_repairs_server` are counted per agent and written to `sessions.jsonl`. Server `execute` before confirmation (NLIP) and `ask`/`restate` in NLIP-0 are not repaired: they stay protocol slips, as before. The client's `answer` after a `restate` is no longer taken as a confirmation (it is repaired). | `nlipeval/agents/repair.py` (new), `agents/client.py`, `agents/server.py`, `runner/session.py`, `runner/run.py` |
| B7 | After a server `decline` or a client `abort` the harness asks for the client's `final` (with the B6 repair). Termination stays `declined`. The `final` step is now one function for all paths (`_client_final`); a missing `final` object is still a slip. An abort after a backend rejection also ends this way. | `runner/session.py` |

Evidence for B7: 3 declined sessions and 2 aborts ended with no `client_final`.

### C. Scoring (scorer 1.2.0)

| # | Fix | Files |
|---|---|---|
| C9 | Required fields of the answer schema must be present and correct; an optional field must be correct if present, and if absent the answer is correct with `response_incomplete: true` in `scores.jsonl`. A present but wrong optional value is wrong. `device` and `ueId` are removed from `config/answer_schemas/` (L2 v3.0.0 and all of L3); if a model returns one it is accepted when it equals the native request's value, and wrong otherwise. Any other extra field is wrong. `compare_response_understanding` returns a fourth value, `response_incomplete`. | `scoring/compare.py`, `scoring/score.py`, `config/answer_schemas/L2.yaml`, `L3.yaml` |
| C10 | L1 precedence: for a DATA+SMS device at v0.5.1 and v0.6.0, `CONNECTED_SMS` is accepted through `gold_client_answer.alternatives` (primary `CONNECTED_DATA`). 34 instances (24 main, 10 pilot). `NOT_CONNECTED` and `unrepresentable` stay wrong. The rule is in `reports/review-renderer-rules.md`. | `tasks/render/l1.py`, `tasks/L1/*.json`, `reports/review-renderer-rules.md` |

Evidence for C9: 7 sessions failed only because an optional time was missing or a `device` echo was added.

### D. Tasks

| # | Fix | Files |
|---|---|---|
| D11 | Phone numbers render without "+" where the intent number mod 4 is 1 or 2 (was: even numbers). The gold keeps "+"; the tagging rule is unchanged. Tasks regenerated (`python -m nlipeval.tasks.generate`), coverage and prompt-half tables recomputed, `reports/review-tasks.md` regenerated. | `tasks/render/ids.py`, `render/l1.py` and `l2.py` (docstrings), `tasks/`, `results/tasks/*.csv`, `reports/review-tasks.md`, `reports/review-renderer-rules.md` |

Result: L1 `unit_format` goes from 5 instances (0 in the prompt half) to **6 instances, 3 in the prompt half**. That is still below the 5 the stage 3 ablation needs; L3 `changed_meaning` is unchanged (8, 4 in the half). Both are known gaps of stage 05 for Petr to decide on; the half is fixed by the odd/even `prompt_half` rule. The 263 changed task files carry the new phone forms, the L1 alternatives (C10) and the removal of `device` and `ueId` from `client_answer_schema` (C9); the last is why the diff has more deletions (738) than insertions (266).

### E. Small items

| # | Fix |
|---|---|
| E12 | `test_launcher_http` now points `launcher.STATE_FILE` at a file in `tmp_path` (monkeypatch). It no longer reads, skips on, restores or deletes the real `.backends/state.json`. |
| E13 | R3 excerpt sizes re-measured (`results/specs/prompt_excerpt_sizes.csv`, 12 L3 rows changed by 13–28 tokens; R3 answered). |

## Tests

`.venv/bin/python -m pytest tests`: **2366 passed** after H1–H6 (2349 before them) (before: 2344 passed, 5 skipped; the 5 skips were end-to-end tests and `test_launcher_http`, which skipped because backends were running; the last run had no skips).

New tests (`tests/test_harness.py`, `tests/test_scoring.py`):

- B8 — repeated `request` repaired, then confirmed, session succeeds, counters (1, 0); a disallowed action twice gives `error_model`; client `answer`/`final`/non-final cases; server `report` before execution, `ask` after execution, twice-disallowed; NLIP-0 server and client repairs; slips not repaired in either condition; repair call logged with purpose `repair`; abort (after ask and after restate) followed by `final`, status `declined`; abort then a non-final repaired; server decline followed by `final` (NLIP and NLIP-0); decline without a `final` object ends `error_model`; counters reach the session record.
- C9 — one test per rule (required missing; optional absent → correct and incomplete; complete → not incomplete; optional wrong → wrong; `response_incomplete` in `scores.jsonl`; echo fields not in the schemas; echo equal to the native request accepted, other value wrong; unknown extra field wrong).
- C10 — either value accepted at v0.5.1 and v0.6.0, `NOT_CONNECTED` and others wrong; only DATA+SMS devices carry the alternative (34 instances).
- D11 — `test_phone_without_plus_in_intents_1_or_2_mod_4` (replaces the even-number test) with the A11 tests of 07b.
- Existing tests changed: `NLIP_ABORT` in `fake_model.py` now ends with a `final`; the two missing-`final` tests use a `final` action without a `final` object (a non-final action is now repaired first); the scorer-version test expects 1.2.0.

Oracle 510/510 and null 0/510 still hold.

## Fixes after the review (H1–H6)

From `bob_plan/reviews/review-stage-08a.md` §2. H1 and H2 are provenance; H3–H6 change the session state machine, alike for every rung. None changes a template, so `prompts_hash` is unchanged; `tasks_hash` is unchanged.

| # | Fix | Files | Evidence |
|---|---|---|---|
| H1 | The manifest records `git_dirty` and `git_dirty_paths`: uncommitted changes, untracked files included, under `nlipeval/`, `prompts/`, `tasks/`, `config/`, `specs/`, `scripts/`, `pyproject.toml`, `uv.lock`. A run does not start with such changes unless its matrix sets `allow_dirty: true`; such a run is registered with status `test`. A run that already has a manifest is resumed only if `git_commit` and the five hashes are unchanged; the first `created_utc` is kept and each resume is added to `resumed_utc`. All of 08a is committed before F15. | `runner/run.py` | 08a was uncommitted, so a run would have recorded `0401f07`, which has none of it |
| H2 | `pilot-r1.yaml` no longer fixes `run_id` (it named the test run, which F15 would have resumed). Generated IDs use the matrix's `stage` (was `-stage6-` in the code). `--run-id` resumes an interrupted run. New `pilot-rits.yaml` with R2–R4; with `pilot-r1.yaml` it makes up `pilot.yaml` exactly (120 + 300 = 420 sessions, tested). | `config/runs/pilot-r1.yaml`, `pilot-rits.yaml` (new), `runner/run.py` | |
| H3 | NLIP-0 report: no parse, or no allowed action after the repair, ends `error_model` (was `error_harness`), as under NLIP. | `runner/session.py` | reproduced: `request, execute, ask, ask` ended `error_harness` |
| H4 | NLIP-0 after a backend rejection: a `report` from the server is its report (it was discarded, and the server asked again with the backend result repeated in its history). A `restate` there is logged as a protocol slip and its plan retried; a reply that does not parse ends `error_model` (was ignored). | `runner/session.py` | reproduced: 3 server calls (`plan, report, report`) |
| H5 | The client's `confirm` is added to its own history before the execution, so its `final` call no longer sees the restatement and the report as consecutive user turns. The stale `results/pilot/*.csv` (11 sessions of the test run, older `pilot_checks.py`) are deleted. | `runner/session.py`, `results/pilot/` | |
| H6 | After a backend rejection the server's restatement goes back through the general restate step. A `correct` there is now sent to the server, whose new plan is executed (before, the correction was counted but never sent, and the rejected-then-restated plan was executed anyway); `confirm` and `abort` are as before. A restatement is allowed only after the first execution, as before; after a later one only `report` (repaired otherwise). A server `execute` answering a client message is a protocol slip at any point (it was one only before the first confirmation). Counts of restatements and interactions are unchanged (tested). | `runner/session.py` | found while doing H5 |

Tests added: `TestNlip0Report` (5), `TestClientConfirmInHistory` (2), `TestCorrectionAfterRejection` (4), `TestRunProvenance` (6) in `tests/test_harness.py`.

## Bookkeeping

- `reports/schema-changes.md`: `n_action_repairs_client`, `n_action_repairs_server`, `response_incomplete`, `gold_client_answer.alternatives` on L1, the `termination` note, and the answer-schema change.
- `data/RUNS.md`: `20261118-1905-stage8-pilot-r1` registered with status `test` (F14). It has 41 sessions, not 18: the run was still going when I started 08a, so I stopped it. It is never analysed. Its git commit is `0401f07`.
- `scripts/pilot_checks.py` now reports the three F15 criteria: `error_model` sessions, sessions with an action repair, sessions with no `client_final`.
- `reports/review-prompts.md`, `reports/review-tasks.md`, `reports/review-renderer-rules.md` regenerated or updated for Petr's reviews. The P3 notes are unchanged by 08a.
- `reports/schema-changes.md`: `git_dirty`, `git_dirty_paths`, `resumed_utc` in `manifest.json`; the NLIP-0 retry `restate` counted in `n_protocol_slips`.

## Not done yet

- **F15** the first 10 R1 sessions of the pilot matrix (`config/runs/pilot-r1.yaml`), with the stop rule (more than 1 `error_model`, more than 3 action repairs, any `final` or `declined` session without `client_final`). The first 10 are all L1 (p01, p02); the review proposes the same check on R1 sessions 31–40 (L2) and 61–70 (L3).
- **F16** the pilot from scratch under new run IDs: R1 with `scripts/start_ollama_r1.sh`, concurrency 1, under `caffeinate -i`; R2–R4 with `config/runs/pilot-rits.yaml`.
- **F17** R1's speed figures for the stage 08 report (the test runs: about 35 s per call, 1,250–1,430 output tokens, sessions of about 175 s and 129 s, about 52 h projected for stages 09–10). `results/prompts/time_projection.csv` has not been regenerated; it uses the pilot figures.

## Next

F15, then F16, F17.
