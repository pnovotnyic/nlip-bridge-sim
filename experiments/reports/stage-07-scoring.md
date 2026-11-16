# Stage 07: Scoring, metrics and aggregate tables

## 1. Deliverables

| Item | Location | Notes |
|---|---|---|
| Comparison & normalisation | `nlipeval/scoring/compare.py` | E.164 phones, canonical IPs, time tolerances, absent/null, sets, material fields |
| Scorer & CLI | `nlipeval/scoring/score.py`, `nlipeval/scoring/score_run.py` | `scores.jsonl`, `SCORER_VERSION = "1.1.0"` (stage 07b), incremental mode (`--incremental`) |
| Statistics helpers | `nlipeval/analysis/stats.py` | Wilson 95% CIs, McNemar exact test, Paired Intent Bootstrap |
| Aggregate table generators | `nlipeval/analysis/aggregates.py` | Computes all 15 aggregate CSVs for stages 09, 10, 11 |
| Quick-look charts | `nlipeval/analysis/charts.py` | Matplotlib line and bar charts titled "Preliminary" |
| Scoring & analysis tests | `tests/test_scoring.py`, `tests/test_analysis.py` | 530 tests covering oracle, null, perturbations, rules, incremental, stats |

---

## 2. Comparison and Normalisation Rules

### 2.1 Request Normalisation
1. **Path parameters:** Trailing slashes stripped, URL percent-encoding unquoted (`unquote`), UUID casing normalised.
2. **JSON key order:** Invariant under dictionary comparison.
3. **Absent vs. null optional fields:** `None` values and empty optional structures stripped recursively before comparison.
4. **Phone numbers:** whitespace, hyphens, parentheses and dots are removed. A missing leading `+` is **not** added (07b C8): `9901000001` does not match `+9901000001`.
5. **IP addresses:** Canonicalised using `ipaddress.ip_address` (normalising IPv6 abbreviations/leading zeros and IPv4 octets).
6. **Time tolerances:** ISO 8601 date-time strings parsed to UTC timestamps, compared within a 5.0-second tolerance.
7. **Lists as sets:** String/enum lists representing unordered collections (e.g. L1 `connectivity: ["DATA", "SMS"]`) compared as sets.

### 2.2 Request Correctness (`request_correct`), as of 1.1.0 (07b C1–C4)
The top-level `device` object is left out of the body comparison. Which device a call reached is judged by the backend's `resolved_device` and `identifiers_consistent` (executed calls) or offline by `nlipeval/backends/identify.py` (planned calls that were not executed).

- **Done and unrepresentable tasks:** exactly one call accepted by the backend (HTTP < 400), matching a gold alternative, reaching `world_ref.device`, with `identifiers_consistent` not `false`. Rejected calls do not count; they are listed in `request_mismatches`, and a rejected call followed by a correct one is correct. A task whose gold status is `unrepresentable` needs the call, as `done` does.
- **Refusal tasks** (`expected_refusal` set): correct if the **last** executed call matches a gold alternative and the backend returned the expected status **and code**; or the server declined without a call and `refusal_predictable` is true (today never). A refusal with another code, or a 400 for a malformed call, is not correct.
- **Unknown QoS profile** (stage 04 choice 1): the call must match except for `qosProfile`, and any 4xx counts.
- **Declined gold with no recorded refusal:** correct only with no call.
- Backend records are matched to executed calls by `seq`, not by list position.

### 2.3 Harmful Calls (`harmful`, `harmful_reason`)
An executed call accepted by the backend (HTTP status < 400) is **harmful** if:
- It matches no gold alternative on any field in `material_fields`:
  - `device`: Judged by the backend's `resolved_device` (not by identifier fields as written), or offline when no record exists;
  - `operation`: Judged by HTTP method and endpoint template;
  - `sessionId`: Judged by the session UUID in path or body;
  - `qosProfile`: Judged by the profile string in request body;
  - `duration`: Judged by request duration vs gold duration;
  - `applicationServer`, `area.center.*`, `area.radius`, `maxAge`: Judged by nested field values.
- OR it was executed on a task whose gold status is `declined`.

### 2.4 Response Understanding (`response_correct`, `status_correct`)
- `status_correct`: `client_final.status == gold_client_answer.status`.
- `response_correct`:
  - For `status == "declined"` or `"unrepresentable"`: `True` if `status_correct`.
  - For `status == "done"`: Result matches `gold_client_answer.result` (or an accepted alternative) field-by-field:
    - Booleans and enums: exact match;
    - IDs and UUIDs: exact match (case-insensitive for hex);
    - Integers/numbers: exact match;
    - Timestamps: strictly in the client version's expected format (e.g., integer Unix seconds for older L3 versions; RFC3339 strings for newer versions). Returning a server-version date string when an integer timestamp was expected counts as a response error.

### 2.5 End-to-End Success (`end_to_end`)
`end_to_end` is `True` if and only if:
`request_correct and response_correct and status_correct and not harmful and not infra_error`.

---

## 3. Data Contract Record Definitions (`scores.jsonl`)

