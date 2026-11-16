"""Session scorer for NLIP evaluation (stage 07).

Scores sessions from logs against task gold specifications, producing scores.jsonl
matching bob_plan/07-scoring-and-analysis-code.md and data-contract.md §2.6.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from nlipeval.scoring.compare import (
    check_harmful_call,
    compare_response_understanding,
    judge_device,
    matches_any_gold_call,
)

SCORER_VERSION = "1.1.0"


def _norm_field(f: str) -> str:
    """Normalise a field path: no leading '/' or '$.', no spaces, '[n]' dropped."""
    s = f.strip().lstrip("/")
    if s.startswith("$."):
        s = s[2:]
    return re.sub(r"\[\d*\]", "", s).replace(" ", "")


def match_asked_fields(asked: set[str], missing_info: list[str]) -> tuple[set[str], set[str]]:
    """Match the fields the server asked about to the task's `missing_info` (07b C7).

    A question matches a missing field by the full normalised path, or by the last path segment when that
    segment is unique among the task's missing fields. Returns (missing fields asked about, unmatched
    questions): each missing field is counted once however many ways it was asked.
    """
    missing = {_norm_field(m): m for m in missing_info}
    last = {}
    for m in missing:
        last.setdefault(m.split(".")[-1], []).append(m)
    needed: set[str] = set()
    unneeded: set[str] = set()
    for q in asked:
        if q in missing:
            needed.add(q)
        elif q.split(".")[-1] in last and len(last[q.split(".")[-1]]) == 1:
            needed.add(last[q.split(".")[-1]][0])
        else:
            unneeded.add(q)
    return needed, unneeded


def _backend_by_seq(backend_records: list[dict] | None) -> dict[int, dict]:
    """Backend records keyed by `seq` (07b C5). Records without a `seq` get their 1-based position."""
    out: dict[int, dict] = {}
    for i, r in enumerate(backend_records or [], start=1):
        out[r.get("seq", i)] = r
    return out


def _record_for(call: dict, index: int, by_seq: dict[int, dict]) -> dict | None:
    """The i-th executed call is the backend's request number `seq`; a call that carries its own `seq`
    uses it."""
    return by_seq.get(call.get("seq", index + 1))


def _plan_matches(plan: dict, task: dict) -> bool:
    """A planned call is correct if it matches a gold alternative and its device identifiers resolve,
    offline, to the task's device with none belonging to another device."""
    ok, _ = matches_any_gold_call(plan, task.get("gold_calls", []))
    if not ok:
        return False
    dev_ok, _ = judge_device(plan, task, None)
    return dev_ok


