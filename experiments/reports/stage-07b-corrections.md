# Stage 07b: corrections to stages 05–07

Plan: `bob_plan/07b-corrections-to-stages-05-07.md`. Review: `bob_plan/reviews/review-stages-04b-07.md`. Petr's decisions 1–5 were taken as the review recommends them.

Rules followed throughout: every gold answer is reachable from what the agents are given; every tag describes what the instance exercises; the gold is never checked against itself.

Commits: A `aed2b3d`, B `58f8f16`, C–D `2ed697d`, E and size files in the final commit.

Test status: 2361 passed, 6 skipped (`cd experiments && uv run pytest -q`).

## 1. Changes by part

### A. Task instances (A1–A13), commit `aed2b3d`

| Area | Files |
|---|---|
| Intent definitions, renderers, generator, gold derivation, tags | `nlipeval/tasks/**`, `config/intents/*.yaml` |
| Regenerated task files and index | `tasks/**`, `results/tasks/*` |
| Catalogue and spec tables that the tags depend on | `results/specs/*` |
| Review sheets regenerated | `reports/review-renderer-rules.md`, `reports/review-tasks.md` |
| Reports | `reports/stage-05-tasks.md`, `reports/stage-02-specs.md` |

Result: 510 task instances (420 main, 90 pilot). Declined, refusal and unrepresentable tasks each carry an `expected_refusal`, and none is `refusal_predictable`. The oracle test builds executed calls for those tasks, and the null agent scores 0 of 510.

Known gap: L3 v0.8.1 to v0.10.0 answers cannot echo the `device` and `ueId` fields that the spec lists as required. `strict.py` ignores those two errors (the `ECHO_REQUIRED` set).

### B. Prompts and harness (B1–B12), commit `58f8f16`

| Area | Files |
|---|---|
| Prompt templates, schemas, server | `nlipeval/agents/{prompts,schemas,server}.py`, `prompts/*.txt` |
| 14 P3 notes with sources, and a test | `prompts/notes/<api>/<version>{,.sources}.md`, `tests/test_notes.py` |
| Session and run changes, `session_limit_s` per rung | `nlipeval/runner/{run,session}.py`, `config/models.yaml` |
| Run matrices (`smoke-r3`, `pilot`, edited `stage2-main`; `pilot-r3-p2` removed) | `config/runs/*.yaml` |
| Deadline on every model call | `nlipeval/models/adapter.py` |
| Real-tokenizer prompt sizes (replaces the chars/3.5 estimate) | `nlipeval/agents/prompt_sizes.py`, `nlipeval/tasks/prompt_sizes.py` |
| Time and cost projection | `scripts/project_time_cost.py`, `results/prompts/{time_projection,r5_cost}.csv` |
| Review sheet and reports | `reports/{review-prompts,schema-changes,stage-06-harness}.md` (about 15 new 07b rows in `schema-changes.md`) |
| Run register | `data/RUNS.md` |

Prompts hash after 07b: `7f0909b25c63335596d132311e986c32b05c9a3ea6e8e644b31f8d05574c0357`. It changes if a template or note changes.

### C and D. Scorer 1.1.0 and aggregates, commit `2ed697d`

| Area | Files |
|---|---|
| Scorer | `nlipeval/scoring/{score,compare}.py` |
| Aggregates: `compute_breaking` reads the cell value from `results/specs/catalogue_breaking_crossed.csv` and adds `_mean`; new `compute_breaking_by_instance`; `compute_effects` gains `n_missing_info_tasks` and `asked_when_needed_share` | `nlipeval/analysis/{aggregates,__init__}.py` |
| Tests (about 20 new scoring tests, 3 new analysis tests) | `tests/test_scoring.py`, `tests/test_analysis.py` |

Scorer rules as implemented:

- `device` is excluded from the body comparison. `judge_device` uses the backend record, or `resolve_device_offline` (`nlipeval/backends/identify.py`) when there is none.
- Refusal tasks are judged by the last call's status and code.
- The unknown-profile case applies when the task is L3, the gold body has `qosProfile`, and either the gold backend status or `expected_refusal.status` is 404. Any 4xx counts if the call matches except for `qosProfile`.
- `match_asked_fields` implements C7.
- Backend records are matched by `seq`.