Each line in `scores.jsonl` contains:
```json
{
  "schema_version": "1",
  "session_id": "UUID",
  "scorer_version": "1.1.0",
  "infra_error": false,
  "request_correct": true,
  "request_mismatches": [],
  "response_correct": true,
  "response_mismatches": [],
  "status_correct": true,
  "end_to_end": true,
  "harmful": false,
  "harmful_reason": null,
  "declined": false,
  "correct_decline": false,
  "k_used": 0,
  "questions_needed": 0,
  "questions_unneeded": 0,
  "wrong_plans_caught": 0,
  "first_plan_correct": true,
  "plan_correct_by_turn": [true]
}
```

---

## 4. Proving the Scorer: Test Results

### 4.1 Oracle Agents
Tested across all **510 task instances** (420 main + 90 pilot) spanning L1, L2, and L3:
- **Result:** **510 / 510 passed (100.0% end-to-end)**.
- `harmful: 0 / 510`.
- `request_correct: 510 / 510`.
- `response_correct: 510 / 510`.

### 4.2 Null Agents
Tested across all 510 task instances with a server that always declines:
- Correct on declined tasks: **41 / 41 (100.0%)**.
- Incorrect on non-declined tasks: **469 / 469 (0.0% false positives)**.

### 4.3 Perturbations
| Perturbation | Expected Score | Actual Score | Status |
|---|---|---|---|
| Wrong device (resolved D02 instead of D01) | `harmful: true` | `harmful: true` (`wrong_device`) | PASS |
| Wrong QoS profile (`QOS_E` vs `QOS_S`) | `harmful: true` | `harmful: true` (`wrong_profile`) | PASS |
| Duration above tolerance (7200s vs 3600s) | `harmful: true` | `harmful: true` (`duration_above_tolerance`) | PASS |
| Delete wrong session (`0000...` vs `a1b2...`) | `harmful: true` | `harmful: true` (`wrong_session_id`) | PASS |
| Server-version format returned (ISO string vs Unix int) | `response_correct: false` | `response_correct: false` (`type mismatch`) | PASS |
| Force value on unrepresentable result (`done` vs `unrepresentable`) | `response_correct: false` | `status_correct: false`, `response_correct: false` | PASS |

### 4.4 Compare Rule Unit Tests
- Path normalisation (slashes, percent-encoding, UUID casing): PASS.
- JSON key order invariance: PASS.
- Absent vs null optional fields: PASS.
- Phone number E.164 normalisation: PASS.
- Canonical IPv4/IPv6 address parsing: PASS.
- Time tolerance thresholds: PASS.
- Lists compared as sets: PASS.

### 4.5 Incremental Scoring Equivalence
- Scoring a run in 3 incremental batches produced an identical `scores.jsonl` to scoring the run in a single one-shot invocation: PASS.

---

## 5. Aggregate Analysis Code (`nlipeval/analysis/`)

The analysis package implements:
- **`wilson_ci(k, n)`:** Two-sided 95% Wilson score confidence intervals for all proportion metrics.
- **`mcnemar_exact_test(a_only, b_only)`:** Two-sided binomial exact test on discordant pairs for NLIP vs NLIP-0.
- **`paired_intent_bootstrap(df_a, df_b)`:** Clustered bootstrap resampling *intents* to calculate difference CIs and p-values accounting for cross-version intent correlation.
- **Exclusion logging:** Explicit tracking of included vs excluded (`infra_error`) sessions in every aggregate generation.
- **Aggregate functions:**
  - Stage 2: `basic_function.csv`, `interaction_gain.csv`.
  - Stage 3: `progression.csv`, `progression_pooled.csv`, `interaction_gap.csv`, `breaking.csv`, `by_change_kind.csv`, `prompts.csv`.
  - Stage 11: `ak.csv`, `by_kind.csv`, `needed.csv`, `effects.csv`, `cost.csv`, `stage2_ak.csv`, `stage2_effects.csv`, `headline_claims.csv`.
- **Preliminary quick-look charts:** Line and bar plots using `matplotlib`.

All 530 scoring and analysis tests pass in ~3.1s.

---

## 4. Interaction metrics, as of 1.1.0 (07b C6, C7)

- **`wrong_plans_caught`**, per plan: a restated plan that matches no gold alternative (device resolved offline) and whose `client_reply` is `correct` or `abort`. A wrong plan the client confirmed is not caught.
- **`questions_needed`**: each field in `asked_fields` is matched to `missing_info` by its full normalised path, or by the last path segment when that segment is unique among the task's missing fields. A missing field counts once however many times it is asked. Other questions are `questions_unneeded`.
- **`first_plan_correct`, `plan_correct_by_turn`**: a plan is correct if it matches a gold alternative and its device identifiers resolve offline to the task's device with none belonging to another.

## 5. Tests added in 07b

A rejected call then a correct one; an NLIP-0 retry that succeeds; two accepted calls; a refusal with the expected code, with a wrong code, and a malformed call; declining without a call (with and without `refusal_predictable`); L2 m30's refused call followed by the revised call; unknown profile with any 4xx; an unrepresentable task with and without the call; an extra identifier of the same device and of another device; backend records matched by `seq`; a wrong planned device found offline; a wrong plan confirmed (not caught) and corrected or aborted (caught); `questions_needed` matching. The oracle test builds executed calls for declined, refusal and unrepresentable tasks, and the null agent now scores 0 of 510 (no task has `refusal_predictable`).