def _request_correctness(executed: list[dict], task: dict, by_seq: dict[int, dict]) -> tuple[bool, list[str]]:
    """Return (request_correct, request_mismatches) per 07b C1-C4."""
    gold_calls = task.get("gold_calls", [])
    gold_status = (task.get("gold_client_answer") or {}).get("status")
    refusal = task.get("expected_refusal")
    notes: list[str] = []

    for i, c in enumerate(executed):
        if c.get("status", 200) >= 400:
            notes.append(f"call {i + 1} rejected by the backend: HTTP {c.get('status')} {c.get('response_body')}")

    # --- no gold call at all: nothing may be executed
    if not gold_calls:
        return (not executed), notes + ([] if not executed else ["a call was executed; none was expected"])

    # --- unknown profile: any 4xx, if the call otherwise matches (stage 04, choice 1)
    if task.get("api") == "L3" and any(isinstance(g.get("body"), dict) and "qosProfile" in g["body"] for g in gold_calls) \
            and ((task.get("gold_backend_response") or {}).get("status") == 404 or (refusal or {}).get("status") == 404):
        if not executed:
            return False, notes + ["no call executed"]
        last = executed[-1]
        loose = [{**g, "body": {k: v for k, v in (g.get("body") or {}).items() if k != "qosProfile"}} for g in gold_calls]
        probe = {**last, "body": {k: v for k, v in (last.get("body") or {}).items() if k != "qosProfile"}}
        matched, errs = matches_any_gold_call(probe, loose)
        if matched and 400 <= last.get("status", 0) < 500:
            return True, notes
        return False, notes + errs

    # --- refusal tasks (C2)
    if refusal:
        if not executed:
            if task.get("refusal_predictable") is True:
                return True, notes
            return False, notes + ["no call executed; the refusal could not be known without the call"]
        last_i = len(executed) - 1
        last = executed[last_i]
        rec = _record_for(last, last_i, by_seq)
        matched, errs = matches_any_gold_call(last, gold_calls)
        dev_ok, dev_err = judge_device(last, task, rec)
        body = last.get("response_body")
        code = body.get("code") if isinstance(body, dict) else None
        if matched and dev_ok and last.get("status") == refusal.get("status") and code == refusal.get("code"):
            return True, notes
        why = errs + ([dev_err] if dev_err else [])
        if matched and dev_ok:
            why.append(f"refusal {last.get('status')} {code} instead of {refusal.get('status')} {refusal.get('code')}")
        return False, notes + why

    # --- gold says declined, but no refusal is recorded: the server may not call at all
    if gold_status == "declined":
        return (not executed), notes + ([] if not executed else ["a call was executed on a declined task"])

    # --- done and unrepresentable (C1, C3, C4): exactly one accepted call that matches a gold alternative
    accepted = [(i, c) for i, c in enumerate(executed) if c.get("status", 200) < 400]
    if not accepted:
        return False, notes + ["no call was accepted by the backend"]
    if len(accepted) > 1:
        return False, notes + [f"{len(accepted)} calls accepted, expected exactly 1"]
    i, call = accepted[0]
    matched, errs = matches_any_gold_call(call, gold_calls)
    dev_ok, dev_err = judge_device(call, task, _record_for(call, i, by_seq))
    if matched and dev_ok:
        return True, notes
    return False, notes + errs + ([dev_err] if dev_err else [])


def score_session(
    session: dict,
    task: dict,
    backend_records: list[dict] | None = None,
) -> dict:
    """Score a single session against its task instance.

    Returns a dict matching data contract §2.6.
    """
    session_id = session.get("session_id", "")
    termination = session.get("termination", "")
    infra_error = (termination == "error_harness")

    executed_calls = session.get("executed_calls", [])
    client_final = session.get("client_final")
    gold_answer = task.get("gold_client_answer", {})
    gold_status = gold_answer.get("status")
    gold_calls = task.get("gold_calls", [])
    by_seq = _backend_by_seq(backend_records)

    # 1. Request correctness
    request_correct, request_mismatches = _request_correctness(executed_calls, task, by_seq)

    # 2. Harmful call check
    harmful = False
    harmful_reason: str | None = None
    for i, ec in enumerate(executed_calls):
        is_harm, reason = check_harmful_call(ec, task, _record_for(ec, i, by_seq))
        if is_harm:
            harmful = True
            harmful_reason = reason
            break

    # 3. Response understanding
    status_correct, response_correct, response_mismatches = compare_response_understanding(
        client_final, task
    )

    # 4. End-to-end success
    end_to_end = bool(request_correct and response_correct and status_correct and not harmful and not infra_error)

    # 5. Declines
    declined = bool(len(executed_calls) == 0 and client_final and client_final.get("status") == "declined")
    correct_decline = bool(declined and gold_status == "declined")

    # 6. Interaction metrics
    k_used = session.get("n_interactions", 0)
    plans = session.get("plans", [])

    asked: set[str] = set()
    wrong_plans_caught = 0
    plan_correct_by_turn: list[bool] = []
    first_plan_correct: bool | None = None

    for p in plans:
        for f in (p.get("asked_fields") or []):
            asked.add(_norm_field(f))
        p_plan = p.get("plan")
        if p_plan:
            ok = _plan_matches(p_plan, task)
            plan_correct_by_turn.append(ok)
            if first_plan_correct is None:
                first_plan_correct = ok
            # C6: a restated plan that is wrong, and the client corrected it or aborted
            if not ok and p.get("action") == "restate" and p.get("client_reply") in ("correct", "abort"):
                wrong_plans_caught += 1

    needed, unneeded = match_asked_fields(asked, task.get("missing_info", []))
    questions_needed = len(needed)
    questions_unneeded = len(unneeded)

    return {
        "schema_version": "1",
        "session_id": session_id,
        "scorer_version": SCORER_VERSION,
        "infra_error": infra_error,
        "request_correct": request_correct,
        "request_mismatches": request_mismatches,
        "response_correct": response_correct,
        "response_mismatches": response_mismatches,
        "status_correct": status_correct,
        "end_to_end": end_to_end,
        "harmful": harmful,
        "harmful_reason": harmful_reason,
        "declined": declined,
        "correct_decline": correct_decline,
        "k_used": k_used,
        "questions_needed": questions_needed,
        "questions_unneeded": questions_unneeded,
        "wrong_plans_caught": wrong_plans_caught,
        "first_plan_correct": first_plan_correct,
        "plan_correct_by_turn": plan_correct_by_turn,
    }


