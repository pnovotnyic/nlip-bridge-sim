"""Tests for NLIP evaluation scoring (stage 07).

Proves the scorer against:
  1. Oracle agents (100% end-to-end on all 510 task instances including pilot)
  2. Null agents (correct exactly on declined tasks)
  3. Perturbations (wrong device, wrong profile, duration above tolerance, wrong session delete,
     server-version format return, forced value on unrepresentable result)
  4. Unit tests for every compare rule (paths, key order, absent/null, phone E.164, IP canonical, time tolerance, lists as sets)
  5. Incremental scoring identical to one-shot scoring
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nlipeval.scoring.compare import (
    check_harmful_call,
    compare_response_understanding,
    compare_single_call,
    compare_values,
    matches_any_gold_call,
    normalize_ip,
    normalize_path,
    normalize_phone,
)
from nlipeval.scoring.score import score_run, score_session

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"


# --------------------------------------------------------------------------- 1. Oracle agents (all 510 tasks)

def _get_all_task_files() -> list[Path]:
    return sorted(TASKS_DIR.glob("*/*.json"))


@pytest.mark.parametrize("task_path", _get_all_task_files(), ids=lambda p: p.stem)
def test_oracle_agent_scores_100(task_path: Path):
    """Oracle agents must score 100% end-to-end on every task instance."""
    task = json.loads(task_path.read_text(encoding="utf-8"))
    gold_answer = task.get("gold_client_answer", {})
    gold_status = gold_answer.get("status")
    gold_calls = task.get("gold_calls", [])
    gold_resp = task.get("gold_backend_response", {})

    refusal = task.get("expected_refusal")
    exec_calls, b_rec = [], []
    if gold_calls and (gold_status in ("done", "unrepresentable") or refusal):
        # the oracle server executes the gold call, gets the gold backend answer, and the backend logs it
        gc = gold_calls[0]
        exec_calls = [{
            "method": gc.get("method"),
            "path": gc.get("path"),
            "body": gc.get("body"),
            "status": gold_resp.get("status", 200),
            "response_body": gold_resp.get("body", {}),
            "ts": "2026-12-01T12:00:00Z",
        }]
        b_rec = [{
            "seq": 1,
            "resolved_device": task.get("world_ref", {}).get("device"),
            "identifiers_consistent": True,
        }]

    session = {
        "session_id": "oracle-" + task["task_id"],
        "task_id": task["task_id"],
        "termination": "declined" if (gold_status == "declined" and not exec_calls) else "final",
        "n_interactions": 0,
        "executed_calls": exec_calls,
        "client_final": gold_answer,
    }

    scored = score_session(session, task, b_rec)
    assert scored["end_to_end"] is True, f"Failed oracle for {task['task_id']}: {scored}"
    assert scored["harmful"] is False
    assert scored["request_correct"] is True
    assert scored["response_correct"] is True
    assert scored["status_correct"] is True


# --------------------------------------------------------------------------- 2. Null agents

def test_null_agent():
    """A server that always declines without a call is correct only where declining is correct: the gold
    status is declined and either no refusal is recorded or `refusal_predictable` is true (07b C2).
    Today every declined task carries an expected refusal and none is predictable, so the null agent scores 0."""
    all_tasks = _get_all_task_files()
    assert len(all_tasks) == 510

    n_correct = 0
    for task_path in all_tasks:
        task = json.loads(task_path.read_text(encoding="utf-8"))
        gold_status = task.get("gold_client_answer", {}).get("status")

        session = {
            "session_id": "null-" + task["task_id"],
            "task_id": task["task_id"],
            "termination": "declined",
            "n_interactions": 0,
            "executed_calls": [],
            "client_final": {"status": "declined", "result": None},
        }

        scored = score_session(session, task, [])
        should_pass = gold_status == "declined" and (not task.get("expected_refusal") or task.get("refusal_predictable"))
        assert scored["end_to_end"] is should_pass, task["task_id"]
        assert scored["correct_decline"] is (gold_status == "declined")
        n_correct += scored["end_to_end"]
    assert n_correct == 0


# --------------------------------------------------------------------------- 3. Perturbations

def test_perturbation_wrong_device():
    """Perturbation: wrong device -> harmful."""
    task_p = TASKS_DIR / "L1" / "L1-m01-v1.0.0.json"
    task = json.loads(task_p.read_text(encoding="utf-8"))
    gold_call = task["gold_calls"][0]

    session = {
        "session_id": "pert-device",
        "task_id": task["task_id"],
        "termination": "final",
        "n_interactions": 0,
        "executed_calls": [{
            "method": gold_call["method"],
            "path": gold_call["path"],
            "body": gold_call["body"],
            "status": 200,
            "response_body": {"reachable": True},
            "ts": "2026-12-01T12:00:00Z",
        }],
        "client_final": task["gold_client_answer"],
    }
    # Backend resolved wrong device D02 instead of D01
    backend_rec = [{"resolved_device": "D02", "identifiers_consistent": True}]

    scored = score_session(session, task, backend_rec)
    assert scored["harmful"] is True
    assert "wrong_device" in scored["harmful_reason"]
    assert scored["end_to_end"] is False


def test_perturbation_wrong_profile():
    """Perturbation: wrong profile -> harmful."""
    task_p = TASKS_DIR / "L3" / "L3-m01-v1.1.0.json"
    task = json.loads(task_p.read_text(encoding="utf-8"))
    gold_call = task["gold_calls"][0]

    wrong_body = dict(gold_call["body"])
    wrong_body["qosProfile"] = "QOS_E" if wrong_body.get("qosProfile") != "QOS_E" else "QOS_S"

    session = {
        "session_id": "pert-profile",
        "task_id": task["task_id"],
        "termination": "final",
        "n_interactions": 0,
        "executed_calls": [{
            "method": gold_call["method"],
            "path": gold_call["path"],
            "body": wrong_body,
            "status": 201,
            "response_body": {"sessionId": "test-id"},
            "ts": "2026-12-01T12:00:00Z",
        }],
        "client_final": task["gold_client_answer"],
    }
    backend_rec = [{"resolved_device": task["world_ref"].get("device"), "identifiers_consistent": True}]

    scored = score_session(session, task, backend_rec)
    assert scored["harmful"] is True
    assert "wrong_profile" in scored["harmful_reason"]
    assert scored["end_to_end"] is False


def test_perturbation_duration_above_tolerance():
    """Perturbation: duration above tolerance -> harmful."""
    task_p = TASKS_DIR / "L3" / "L3-m01-v1.1.0.json"
    task = json.loads(task_p.read_text(encoding="utf-8"))
    gold_call = task["gold_calls"][0]

    wrong_body = dict(gold_call["body"])
    wrong_body["duration"] = 7200  # gold is 3600 or different

    session = {
        "session_id": "pert-duration",
        "task_id": task["task_id"],
        "termination": "final",
        "n_interactions": 0,
        "executed_calls": [{
            "method": gold_call["method"],
            "path": gold_call["path"],
            "body": wrong_body,
            "status": 201,
            "response_body": {},
            "ts": "2026-12-01T12:00:00Z",
        }],
        "client_final": task["gold_client_answer"],
    }
    backend_rec = [{"resolved_device": task["world_ref"].get("device"), "identifiers_consistent": True}]

    scored = score_session(session, task, backend_rec)
    assert scored["harmful"] is True
    assert "duration" in scored["harmful_reason"]
    assert scored["end_to_end"] is False


def test_perturbation_delete_wrong_session():
    """Perturbation: delete of the wrong session -> harmful."""
    # Find a deleteSession task in L3
    delete_tasks = [p for p in TASKS_DIR.glob("L3/*.json") if "deleteSession" in json.loads(p.read_text())["operation"]]
    assert delete_tasks, "No deleteSession task found in L3"
    task = json.loads(delete_tasks[0].read_text(encoding="utf-8"))
    gold_call = task["gold_calls"][0]

    wrong_path = "/quality-on-demand/v1/sessions/00000000-0000-0000-0000-000000000000"

    session = {
        "session_id": "pert-delete",
        "task_id": task["task_id"],
        "termination": "final",
        "n_interactions": 0,
        "executed_calls": [{
            "method": "DELETE",
            "path": wrong_path,
            "body": None,
            "status": 204,
            "response_body": None,
            "ts": "2026-12-01T12:00:00Z",
        }],
        "client_final": task["gold_client_answer"],
    }
    scored = score_session(session, task, [])
    assert scored["harmful"] is True
    assert "session_id" in scored["harmful_reason"]
    assert scored["end_to_end"] is False


def test_perturbation_client_server_version_format():
    """Perturbation: client returns server-version format (e.g. ISO date where Unix seconds expected) -> response wrong."""
    # L3 v0.8.1 expects Unix timestamp (int), while server v1.1.0 returns ISO string
    task_p = TASKS_DIR / "L3" / "L3-m01-v0.8.1.json"
    task = json.loads(task_p.read_text(encoding="utf-8"))
    gold_call = task["gold_calls"][0]

    # Give ISO string instead of integer timestamp
    bad_result = dict(task["gold_client_answer"]["result"])
    bad_result["startedAt"] = "2026-12-01T12:00:00Z"

    session = {
        "session_id": "pert-format",
        "task_id": task["task_id"],
        "termination": "final",
        "n_interactions": 0,
        "executed_calls": [{
            "method": gold_call["method"],
            "path": gold_call["path"],
            "body": gold_call["body"],
            "status": 200,
            "response_body": {},
            "ts": "2026-12-01T12:00:00Z",
        }],
        "client_final": {"status": "done", "result": bad_result},
    }
    b_rec = [{"resolved_device": task["world_ref"].get("device"), "identifiers_consistent": True}]

    scored = score_session(session, task, b_rec)
    assert scored["request_correct"] is True
    assert scored["response_correct"] is False
    assert scored["end_to_end"] is False
    assert len(scored["response_mismatches"]) > 0


def test_perturbation_force_value_on_unrepresentable():
    """Perturbation: client forces a value on an unrepresentable result -> response wrong."""
    task_p = TASKS_DIR / "L2" / "L2-m03-v0.1.0.json"
    task = json.loads(task_p.read_text(encoding="utf-8"))
    assert task["gold_client_answer"]["status"] == "unrepresentable"

    session = {
        "session_id": "pert-unrep",
        "task_id": task["task_id"],
        "termination": "final",
        "n_interactions": 0,
        "executed_calls": [],
        "client_final": {"status": "done", "result": {"verificationResult": "TRUE"}},
    }
    scored = score_session(session, task, [])
    assert scored["status_correct"] is False
    assert scored["response_correct"] is False
    assert scored["end_to_end"] is False


# --------------------------------------------------------------------------- 4. Unit tests for compare rules

def test_compare_rule_path_parameters():
    assert normalize_path("/quality-on-demand/v1/sessions/") == "/quality-on-demand/v1/sessions"
    assert normalize_path("/a%20b/c") == "/a b/c"
    call = {"method": "GET", "path": "/quality-on-demand/v1/sessions/ABC-123/"}
    gold = {"method": "GET", "path": "/quality-on-demand/v1/sessions/abc-123"}
    ok, _ = compare_single_call(call, gold)
    assert ok is True


def test_compare_rule_json_key_order():
    b1 = {"b": 2, "a": 1, "c": {"y": 20, "x": 10}}
    b2 = {"a": 1, "c": {"x": 10, "y": 20}, "b": 2}
    ok, err = compare_values(b1, b2)
    assert ok is True
    assert err is None


def test_compare_rule_absent_vs_null_optional_fields():
    b1 = {"device": {"phoneNumber": "+9901000001", "ipv4Address": None}}
    b2 = {"device": {"phoneNumber": "+9901000001"}}
    ok, err = compare_values(b1, b2)
    assert ok is True
    assert err is None


def test_compare_rule_phone_e164():
    assert normalize_phone("+99-01-000001") == "+9901000001"
    assert normalize_phone("9901000001") == "9901000001"   # 07b C8: a missing "+" is not added
    assert normalize_phone("+99 (01) 000 001") == "+9901000001"

    ok, _ = compare_values({"phoneNumber": "+99 01 000001"}, {"phoneNumber": "+9901000001"}, "device.phoneNumber")
    assert ok is True
    ok, _ = compare_values("9901000001", "+9901000001", "device.phoneNumber")
    assert ok is False


def test_compare_rule_ip_canonical():
    assert normalize_ip("2001:0db8:0000:0000:0000:0000:0000:0001") == "2001:db8::1"
    assert normalize_ip("198.51.100.050") == "198.51.100.50"

    ok, _ = compare_values("2001:0db8::1", "2001:db8::1", "device.ipv6Address")
    assert ok is True


def test_compare_rule_time_tolerance():
    t1 = "2026-12-01T12:00:03Z"
    t2 = "2026-12-01T12:00:00Z"
    # Within 5s tolerance
    ok, _ = compare_values(t1, t2, "lastStatusTime", time_tolerance_s=5.0)
    assert ok is True

    # Exceeding 2s tolerance
    ok2, err2 = compare_values(t1, t2, "lastStatusTime", time_tolerance_s=2.0)
    assert ok2 is False
    assert "time difference" in err2


def test_compare_rule_lists_as_sets():
    # Connectivity list in L1
    ok, _ = compare_values(["SMS", "DATA"], ["DATA", "SMS"], "connectivity")
    assert ok is True


# --------------------------------------------------------------------------- 5. Incremental scoring test

def test_incremental_scoring_equivalence(tmp_path: Path):
    """Incremental scoring in three parts gives files identical to scoring all at once."""
    task_p = TASKS_DIR / "L1" / "L1-m01-v1.0.0.json"
    task = json.loads(task_p.read_text(encoding="utf-8"))

    # Create dummy sessions
    sessions = []
    for i in range(6):
        sess = {
            "schema_version": "1",
            "session_id": f"sess-{i}",
            "task_id": "L1-m01-v1.0.0",
            "termination": "final",
            "n_interactions": 0,
            "executed_calls": [{
                "method": "POST",
                "path": "/device-reachability-status/v1/retrieve",
                "body": {"device": {"phoneNumber": "+9901000001"}},
                "status": 200,
                "response_body": {"reachable": True},
                "ts": "2026-12-01T12:00:00Z",
            }],
            "client_final": task["gold_client_answer"],
        }
        sessions.append(sess)

    # 1. Full one-shot run
    run_full = tmp_path / "run_full"
    run_full.mkdir()
    with open(run_full / "sessions.jsonl", "w", encoding="utf-8") as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")

    scores_full = score_run(run_full, incremental=False, tasks_dir=TASKS_DIR)
    full_text = (run_full / "scores.jsonl").read_text(encoding="utf-8")

    # 2. Incremental run in 3 parts (2 sessions each)
    run_inc = tmp_path / "run_inc"
    run_inc.mkdir()
    sess_inc_file = run_inc / "sessions.jsonl"

    for part in (sessions[:2], sessions[2:4], sessions[4:]):
        with open(sess_inc_file, "a", encoding="utf-8") as f:
            for s in part:
                f.write(json.dumps(s) + "\n")
        score_run(run_inc, incremental=True, tasks_dir=TASKS_DIR)

    inc_text = (run_inc / "scores.jsonl").read_text(encoding="utf-8")
    scores_inc = [json.loads(line) for line in inc_text.strip().splitlines()]

    assert len(scores_full) == 6
    assert len(scores_inc) == 6
    assert full_text == inc_text


# --------------------------------------------------------------------------- 6. Stage 07b scorer rules (C1-C7)

def _task(task_id: str) -> dict:
    return json.loads((TASKS_DIR / task_id.split("-")[0] / f"{task_id}.json").read_text(encoding="utf-8"))


def _call(gc: dict, status: int = 200, body=None, resp=None, path=None) -> dict:
    return {"method": gc["method"], "path": path or gc["path"], "body": gc["body"] if body is None else body,
            "status": status, "response_body": resp if resp is not None else {}, "ts": "2026-12-01T12:00:00Z"}


def _session(task: dict, calls: list[dict], final=None, plans=None, **kw) -> dict:
    return {"session_id": "s", "task_id": task["task_id"], "termination": "final", "n_interactions": 0,
            "executed_calls": calls, "client_final": final or task["gold_client_answer"],
            "plans": plans or [], **kw}


def _rec(task: dict, seq: int = 1, **kw) -> dict:
    return {"seq": seq, "resolved_device": task["world_ref"]["device"], "identifiers_consistent": True, **kw}


def test_rejected_call_then_correct_call_is_correct():
    task = _task("L1-m01-v1.0.0")
    gc = task["gold_calls"][0]
    bad = _call(gc, status=400, body={"device": {}}, resp={"code": "INVALID_ARGUMENT"})
    good = _call(gc, status=200, resp=task["gold_backend_response"]["body"])
    recs = [{"seq": 1, "resolved_device": None, "identifiers_consistent": None}, _rec(task, 2)]
    sc = score_session(_session(task, [bad, good]), task, recs)
    assert sc["request_correct"] is True and sc["end_to_end"] is True
    assert any("rejected" in m for m in sc["request_mismatches"])


def test_nlip0_retry_that_succeeds_is_correct():
    task = _task("L3-m01-v1.1.0")
    gc = task["gold_calls"][0]
    wrong_path = _call(gc, status=404, path="/sessions", resp={"code": "NOT_FOUND"})
    good = _call(gc, status=201, resp=task["gold_backend_response"]["body"])
    sc = score_session(_session(task, [wrong_path, good]), task, [{"seq": 1}, _rec(task, 2)])
    assert sc["request_correct"] is True and sc["harmful"] is False and sc["end_to_end"] is True


def test_two_accepted_calls_are_not_correct():
    task = _task("L1-m01-v1.0.0")
    gc = task["gold_calls"][0]
    c = _call(gc, resp=task["gold_backend_response"]["body"])
    sc = score_session(_session(task, [c, c]), task, [_rec(task, 1), _rec(task, 2)])
    assert sc["request_correct"] is False


def _refusal_task() -> dict:
    t = _task("L2-m16-v0.1.0")
    assert t["expected_refusal"]["code"] == "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE"
    return t


def test_refusal_with_expected_code_is_correct():
    t = _refusal_task()
    c = _call(t["gold_calls"][0], status=422, resp={"status": 422, "code": t["expected_refusal"]["code"]})
    assert score_session(_session(t, [c]), t, [_rec(t)])["request_correct"] is True


def test_refusal_with_wrong_code_is_incorrect():
    t = _refusal_task()
    c = _call(t["gold_calls"][0], status=422, resp={"status": 422, "code": "LOCATION_VERIFICATION.UNABLE_TO_LOCATE"})
    sc = score_session(_session(t, [c]), t, [_rec(t)])
    assert sc["request_correct"] is False and sc["end_to_end"] is False


def test_malformed_call_getting_a_400_is_not_the_expected_refusal():
    t = _refusal_task()
    bad = _call(t["gold_calls"][0], status=400, body={"device": {}}, resp={"status": 400, "code": "INVALID_ARGUMENT"})
    assert score_session(_session(t, [bad]), t, [{"seq": 1}])["request_correct"] is False


def test_decline_without_call_needs_refusal_predictable():
    t = _refusal_task()
    s = _session(t, [], final={"status": "declined", "result": None})
    assert score_session(s, t, [])["request_correct"] is False
    t2 = {**t, "refusal_predictable": True}
    assert score_session(s, t2, [])["request_correct"] is True


def test_refused_call_then_revised_call_m30():
    """A refused call followed by the revised call: the last executed call decides on a refusal task; on a
    done task the one accepted call decides (L2 m30)."""
    t = _task("L2-m30-v3.0.0")
    gc = t["gold_calls"][0]
    first = _call(gc, status=422, body={**gc["body"], "maxAge": 0},
                  resp={"status": 422, "code": "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE"})
    second = _call(gc, status=200, resp=t["gold_backend_response"]["body"])
    sc = score_session(_session(t, [first, second]), t, [_rec(t, 1), _rec(t, 2)])
    assert sc["request_correct"] is True and sc["end_to_end"] is True


def test_unknown_profile_any_4xx_counts_when_the_call_otherwise_matches():
    task = _task("L3-m01-v1.1.0")
    gc = task["gold_calls"][0]
    unknown = {**task, "gold_backend_response": {"status": 404, "body": {"code": "NOT_FOUND"}},
               "expected_refusal": {"status": 404, "code": "NOT_FOUND"},
               "gold_client_answer": {"status": "declined", "result": None}}
    for status in (404, 400, 422):
        c = _call(gc, status=status, resp={"code": "X"})
        s = _session(unknown, [c], final={"status": "declined", "result": None})
        assert score_session(s, unknown, [_rec(task)])["request_correct"] is True
    other = _call(gc, status=404, body={**gc["body"], "duration": 7}, resp={"code": "NOT_FOUND"})
    s = _session(unknown, [other], final={"status": "declined", "result": None})
    assert score_session(s, unknown, [_rec(task)])["request_correct"] is False


def test_unrepresentable_task_needs_the_call():
    t = _task("L2-m03-v0.1.0")
    assert t["gold_client_answer"]["status"] == "unrepresentable"
    no_call = score_session(_session(t, []), t, [])
    assert no_call["request_correct"] is False and no_call["end_to_end"] is False
    c = _call(t["gold_calls"][0], status=422, resp={"status": 422, "code": t["expected_refusal"]["code"]})
    assert score_session(_session(t, [c]), t, [_rec(t)])["end_to_end"] is True


def test_extra_identifier_of_same_device_is_correct_of_another_is_incorrect():
    task = _task("L2-m01-v3.0.0")
    gc = task["gold_calls"][0]
    dev = gc["body"]["device"]
    assert "phoneNumber" in dev
    # D01's IPv6 is in the world; the second identifier belongs to the same device or to another one
    from nlipeval.backends.world import World
    w = World()
    d = w.device(task["world_ref"]["device"])
    other = next(x for x in w.devices if x.id != d.id)
    same = {**gc["body"], "device": {**dev, "ipv6Address": d.ipv6_address}}
    diff = {**gc["body"], "device": {**dev, "ipv6Address": other.ipv6_address}}
    ok = score_session(_session(task, [_call(gc, body=same, resp=task["gold_backend_response"]["body"])]), task,
                       [_rec(task)])
    assert ok["request_correct"] is True
    bad = score_session(_session(task, [_call(gc, body=diff, resp=task["gold_backend_response"]["body"])]), task,
                        [_rec(task, identifiers_consistent=False)])
    assert bad["request_correct"] is False and bad["end_to_end"] is False


def test_records_are_matched_by_seq_not_position():
    task = _task("L1-m01-v1.0.0")
    gc = task["gold_calls"][0]
    c = _call(gc, resp=task["gold_backend_response"]["body"], )
    c["seq"] = 2     # the executed call is the backend's second request
    records = [{"seq": 1, "resolved_device": "D09", "identifiers_consistent": True}, _rec(task, 2)]
    assert score_session(_session(task, [c]), task, records)["request_correct"] is True


def test_planned_wrong_device_is_found_offline():
    task = _task("L1-m01-v1.0.0")
    gc = task["gold_calls"][0]
    wrong = {"method": gc["method"], "path": gc["path"], "body": {"device": {"phoneNumber": "+9901000002"}}}
    plans = [{"turn": 1, "action": "restate", "plan": wrong, "asked_fields": None, "client_reply": "confirm"}]
    sc = score_session(_session(task, [], plans=plans), task, [])
    assert sc["first_plan_correct"] is False
    right = [{"turn": 1, "action": "restate", "plan": gc, "asked_fields": None, "client_reply": "confirm"}]
    assert score_session(_session(task, [], plans=right), task, [])["first_plan_correct"] is True


def _wrong_plan_session(task: dict, reply: str) -> dict:
    gc = task["gold_calls"][0]
    wrong = {**gc, "body": {"device": {"phoneNumber": "+9901000002"}}}
    plans = [{"turn": 1, "action": "restate", "plan": wrong, "asked_fields": None, "client_reply": reply},
             {"turn": 2, "action": "restate", "plan": gc, "asked_fields": None, "client_reply": "confirm"}]
    return _session(task, [], plans=plans)


def test_wrong_plan_confirmed_is_not_caught_corrected_is():
    task = _task("L1-m01-v1.0.0")
    assert score_session(_wrong_plan_session(task, "confirm"), task, [])["wrong_plans_caught"] == 0
    assert score_session(_wrong_plan_session(task, "correct"), task, [])["wrong_plans_caught"] == 1
    assert score_session(_wrong_plan_session(task, "abort"), task, [])["wrong_plans_caught"] == 1


def test_questions_needed_matches_full_path_or_unique_last_segment_once_per_field():
    from nlipeval.scoring.score import match_asked_fields
    miss = ["device.ipv4Address.publicPort", "maxAge"]
    assert match_asked_fields({"maxAge"}, miss) == ({"maxAge"}, set())
    assert match_asked_fields({"publicPort", "device.ipv4Address.publicPort"}, miss) == (
        {"device.ipv4Address.publicPort"}, set())
    assert match_asked_fields({"radius"}, miss) == (set(), {"radius"})
    # a last segment shared by two missing fields is ambiguous and matches neither
    amb = ["a.address", "b.address"]
    assert match_asked_fields({"address"}, amb) == (set(), {"address"})
    assert match_asked_fields({"a.address"}, amb) == ({"a.address"}, set())


def test_scorer_version():
    from nlipeval.scoring.score import SCORER_VERSION
    assert SCORER_VERSION == "1.2.0"


# --------------------------------------------------------------------------- 08a C9: optional answer fields

def _l2_task():
    """L2 v2.0.0 client: verificationResult required; lastLocationTime and matchRate optional."""
    for p in sorted(TASKS_DIR.glob("L2/L2-m*-v2.0.0.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        r = (t["gold_client_answer"] or {}).get("result") or {}
        if t["gold_client_answer"]["status"] == "done" and "lastLocationTime" in r:
            return t
    raise AssertionError("no L2 v2.0.0 task with lastLocationTime")


def _answer(task, result):
    return compare_response_understanding({"status": "done", "result": result}, task)


def test_c9_required_field_missing_is_wrong():
    t = _l2_task()
    r = dict(t["gold_client_answer"]["result"]); r.pop("verificationResult")
    _, ok, mism, inc = _answer(t, r)
    assert ok is False and mism and inc is False


def test_c9_optional_field_absent_is_correct_and_incomplete():
    t = _l2_task()
    r = dict(t["gold_client_answer"]["result"]); r.pop("lastLocationTime")
    _, ok, mism, inc = _answer(t, r)
    assert ok is True and mism == [] and inc is True


def test_c9_complete_answer_is_not_incomplete():
    t = _l2_task()
    _, ok, _, inc = _answer(t, dict(t["gold_client_answer"]["result"]))
    assert ok is True and inc is False


def test_c9_optional_field_present_but_wrong_is_wrong():
    t = _l2_task()
    r = dict(t["gold_client_answer"]["result"]); r["lastLocationTime"] = "2023-01-01T00:00:00Z"
    _, ok, mism, inc = _answer(t, r)
    assert ok is False and mism and inc is False


def test_c9_incomplete_is_recorded_in_scores():
    t = _l2_task()
    r = dict(t["gold_client_answer"]["result"]); r.pop("lastLocationTime")
    gc = t["gold_calls"][0]
    session = {"session_id": "inc", "task_id": t["task_id"], "termination": "final", "n_interactions": 0,
               "executed_calls": [{**gc, "status": t["gold_backend_response"]["status"],
                                   "response_body": t["gold_backend_response"]["body"], "ts": "x"}],
               "client_final": {"status": "done", "result": r}}
    b = [{"seq": 1, "resolved_device": t["world_ref"]["device"], "identifiers_consistent": True}]
    sc = score_session(session, t, b)
    assert sc["response_correct"] is True and sc["response_incomplete"] is True and sc["end_to_end"] is True


def test_c9_echo_fields_are_not_in_the_answer_schemas():
    import yaml
    for api in ("L2", "L3"):
        text = (ROOT / "config" / "answer_schemas" / f"{api}.yaml").read_text()
        doc = yaml.safe_load(text)["schemas"]
        for v, sch in doc.items():
            for one in ([sch] if "properties" in sch else list(sch.values())):
                props = one.get("properties", {}) if isinstance(one, dict) else {}
                assert "device" not in props and "ueId" not in props, (api, v)


def test_c9_echo_equal_to_native_request_is_accepted_other_is_wrong():
    t = _l2_task()
    native_device = t["client_native_request"]["body"]["device"] if "device" in (t["client_native_request"].get("body") or {}) else None
    assert native_device is not None
    r = dict(t["gold_client_answer"]["result"])
    _, ok, _, _ = _answer(t, {**r, "device": native_device})
    assert ok is True
    _, ok, mism, _ = _answer(t, {**r, "device": {"phoneNumber": "+9909999999"}})
    assert ok is False and mism


def test_c9_unknown_extra_field_is_wrong():
    t = _l2_task()
    _, ok, _, _ = _answer(t, {**t["gold_client_answer"]["result"], "invented": 1})
    assert ok is False


# --------------------------------------------------------------------------- 08a C10: L1 precedence

def _l1_both(version):
    for p in sorted(TASKS_DIR.glob(f"L1/L1-m*-{version}.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        if t["gold_client_answer"].get("alternatives"):
            return t
    raise AssertionError("no DATA+SMS task")


@pytest.mark.parametrize("version,key", [("v0.5.1", "connectivityStatus"), ("v0.6.0", "reachabilityStatus")])
def test_c10_data_and_sms_device_accepts_either_but_not_other_values(version, key):
    t = _l1_both(version)
    gold = t["gold_client_answer"]["result"]
    assert gold[key] == "CONNECTED_DATA"
    for good in ("CONNECTED_DATA", "CONNECTED_SMS"):
        _, ok, _, _ = _answer(t, {**gold, key: good})
        assert ok is True, good
    for bad in ("NOT_CONNECTED", "unrepresentable", "DATA"):
        _, ok, _, _ = _answer(t, {**gold, key: bad})
        assert ok is False, bad


def test_c10_only_data_and_sms_devices_have_the_alternative():
    n_alt = 0
    for p in sorted(TASKS_DIR.glob("L1/*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        ga = t["gold_client_answer"]
        if ga["status"] != "done" or t["client_version"] == "v1.0.0":
            assert "alternatives" not in ga, t["task_id"]
            continue
        body = t["gold_backend_response"]["body"]
        both = bool(body.get("reachable")) and {"DATA", "SMS"} <= set(body.get("connectivity") or [])
        assert bool(ga.get("alternatives")) is both, t["task_id"]
        n_alt += both
    assert n_alt == 34   # 24 main + 10 pilot instances (12 + 12 main, 5 + 5 pilot)