### E. Bookkeeping

| Area | Files |
|---|---|
| Scoring report (version 1.1.0, new sections 2.2, 4 and 5) | `reports/stage-07-scoring.md` |
| Size table in the 03b report | `reports/stage-03b-corrections.md` |
| Excerpt sizes | `results/specs/prompt_excerpt_sizes.csv` |
| Status table | `STATUS.md` |
| This report | `reports/stage-07b-corrections.md` |

## 2. Before and after (420 main instances)

The "before" values are kept in `results/tasks/before_07b.json`. The "after" values are in `results/tasks/{gold_status,missing_info_share,coverage,prompt_half_coverage}.csv`.

### Gold status

| API | Stage | done before | done after | declined before | declined after | unrepresentable before | unrepresentable after |
|---|---|---|---|---|---|---|---|
| L1 | 2 | 28 | 30 | 2 | 0 | 0 | 0 |
| L1 | 3 | 56 | 60 | 4 | 0 | 0 | 0 |
| L2 | 2 | 23 | 25 | 7 | 5 | 0 | 0 |
| L2 | 3 | 92 | 99 | 16 | 8 | 12 | 13 |
| L3 | 2 | 28 | 30 | 2 | 0 | 0 | 0 |
| L3 | 3 | 140 | 150 | 10 | 0 | 0 | 0 |

### `missing_info` share (instances needing a question to the user)

| API | Version | Before | After |
|---|---|---|---|
| L1 | v0.5.1, v0.6.0, v1.0.0 | 0/30 each | 2/30 each (6.7%) |
| L2 | v0.1.0 | 30/30 | 6/30 (20%) |
| L2 | v0.2.0, v1.0.0, v2.0.0, v3.0.0 | 0/30 each | 2/30 each (6.7%) |
| L3 | v0.8.1 | 7/30 | 10/30 (33%) |
| L3 | v0.9.0, v0.10.0, v0.11.0, v1.0.0, v1.1.0 | 0/30 each | 4/30 each (13.3%) |

Overall: 50 of 420 main instances.

### Coverage: Stage 3 instances per kind ("either" direction)

| Kind | L1 before | L1 after | L2 before | L2 after | L3 before | L3 after |
|---|---|---|---|---|---|---|
| renamed | 30 | 30 | 20 | 30 | 42 | 44 |
| restructured | 60 | 60 | 30 | 30 | 30 | 40 |
| unit_format | 10 | 5 | 40 | 30 | 82 | 96 |
| newly_required | 0 | 0 | 103 | 105 | 66 | 78 |
| changed_meaning | 0 | 0 | 30 | 37 | 8 | 8 |
| removed | 0 | 0 | 0 | 0 | 0 | 0 |

### Prompt-half counts per kind (n of the Stage 3 instances)

| Kind | L1 before | L1 after | L2 before | L2 after | L3 before | L3 after |
|---|---|---|---|---|---|---|
| renamed | 15 | 15 | 11 | 15 | 21 | 23 |
| restructured | 30 | 30 | 15 | 15 | 14 | 21 |
| unit_format | 5 | 0 | 20 | 15 | 41 | 49 |
| newly_required | 0 | 0 | 50 | 48 | 33 | 39 |
| changed_meaning | 0 | 0 | 15 | 23 | 4 | 4 |

L3 `changed_meaning` has 4 prompt-half instances. L1 `unit_format` has 5 instances and none in the prompt half, so the prompt-vs-no-prompt effect for that cell cannot be estimated.

## 3. Prompt sizes (tokens, real tokenizers, `results/prompts/prompt_sizes.csv`, 68 rows)

Min–max over all task/version combinations:

| Variant | Role | R1 | R2 | R3 | R4 |
|---|---|---|---|---|---|
| P1 | server | 2787–14979 | 2959–15527 | 2785–14905 | 2895–15508 |
| P2 | server | 2868–15060 | 3045–15613 | 2865–14985 | 2976–15589 |
| P3 | server | 3069–15439 | 3251–16009 | 3063–15352 | 3182–15981 |
| NLIP-0 | server | 2802–14994 | 2976–15544 | 2800–14920 | 2912–15525 |
| P1 | client | 2188–15194 | 2335–15799 | 2146–15124 | 2212–15726 |
| P2 | client | 2255–15261 | 2407–15871 | 2213–15191 | 2279–15793 |
| P3 | client | 2457–15640 | 2614–16267 | 2431–15558 | 2503–16185 |
| NLIP-0 | client | 2180–15186 | 2329–15793 | 2138–15116 | 2204–15718 |