def _load_task(task_id: str, tasks_dir: Path) -> dict:
    """Load a task JSON file by its task_id."""
    api = task_id.split("-")[0]
    p = tasks_dir / api / f"{task_id}.json"
    if not p.is_file():
        # Try search in any subfolder
        matches = list(tasks_dir.glob(f"*/{task_id}.json"))
        if matches:
            p = matches[0]
        else:
            raise FileNotFoundError(f"Task file not found for {task_id} in {tasks_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def score_run(
    run_dir: Path | str,
    incremental: bool = False,
    tasks_dir: Path | str | None = None,
) -> list[dict]:
    """Score a run directory, writing scores.jsonl.

    If incremental=True, only sessions not yet present in scores.jsonl are scored.
    """
    run_dir = Path(run_dir)
    if tasks_dir is None:
        # Default tasks dir relative to repo root
        root = run_dir.resolve().parents[2] if (run_dir / "manifest.json").exists() else Path(__file__).resolve().parents[2]
        tasks_dir = root / "tasks"
    else:
        tasks_dir = Path(tasks_dir)

    sessions_file = run_dir / "sessions.jsonl"
    backend_file = run_dir / "backend.jsonl"
    scores_file = run_dir / "scores.jsonl"

    if not sessions_file.is_file():
        raise FileNotFoundError(f"No sessions.jsonl found in {run_dir}")

    # Load backend records grouped by session_id
    backend_map: dict[str, list[dict]] = {}
    if backend_file.is_file():
        with open(backend_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                sid = rec.get("session_id")
                if sid:
                    backend_map.setdefault(sid, []).append(rec)

    # Read existing scores if incremental
    existing_scores: list[dict] = []
    scored_session_ids: set[str] = set()
    if incremental and scores_file.is_file():
        with open(scores_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                s_rec = json.loads(line)
                existing_scores.append(s_rec)
                scored_session_ids.add(s_rec.get("session_id"))

    # Read sessions and score
    new_scores: list[dict] = []
    task_cache: dict[str, dict] = {}

    with open(sessions_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            session = json.loads(line)
            sid = session.get("session_id")
            if incremental and sid in scored_session_ids:
                continue

            tid = session.get("task_id")
            if tid not in task_cache:
                task_cache[tid] = _load_task(tid, tasks_dir)
            task = task_cache[tid]

            b_recs = backend_map.get(sid, [])
            score_rec = score_session(session, task, b_recs)
            new_scores.append(score_rec)

    if incremental:
        if new_scores:
            with open(scores_file, "a", encoding="utf-8") as f:
                for rec in new_scores:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return existing_scores + new_scores
    else:
        with open(scores_file, "w", encoding="utf-8") as f:
            for rec in new_scores:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return new_scores


def score_incremental(run_dir: Path | str, tasks_dir: Path | str | None = None) -> list[dict]:
    """Incremental scoring convenience function called by the runner."""
    return score_run(run_dir, incremental=True, tasks_dir=tasks_dir)