The largest prompt is the L3 v1.1.0 client at P3: 16,267 tokens on R2. R2 means: server 7,714, client 7,196. R1 counts come from Ollama's `prompt_tokens`.

Excerpt sizes (`results/specs/prompt_excerpt_sizes.csv`, sum over 14 versions):

| | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| JSON before | 80,848 | 82,919 | 79,865 | 83,071 |
| JSON after | 80,982 | 83,064 | 79,865 (not re-measured) | 83,234 |
| YAML after | 93,566 | 100,563 | 91,472 (not re-measured) | 93,104 |

The rise is 134–163 tokens per rung (callback summaries in the L3 excerpts). The plan expected about 40 tokens per L3 version; the result is below that. The R3 column is the old figure because the R3 endpoint was down (section 6).

## 4. Time and cost projections

`scripts/project_time_cost.py <smoke-run-dir>`. Assumptions: 5 calls per NLIP session plus 2 per interaction, 4 per NLIP-0 session; per-call latency from 03b/04b (R1 13.07 s, R2 5.8 s, R3 1.8 s, R4 28 s); concurrency 1 for R1 and 8 for the others. In the smoke run, calls on R3 were about 4.05 times slower than the stage 01 median, so R2–R4 also have a scaled estimate. R1 is not scaled.

Hours per stage and rung, unscaled / scaled:

| Stage | Sessions per rung | R1 | R2 | R3 | R4 |
|---|---|---|---|---|---|
| 08 pilot | 90–120 | 2.0 | 0.1 / 0.3 | 0.0 / 0.1 | 0.4 / 1.6 |
| 09 stage 2 | 180 | 3.0 | 0.2 / 0.7 | 0.1 / 0.2 | 0.8 / 3.3 |
| 10 stage 3 | 990 | 17.4 | 1.0 / 3.9 | 0.3 / 1.2 | 4.7 / 18.9 |
| Total | | 22.4 | 1.3 / 4.9 | 0.4 / 1.5 | 5.9 / 23.8 |

R1 stages 09 and 10 together: 20.4 hours.

R5 (stage 14, 840 sessions, about 3,880 calls): about 30 M input tokens and 1.3–2.6 M output tokens, **about $145–177** depending on the tokenizer and the output length ($145–151 with the R3 smoke output lengths; $171–177 with output doubled). The old estimate in `stage-06-harness.md` was about $280.

Caveats: call counts use the share of instances with `missing_info` as k. Input tokens use the smoke run's history overhead (client about 136, server about 202 tokens) on top of the system prompt, so longer sessions may be understated.

## 5. Smoke run

Run `data/runs/20261113-2205-stage6-smoke-r3/` (R3, 12 sessions: pilot instances L1, L2 and L3, two client versions each, NLIP and NLIP-0). Two earlier runs are registered as `smoke-superseded` in `data/RUNS.md`.

| Check | Result |
|---|---|
| Sessions finished with termination `final` | 12 of 12 |
| Errors, parse failures | 0, 0 |
| Protocol slips | 0 |
| Wire valid | yes |
| Backend calls | all 2xx, except one 404 (below) |
| Request correct | 12 of 12 |
| Harmful calls | 0 |
| End-to-end correct | 6 of 12 |
| Session time | 23–44 s; per call: client 3–6 s with about 5.9k input tokens, server about 9.5 s with 7.5–8k input tokens |

Sessions:

| Task | Condition | Calls (status, path) | Client final | Seconds |
|---|---|---|---|---|
| L1 v1.0.0 | NLIP | 200 `/device-reachability-status/v1/retrieve` | done | 33 |
| L1 v1.0.0 | NLIP-0 | 200 same | done | 29 |
| L1 v0.5.1 | NLIP | 200 same | none (slip) | 36 |
| L1 v0.5.1 | NLIP-0 | 200 same | unrepresentable | 39 |
| L2 v3.0.0 | NLIP | 200 `/location-verification/v3/verify` | done | 26 |
| L2 v3.0.0 | NLIP-0 | 200 same | done | 43 |
| L2 v0.1.0 | NLIP | 200 same | done | 39 |
| L2 v0.1.0 | NLIP-0 | 200 same | done | 29 |
| L3 v1.1.0 | NLIP | 201 `/quality-on-demand/v1/sessions` | done | 44 |
| L3 v1.1.0 | NLIP-0 | 404 `/sessions`, then 201 `/quality-on-demand/v1/sessions` | done | 23 |
| L3 v0.8.1 | NLIP | 201 same | done | 37 |
| L3 v0.8.1 | NLIP-0 | 201 same | done | 38 |

The one 404: the NLIP-0 server posted `/sessions`, saw the 404, and then used the full path. Scored request-correct, as C1 requires.

Six sessions failed end to end; every failure is on the model or answer side:

- L1 v0.5.1 NLIP: the client's last turn was `confirm` with no `final` object. Counted as a protocol slip and the answer is missing (this check was added after the run showed it; see defect 5).
- L1 v0.5.1 NLIP-0: the client answered `unrepresentable`, but gold is `CONNECTED_DATA` (open question below).
- L3 v1.1.0, both conditions: the client added `device` to its answer; flagged as "unexpected field result.device".
- L3 v0.8.1, both conditions: the client's `expiresAt` was wrong; it made up the Unix times.

All aggregate functions ran on the smoke run. The smoke tasks are pilot instances (`pilot` is True in `INDEX.csv`), and the aggregates exclude pilot rows, so most tables are empty by design. I did not change `load_data`.

### Harness defects found by the smoke run (all fixed)

1. **Client history.** The client was given `[Start session] …` as a user turn, so the model took each server reply as a new prompt. The history now opens with the user turn "Begin the session.", agent replies are JSON assistant turns, and the backend report is appended to the server history.
2. **`plan.path`.** The server returned an operation-only path or a full URL with host. The four server templates and `SERVER_SCHEMA` now ask for the full request path: the base path of the servers URL followed by the operation path, starting with `/`, with no scheme or host. The harness does not repair paths; a wrong path is a rejected call.
3. **Session IDs.** `calls.jsonl` and `sessions.jsonl` had different IDs. `SessionConfig.session_id` is now shared with the agents.
4. **Stalled HTTP read.** A read with no overall deadline hung a run for 34 minutes. `_create_with_deadline` in `nlipeval/models/adapter.py` now bounds every try by wall-clock time. It is also used by both `prompt_sizes.py` modules. Test: `tests/test_adapter.py::test_create_with_deadline_bounds_a_stalled_call`.
5. **Missing `final`.** A client whose last turn has no `final` object counts as a protocol slip (`_note_missing_final` in `session.py`; tests `TestMissingFinal`).
6. **Stale backends.** A stale `.backends/state.json` pointing at dead backends caused 500s. Delete it and run `pkill -f nlipeval.backends.launcher` before a run, and after removing a run directory.

## 6. Open items

**L1 gold precedence (needs Petr's decision).** For L1 v0.5.1 and v0.6.0, the gold is `CONNECTED_DATA` for devices with both DATA and SMS. No text the agents are given states that precedence rule. It affects 12 of 30 main instances at each of the two versions. In the smoke run an R3 client answered `unrepresentable`. Options: keep the gold, accept either value, or make it `unrepresentable`. Also noted in `stage-06-harness.md`, "Open questions".

**R3 endpoint outage.** The R3 endpoint (gpt-oss-20b on RITS) stopped answering at about 19:00 local time on 2026-11-13 (connection timeouts on `/models`) and was still down at the end of this stage. R2 and R4 answer. Effect: the R3 rows of `results/specs/prompt_excerpt_sizes.csv` are the stage 03b figures, not re-measured after the callback summaries. Re-run `uv run python -m nlipeval.tasks.prompt_sizes R3` once the endpoint is back. The R3 rows of `results/prompts/prompt_sizes.csv` were measured while it was up.

**Before the pilot (stage 08)** Petr still has to review the renderer rules (`reports/review-renderer-rules.md`), the task sheet (`reports/review-tasks.md`), the prompts (`reports/review-prompts.md`) and the 14 P3 notes.
