"""Harness tests for stage 06.

Tests are split into:
1. Unit tests: state machine paths using FakeModel scripted responses,
   driving `ClientAgent` and `ServerAgent` directly with a fake adapter,
   and running through `run_session` with mock backends.
2. End-to-end test: 2 tasks per API × NLIP and NLIP-0 × R3 (fake model),
   checking log file completeness and wire message validity.

The fake_model.py module provides scripted replies and the make_adapter helper.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from tests.fake_model import (
    NLIP0_DECLINE,
    NLIP0_EXECUTE,
    NLIP0_PROTOCOL_SLIP_ASK,
    NLIP_ABORT,
    NLIP_ASK_ANSWER_RESTATE_CONFIRM,
    NLIP_BACKEND_REJECTION,
    NLIP_CORRECT_THEN_CONFIRM,
    NLIP_PROTOCOL_SLIP_EXECUTE_BEFORE_CONFIRM,
    NLIP_SERVER_DECLINE,
    make_adapter,
    minimal_task,
)


# --------------------------------------------------------------------------- mock backend

def _make_mock_backend_server(responses: list[dict]) -> tuple[HTTPServer, str]:
    """Return (server, url). Responses consumed in order; last repeats."""
    _responses = list(responses)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a: Any) -> None:
            pass

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            resp = _responses.pop(0) if len(_responses) > 1 else _responses[0]
            data = json.dumps(resp.get("body", {})).encode()
            self.send_response(resp.get("status", 200))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    return srv, f"http://127.0.0.1:{port}"


@pytest.fixture
def backend_200(tmp_path):
    """A backend that always returns 200 with a simple reachability response."""
    srv, url = _make_mock_backend_server([
        {"status": 200, "body": {"reachable": True, "connectivity": ["DATA"]}}
    ])
    yield {"L1": url, "L2": url, "L3": url}
    srv.shutdown()


@pytest.fixture
def backend_400_then_200(tmp_path):
    """A backend that returns 400 on the first call, then 200."""
    srv, url = _make_mock_backend_server([
        {"status": 400, "body": {"status": 400, "code": "INVALID_ARGUMENT", "message": "bad"}},
        {"status": 200, "body": {"reachable": True, "connectivity": ["DATA"]}},
    ])
    yield {"L1": url, "L2": url, "L3": url}
    srv.shutdown()


# --------------------------------------------------------------------------- session runner helper

def _run(tmp_path, replies, task=None, condition="NLIP", backend_urls=None):
    """Run one session using scripted replies and return the SessionOutcome."""
    from nlipeval.agents.client import ClientAgent
    from nlipeval.agents.server import ServerAgent
    from nlipeval.runner.session import SessionConfig, run_session

    if task is None:
        task = minimal_task()
    if backend_urls is None:
        # use a default always-200 backend
        srv, url = _make_mock_backend_server([
            {"status": 200, "body": {"reachable": True, "connectivity": ["DATA"]}}
        ])
        backend_urls = {"L1": url, "L2": url, "L3": url}

    adapter, script = make_adapter(tmp_path, replies)
    system = "You are a test agent."

    client_agent = ClientAgent(adapter, "R3", system, "test-session")
    server_agent = ServerAgent(adapter, "R3", system, "test-session")

    cfg = SessionConfig(
        rung="R3",
        prompt="P2",
        condition=condition,
        attempt=1,
        run_id="test-run",
        client_agent=client_agent,
        server_agent=server_agent,
        backend_urls=backend_urls,
        wall_time_limit_s=30.0,
    )

    return run_session(task, cfg)


# ===========================================================================
# NLIP state machine paths
# ===========================================================================

class TestNLIPAskAnswerRestateConfirm:
    """Happy path: ask → answer → restate → confirm → execute → report → final."""

    def test_termination(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert out.termination == "final"

    def test_counters(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert out.n_questions == 1
        assert out.n_restatements == 1
        assert out.n_corrections == 0
        assert out.n_interactions == 1   # one ask/answer round

    def test_plans_recorded(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert len(out.plans) >= 2   # ask + restate
        actions = [p.action for p in out.plans]
        assert "ask" in actions
        assert "restate" in actions

    def test_executed_call(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert len(out.executed_calls) == 1
        ec = out.executed_calls[0]
        assert ec.status == 200

    def test_client_final(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert out.client_final is not None
        assert out.client_final["status"] == "done"


class TestNLIPCorrectThenConfirm:
    """Client corrects wrong restatement, then confirms the revised one."""

    def test_termination(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_CORRECT_THEN_CONFIRM, backend_urls=backend_200)
        assert out.termination == "final"

    def test_correction_counted(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_CORRECT_THEN_CONFIRM, backend_urls=backend_200)
        assert out.n_corrections == 1
        assert out.n_restatements == 2   # two restates


class TestNLIPAbort:
    """Client aborts after server asks for a value."""

    def test_termination(self, tmp_path):
        out = _run(tmp_path, NLIP_ABORT)
        assert out.termination == "declined"

    def test_no_execution(self, tmp_path):
        out = _run(tmp_path, NLIP_ABORT)
        assert len(out.executed_calls) == 0


class TestNLIPServerDecline:
    """Server declines; client produces final with status declined."""

    def test_termination(self, tmp_path):
        out = _run(tmp_path, NLIP_SERVER_DECLINE)
        assert out.termination == "declined"

    def test_no_execution(self, tmp_path):
        out = _run(tmp_path, NLIP_SERVER_DECLINE)
        assert len(out.executed_calls) == 0

    def test_client_final_declined(self, tmp_path):
        out = _run(tmp_path, NLIP_SERVER_DECLINE)
        assert out.client_final is not None
        assert out.client_final["status"] == "declined"


class TestNLIPProtocolSlipExecuteBeforeConfirm:
    """Server sends 'execute' before client confirms — treated as restate; slip logged."""

    def test_termination(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_PROTOCOL_SLIP_EXECUTE_BEFORE_CONFIRM, backend_urls=backend_200)
        assert out.termination == "final"

    def test_slip_logged(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_PROTOCOL_SLIP_EXECUTE_BEFORE_CONFIRM, backend_urls=backend_200)
        assert any("protocol_slip" in e for e in out.errors)


class TestNLIPBackendRejection:
    """Backend rejects the first call; server restates; client confirms again."""

    def test_termination(self, tmp_path, backend_400_then_200):
        out = _run(tmp_path, NLIP_BACKEND_REJECTION, backend_urls=backend_400_then_200)
        # may be final or error depending on whether the re-restate succeeds
        assert out.termination in ("final", "error_harness", "error_model")

    def test_two_executions(self, tmp_path, backend_400_then_200):
        out = _run(tmp_path, NLIP_BACKEND_REJECTION, backend_urls=backend_400_then_200)
        # at least one execution happened
        assert len(out.executed_calls) >= 1


# ===========================================================================
# NLIP-0 state machine paths
# ===========================================================================

class TestNLIP0Execute:
    """Happy path: request → execute → report → final."""

    def test_termination(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_EXECUTE, condition="NLIP-0", backend_urls=backend_200)
        assert out.termination == "final"

    def test_no_interactions(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_EXECUTE, condition="NLIP-0", backend_urls=backend_200)
        assert out.n_interactions == 0

    def test_plan_recorded(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_EXECUTE, condition="NLIP-0", backend_urls=backend_200)
        assert any(p.action == "execute" for p in out.plans)

    def test_executed_call(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_EXECUTE, condition="NLIP-0", backend_urls=backend_200)
        assert len(out.executed_calls) >= 1


class TestNLIP0Decline:
    """Server declines in NLIP-0."""

    def test_termination(self, tmp_path):
        out = _run(tmp_path, NLIP0_DECLINE, condition="NLIP-0")
        assert out.termination == "declined"

    def test_client_final_declined(self, tmp_path):
        out = _run(tmp_path, NLIP0_DECLINE, condition="NLIP-0")
        assert out.client_final is not None
        assert out.client_final["status"] == "declined"


class TestNLIP0ProtocolSlipAsk:
    """Server sends 'ask' in NLIP-0 — treated as execute if plan is present."""

    def test_slip_logged(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_PROTOCOL_SLIP_ASK, condition="NLIP-0", backend_urls=backend_200)
        assert any("protocol_slip" in e for e in out.errors)

    def test_execution_proceeded(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_PROTOCOL_SLIP_ASK, condition="NLIP-0", backend_urls=backend_200)
        # plan was present, so harness should have executed
        assert len(out.executed_calls) >= 1


# ===========================================================================
# Interaction counting
# ===========================================================================

class TestInteractionCounting:
    """Verify counting rules from the spec."""

    def test_first_restate_confirm_is_zero_interactions(self, tmp_path, backend_200):
        """The first restatement and its confirmation count as zero interactions."""
        # Simple path: restate → confirm (no asks, no corrections)
        replies = [
            {"role": "client", "reply": {
                "action": "request", "message": "Check reachability", "final": None}},
            {"role": "server", "reply": {
                "action": "restate",
                "message": "I will POST ...",
                "plan": {
                    "method": "POST",
                    "path": "/device-reachability-status/v1/retrieve",
                    "body": {"device": {"phoneNumber": "+9901000001"}},
                },
                "asked_fields": None}},
            {"role": "client", "reply": {
                "action": "confirm", "message": "Yes", "final": None}},
            {"role": "server", "reply": {
                "action": "report", "message": "Done.", "plan": None, "asked_fields": None}},
            {"role": "client", "reply": {
                "action": "final", "message": "",
                "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}}},
        ]
        out = _run(tmp_path, replies, backend_urls=backend_200)
        assert out.n_interactions == 0
        assert out.n_restatements == 1

    def test_one_ask_counts_one_interaction(self, tmp_path, backend_200):
        """An ask-answer pair counts as +1 interaction."""
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert out.n_interactions == 1

    def test_n_questions_counts_asks(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert out.n_questions == 1

    def test_n_corrections_counts_corrections(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_CORRECT_THEN_CONFIRM, backend_urls=backend_200)
        assert out.n_corrections == 1


# ===========================================================================
# Wire log
# ===========================================================================

class TestWireLog:
    """Every wire entry has valid_ecma430 assessed."""

    def test_wire_entries_present(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert len(out.wire_log) > 0

    def test_wire_entries_have_required_fields(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        for entry in out.wire_log:
            assert "direction" in entry
            assert "message" in entry
            assert "valid_ecma430" in entry

    def test_wire_messages_are_valid_nlip(self, tmp_path, backend_200):
        """Messages sent by our harness should be valid ECMA-430."""
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        for entry in out.wire_log:
            if entry["direction"] == "client_to_server":
                assert entry["valid_ecma430"], f"Invalid NLIP message: {entry['message']}"


# ===========================================================================
# Schemas
# ===========================================================================

class TestSchemas:
    def test_client_schema_is_valid_jsonschema(self):
        import jsonschema
        from nlipeval.agents.schemas import CLIENT_SCHEMA
        jsonschema.Draft7Validator.check_schema(CLIENT_SCHEMA)

    def test_server_schema_is_valid_jsonschema(self):
        import jsonschema
        from nlipeval.agents.schemas import SERVER_SCHEMA
        jsonschema.Draft7Validator.check_schema(SERVER_SCHEMA)

    def test_valid_client_turn_validates(self):
        import jsonschema
        from nlipeval.agents.schemas import CLIENT_SCHEMA
        jsonschema.validate(
            {"action": "request", "message": "hi", "final": None}, CLIENT_SCHEMA
        )

    def test_valid_client_final_validates(self):
        import jsonschema
        from nlipeval.agents.schemas import CLIENT_SCHEMA
        jsonschema.validate(
            {"action": "final", "message": "",
             "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}},
            CLIENT_SCHEMA
        )

    def test_valid_server_ask_validates(self):
        import jsonschema
        from nlipeval.agents.schemas import SERVER_SCHEMA
        jsonschema.validate(
            {"action": "ask", "message": "What phone?", "plan": None, "asked_fields": ["device.phoneNumber"]},
            SERVER_SCHEMA
        )

    def test_valid_server_restate_validates(self):
        import jsonschema
        from nlipeval.agents.schemas import SERVER_SCHEMA
        jsonschema.validate(
            {"action": "restate", "message": "I will POST...",
             "plan": {"method": "POST", "path": "/x"}, "asked_fields": None},
            SERVER_SCHEMA
        )


# ===========================================================================
# Prompt rendering
# ===========================================================================

class TestPromptRendering:
    def test_render_client_p1(self, tmp_path):
        from nlipeval.agents.prompts import render_client
        task = minimal_task()
        prompt = render_client(task, "P1")
        assert "v1.0.0" in prompt
        assert "Is phone +9901000001 reachable" in prompt
        assert "action" in prompt   # schema is included

    def test_render_client_p2(self, tmp_path):
        from nlipeval.agents.prompts import render_client
        task = minimal_task()
        prompt = render_client(task, "P2")
        assert "check every restatement" in prompt.lower() or "NLIP conventions" in prompt

    def test_render_client_nlip0(self, tmp_path):
        from nlipeval.agents.prompts import render_client
        task = minimal_task()
        prompt = render_client(task, "P2", condition="NLIP-0")
        assert "cannot ask" in prompt.lower() or "NLIP-0" in prompt

    def test_render_server_p1(self, tmp_path):
        from nlipeval.agents.prompts import render_server
        prompt = render_server("L1", "v1.0.0", "P1")
        assert "v1.0.0" in prompt
        assert "action" in prompt

    def test_render_server_l3_has_profile_table(self, tmp_path):
        from nlipeval.agents.prompts import render_server
        prompt = render_server("L3", "v1.1.0", "P2")
        assert "QoS profile table" in prompt or "name | status" in prompt

    def test_prompts_hash_stable(self, tmp_path):
        from nlipeval.agents.prompts import prompts_hash
        h1 = prompts_hash()
        h2 = prompts_hash()
        assert h1 == h2 and len(h1) == 64


# ===========================================================================
# End-to-end test with live backends
# ===========================================================================

@pytest.mark.e2e
class TestEndToEnd:
    """Full session with live backends, checking log file completeness."""

    @pytest.fixture(autouse=True)
    def _start_backends(self, tmp_path):
        """Start the three mock backends."""
        from nlipeval.backends.launcher import up, down
        try:
            self.procs = up("127.0.0.1", None, run_dir=tmp_path)
            self.backend_urls = {api: p["url"] for api, p in self.procs.items()}
        except SystemExit:
            pytest.skip("Backends already running or could not start")
        yield
        down()

    @pytest.mark.parametrize("condition", ["NLIP", "NLIP-0"])
    def test_l1_session_complete(self, tmp_path, condition):
        """Run a session and verify SessionOutcome completeness."""
        from pathlib import Path
        from tests.fake_model import make_adapter, minimal_task
        from nlipeval.agents.client import ClientAgent
        from nlipeval.agents.server import ServerAgent
        from nlipeval.runner.session import SessionConfig, run_session
        from nlipeval.agents.prompts import render_client, render_server
        import json

        task = None
        # load a real task
        tasks_dir = Path(__file__).parent.parent / "tasks" / "L1"
        for p in sorted(tasks_dir.glob("*-v1.0.0.json")):
            task = json.loads(p.read_text())
            break
        if task is None:
            pytest.skip("No L1 tasks found")

        replies = NLIP0_EXECUTE if condition == "NLIP-0" else NLIP_ASK_ANSWER_RESTATE_CONFIRM
        adapter, _ = make_adapter(tmp_path, replies)
        client_sys = render_client(task, "P2", condition)
        server_sys = render_server(task["api"], task["server_version"], "P2", condition)

        cfg = SessionConfig(
            rung="R3",
            prompt="P2",
            condition=condition,
            attempt=1,
            run_id="e2e-test",
            client_agent=ClientAgent(adapter, "R3", client_sys, "e2e"),
            server_agent=ServerAgent(adapter, "R3", server_sys, "e2e"),
            backend_urls=self.backend_urls,
            wall_time_limit_s=60.0,
        )
        out = run_session(task, cfg)

        # basic completeness checks
        assert out.session_id
        assert out.termination in (
            "final", "declined", "max_interactions", "timeout",
            "error_model", "error_harness"
        )
        assert out.started_utc and out.ended_utc
        assert out.wall_seconds >= 0

        # wire log entries have direction and valid_ecma430
        for entry in out.wire_log:
            assert "direction" in entry
            assert "valid_ecma430" in entry

    @pytest.mark.parametrize("api", ["L1", "L2", "L3"])
    def test_multiple_apis_e2e(self, tmp_path, api):
        """Check L1/L2/L3 all run to completion."""
        from pathlib import Path
        import json
        from tests.fake_model import make_adapter
        from nlipeval.agents.client import ClientAgent
        from nlipeval.agents.server import ServerAgent
        from nlipeval.runner.session import SessionConfig, run_session
        from nlipeval.agents.prompts import render_client, render_server

        tasks_dir = Path(__file__).parent.parent / "tasks" / api
        task = None
        for p in sorted(tasks_dir.glob("*-v*.json")):
            task = json.loads(p.read_text())
            break
        if task is None:
            pytest.skip(f"No {api} tasks found")

        adapter, _ = make_adapter(tmp_path, NLIP0_EXECUTE)
        client_sys = render_client(task, "P2", "NLIP-0")
        server_sys = render_server(task["api"], task["server_version"], "P2", "NLIP-0")

        cfg = SessionConfig(
            rung="R3",
            prompt="P2",
            condition="NLIP-0",
            attempt=1,
            run_id="e2e-test",
            client_agent=ClientAgent(adapter, "R3", client_sys, "e2e"),
            server_agent=ServerAgent(adapter, "R3", server_sys, "e2e"),
            backend_urls=self.backend_urls,
            wall_time_limit_s=60.0,
        )
        out = run_session(task, cfg)
        assert out.termination in (
            "final", "declined", "max_interactions", "timeout",
            "error_model", "error_harness"
        )


# ===========================================================================
# 07b: logging, error classes, time limits, task filter, prompt wording
# ===========================================================================

class TestClientReplyAndSlips:
    def test_client_reply_logged(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        replies = {p.action: p.client_reply for p in out.plans}
        assert replies["ask"] == "answer"
        assert replies["restate"] == "confirm"

    def test_correct_logged(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_CORRECT_THEN_CONFIRM, backend_urls=backend_200)
        assert [p.client_reply for p in out.plans if p.action == "restate"] == ["correct", "confirm"]

    def test_abort_logged(self, tmp_path):
        out = _run(tmp_path, NLIP_ABORT)
        assert "abort" in [p.client_reply for p in out.plans]

    def test_slips_counted_nlip(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_PROTOCOL_SLIP_EXECUTE_BEFORE_CONFIRM, backend_urls=backend_200)
        assert out.n_protocol_slips == 1

    def test_slips_counted_nlip0(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_PROTOCOL_SLIP_ASK, condition="NLIP-0", backend_urls=backend_200)
        assert out.n_protocol_slips == 1

    def test_no_slip_on_clean_session(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_ASK_ANSWER_RESTATE_CONFIRM, backend_urls=backend_200)
        assert out.n_protocol_slips == 0


class TestMissingFinal:
    @staticmethod
    def _no_final(script):
        s = [dict(x) for x in script]
        s[-1] = {"role": "client", "reply": {"action": "final", "message": "", "final": None}}
        return s

    def test_nlip_last_turn_without_final_is_a_slip(self, tmp_path, backend_200):
        out = _run(tmp_path, self._no_final(NLIP_CORRECT_THEN_CONFIRM), backend_urls=backend_200)
        assert out.termination == "final" and out.client_final is None
        assert out.n_protocol_slips == 1 and any("no final answer" in e for e in out.errors)

    def test_nlip0_last_turn_without_final_is_a_slip(self, tmp_path, backend_200):
        out = _run(tmp_path, self._no_final(NLIP0_EXECUTE), condition="NLIP-0", backend_urls=backend_200)
        assert out.termination == "final" and out.client_final is None
        assert out.n_protocol_slips == 1


class TestErrorClasses:
    @staticmethod
    def _res(error_type, error="x"):
        from nlipeval.models.adapter import Result
        return Result(error=error, error_type=error_type)

    @pytest.mark.parametrize("et", ["http_429", "http_500", "http_503", "connection", "timeout"])
    def test_infrastructure_is_harness(self, et):
        from nlipeval.runner.session import _HarnessError, _fail
        with pytest.raises(_HarnessError):
            _fail(self._res(et), "client error")

    @pytest.mark.parametrize("et", ["parse_failure", "refusal"])
    def test_model_failures_are_model(self, et):
        from nlipeval.runner.session import _ModelError, _fail
        with pytest.raises(_ModelError):
            _fail(self._res(et), "client error")

    def test_timeout_is_rerun_once_at_double_limit(self, tmp_path, monkeypatch):
        import nlipeval.runner.run as runner
        from nlipeval.runner.session import SessionOutcome

        limits = []

        def fake_run_session(task, cfg):
            limits.append(cfg.wall_time_limit_s)
            return SessionOutcome(session_id=f"s{len(limits)}", termination="timeout",
                                  wall_seconds=cfg.wall_time_limit_s)

        monkeypatch.setattr("nlipeval.runner.session.run_session", fake_run_session)
        adapter, _ = make_adapter(tmp_path, [{"role": "client", "reply": {}}])
        rec, _wire = runner._run_one(minimal_task(), "R3", "P2", "NLIP", 1, "r", adapter,
                                     {}, {"R3": {}}, 100.0)
        assert limits == [100.0, 200.0]                # one re-run, at twice the limit
        assert rec["termination"] == "timeout"        # a second timeout is a failure
        assert rec["timeout_rerun"]["first_limit_s"] == 100.0


class TestTimeLimits:
    def test_nlip_http_timeout_exceeds_a_model_call(self, tmp_path):
        adapter, _ = make_adapter(tmp_path, [{"role": "client", "reply": {}}])
        # one call: 10 s rung timeout x 4 tries + back-off, doubled for the repair call
        assert adapter.max_call_seconds("R3") + 30 > 60
        from nlipeval.runner.session import SessionConfig
        assert SessionConfig.__dataclass_fields__["nlip_http_timeout_s"].default == 60.0

    def test_models_yaml_session_limits(self):
        import yaml
        from nlipeval.runner.run import CONFIG_DIR
        rungs = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text())["rungs"]
        assert rungs["R1"]["session_limit_s"] == 3600
        assert all(rungs[r]["session_limit_s"] == 1200 for r in ("R2", "R3", "R4"))

    def test_real_rung_http_timeout_covers_adapter(self):
        from nlipeval.models.adapter import ModelAdapter
        from nlipeval.runner.run import CONFIG_DIR
        a = ModelAdapter(CONFIG_DIR / "models.yaml", Path("/tmp/nlipeval-limits-test"))
        for r in ("R1", "R2", "R3", "R4"):
            assert a.max_call_seconds(r) + 30 > 60


class TestTaskFilter:
    def test_round_b_refused_without_flag(self):
        from nlipeval.runner.run import _load_tasks
        with pytest.raises(SystemExit):
            _load_tasks({"task_filter": {"pilot_round": "B"}})
        with pytest.raises(SystemExit):
            _load_tasks({"task_filter": {"pilot_only": True}})

    def test_round_b_allowed_with_flag(self):
        from nlipeval.runner.run import _load_tasks
        tasks = _load_tasks({"allow_round_b": True, "task_filter": {"pilot_round": "B"}})
        assert len(tasks) == 45 and {t["pilot_round"] for t in tasks} == {"B"}

    def test_round_a_and_main(self):
        from nlipeval.runner.run import _load_tasks
        assert len(_load_tasks({"task_filter": {"pilot_round": "A"}})) == 45
        assert len(_load_tasks({"task_filter": {"main_only": True}})) == 420

    def test_per_api_limit(self):
        from nlipeval.runner.run import _load_tasks
        t = _load_tasks({"task_filter": {"pilot_round": "A", "per_api_limit": 1}})
        assert len(t) == 9 and len({x["intent_id"] for x in t}) == 1

    def test_smoke_matrix_is_12_sessions(self):
        import yaml
        from nlipeval.runner.run import CONFIG_DIR, _load_tasks, _parts
        m = yaml.safe_load((CONFIG_DIR / "runs" / "smoke-r3.yaml").read_text())
        tasks = _load_tasks(m)
        assert len(tasks) == 6 and not any(t["pilot_round"] == "B" for t in tasks)
        assert len(tasks) * len(m["rungs"]) * len(m["prompts"]) * len(m["conditions"]) == 12
        assert {(t["api"], t["versions_behind"] in (0,)) for t in tasks} >= {("L1", True), ("L2", True), ("L3", True)}

    def test_pilot_matrix_counts(self):
        import yaml
        from nlipeval.runner.run import CONFIG_DIR, _load_part_tasks, _parts
        m = yaml.safe_load((CONFIG_DIR / "runs" / "pilot.yaml").read_text())
        assert not m.get("allow_round_b")
        n = [len(_load_part_tasks(p, False)) * len(p["rungs"]) * len(p["prompts"]) * len(p["conditions"])
             for p in _parts(m)]
        assert n == [360, 60]


class TestPromptWording:
    TASK_VERSIONS = [("L1", "v0.5.1"), ("L2", "v0.1.0"), ("L3", "v0.11.0"), ("L3", "v1.1.0")]

    @staticmethod
    def _task(api, v):
        root = Path(__file__).resolve().parents[1]
        p = root / "tasks" / api / f"{api}-p01-{v}.json"
        if not p.exists():                       # pilot instances exist for 3 versions per API only
            p = root / "tasks" / api / f"{api}-m01-{v}.json"
        return json.loads(p.read_text())

    @pytest.mark.parametrize("api,v", TASK_VERSIONS)
    def test_client_section_order(self, api, v):
        from nlipeval.agents.prompts import render_client
        task = self._task(api, v)
        text = render_client(task, "P3")
        marks = ["You are a client agent", "## Your interface", "## Notes on", "## NLIP conventions",
                 "## Turn contract", "## Your task", "Intent:", "Your native request",
                 "Facts you know that are not in your native request:", "The result you must return"]
        idx = [text.index(m) for m in marks]
        assert idx == sorted(idx)

    @pytest.mark.parametrize("pt,cond", [("P1", "NLIP"), ("P2", "NLIP"), ("P3", "NLIP"), ("P2", "NLIP-0")])
    def test_facts_wording_and_status_definitions(self, pt, cond):
        from nlipeval.agents.prompts import render_client
        text = render_client(self._task("L2", "v0.1.0"), pt, cond)
        assert "Facts you know that are not in your native request:" in text
        assert "gold" not in text.lower()
        assert "Facts you can supply" not in text
        for d in ('"done": the call was carried out, and its result is in "result".',
                  '"declined": there is no result, because the server declined or the service refused.',
                  '"unrepresentable": the call was carried out, but its result cannot be expressed in your interface.'):
            assert d in text

    def test_nlip0_is_p2_with_only_interaction_rules_replaced(self):
        from nlipeval.agents.prompts import render_client, render_server
        task = self._task("L1", "v1.0.0")
        for a, b in ((render_client(task, "P2"), render_client(task, "P2", "NLIP-0")),):
            ia = a.index("## NLIP conventions"); ib = b.index("## NLIP-0 conventions")
            assert a[:ia].replace("over NLIP.", "X") == b[:ib].replace("over NLIP in no-interaction mode.", "X")
            assert a[a.index("## Your task"):] == b[b.index("## Your task"):]
        s2 = render_server("L1", "v1.0.0", "P2"); s0 = render_server("L1", "v1.0.0", "P2", "NLIP-0")
        assert "never invent" in s2.lower() and "never invent" in s0.lower()
        assert "client's terms" in s2 and "client's terms" in s0
        assert "own interface's terms" in render_client(task, "P2", "NLIP-0")

    def test_missing_notes_is_an_error(self, monkeypatch, tmp_path):
        import nlipeval.agents.prompts as P
        monkeypatch.setattr(P, "NOTES_DIR", tmp_path)
        with pytest.raises(FileNotFoundError):
            P.render_client(self._task("L1", "v1.0.0"), "P3")

    def test_excerpt_json_only(self, monkeypatch, tmp_path):
        import nlipeval.agents.prompts as P
        monkeypatch.setattr(P, "SPECS_DIR", tmp_path)
        with pytest.raises(FileNotFoundError):
            P._load_excerpt("L1", "v1.0.0")

    def test_sources_files_not_in_prompts_hash(self, monkeypatch):
        import nlipeval.agents.prompts as P
        h = P.prompts_hash()
        p = P.NOTES_DIR / "L1" / "v1.0.0.sources.md"
        old = p.read_text()
        try:
            p.write_text(old + "\nextra\n")
            assert P.prompts_hash() == h
        finally:
            p.write_text(old)

    def test_every_version_and_prompt_type_renders(self):
        import glob
        from nlipeval.agents.prompts import render_client, render_server
        seen = set()
        root = Path(__file__).resolve().parents[1]
        for f in sorted(glob.glob(str(root / "tasks/*/*-m01-*.json"))):
            t = json.loads(Path(f).read_text())
            for pt in ("P1", "P2", "P3"):
                assert render_client(t, pt) and render_server(t["api"], t["server_version"], pt)
            assert render_client(t, "P2", "NLIP-0") and render_server(t["api"], t["server_version"], "P2", "NLIP-0")
            seen.add((t["api"], t["client_version"]))
        assert len(seen) == 14


# ===========================================================================
# 08a B6-B8: action repair, always end with the client's final
# ===========================================================================

def _c(action, message="ok", final=None):
    return {"role": "client", "reply": {"action": action, "message": message, "final": final}}


def _s(action, message="m", plan=None, asked=None):
    return {"role": "server", "reply": {"action": action, "message": message, "plan": plan, "asked_fields": asked}}


_PLAN = {"method": "POST", "path": "/device-reachability-status/v1/retrieve",
         "body": {"device": {"phoneNumber": "+9901000001"}}}
_FINAL_DONE = {"status": "done", "result": {"reachable": True}, "explanation": "ok"}
_FINAL_DECLINED = {"status": "declined", "result": None, "explanation": "declined"}


class TestActionRepair:
    def test_repeated_request_is_repaired_then_confirmed(self, tmp_path, backend_200):
        script = [_c("request", "Is +9901000001 reachable?"), _s("restate", "I plan this. Shall I go ahead?", _PLAN),
                  _c("request", "Is +9901000001 reachable?"),          # disallowed after restate
                  _c("confirm", "Yes"),                                  # repaired
                  _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "final" and out.client_final == _FINAL_DONE
        assert (out.n_action_repairs_client, out.n_action_repairs_server) == (1, 0)

    def test_disallowed_action_twice_is_error_model(self, tmp_path, backend_200):
        script = [_c("request"), _s("restate", "plan?", _PLAN), _c("request"), _c("request")]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "error_model"
        assert out.n_action_repairs_client == 1

    def test_server_report_before_execution_is_repaired(self, tmp_path, backend_200):
        script = [_c("request"), _s("report", "Reachable."),            # not allowed after request
                  _s("restate", "plan. Shall I go ahead?", _PLAN),
                  _c("confirm"), _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "final"
        assert (out.n_action_repairs_client, out.n_action_repairs_server) == (0, 1)

    def test_server_disallowed_twice_is_error_model(self, tmp_path, backend_200):
        out = _run(tmp_path, [_c("request"), _s("report", "x")], backend_urls=backend_200)
        assert out.termination == "error_model" and out.n_action_repairs_server == 1

    def test_server_ask_after_execution_is_repaired(self, tmp_path, backend_200):
        script = [_c("request"), _s("restate", "plan?", _PLAN), _c("confirm"),
                  _s("ask", "which phone?", asked=["device"]),            # not allowed after execution
                  _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "final" and out.n_action_repairs_server == 1

    def test_client_final_instead_of_answer_is_repaired(self, tmp_path, backend_200):
        script = [_c("request"), _s("ask", "which phone?", asked=["device"]),
                  _c("final", "", _FINAL_DONE), _c("answer", "+9901000001"),
                  _s("restate", "plan?", _PLAN), _c("confirm"), _s("report", "Reachable."),
                  _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "final" and out.n_action_repairs_client == 1

    def test_client_non_final_after_report_is_repaired(self, tmp_path, backend_200):
        script = [_c("request"), _s("restate", "plan?", _PLAN), _c("confirm"), _s("report", "Reachable."),
                  _c("confirm"), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "final" and out.client_final == _FINAL_DONE
        assert out.n_action_repairs_client == 1

    def test_nlip0_clean_session_has_no_repairs(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_EXECUTE, condition="NLIP-0", backend_urls=backend_200)
        assert (out.n_action_repairs_client, out.n_action_repairs_server) == (0, 0)

    def test_nlip0_server_report_first_is_repaired(self, tmp_path, backend_200):
        script = [_c("request"), _s("report", "x"), _s("execute", "go", _PLAN), _s("report", "Reachable."),
                  _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_200)
        assert out.termination == "final" and out.n_action_repairs_server == 1

    def test_nlip0_client_answer_first_is_repaired(self, tmp_path, backend_200):
        script = [_c("answer"), _c("request"), _s("execute", "go", _PLAN), _s("report", "Reachable."),
                  _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_200)
        assert out.termination == "final" and out.n_action_repairs_client == 1

    def test_nlip0_slips_are_not_repaired(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP0_PROTOCOL_SLIP_ASK, condition="NLIP-0", backend_urls=backend_200)
        assert out.n_protocol_slips == 1 and out.n_action_repairs_server == 0

    def test_nlip_execute_slip_is_not_repaired(self, tmp_path, backend_200):
        out = _run(tmp_path, NLIP_PROTOCOL_SLIP_EXECUTE_BEFORE_CONFIRM, backend_urls=backend_200)
        assert out.n_protocol_slips == 1 and out.n_action_repairs_server == 0

    def test_repair_call_is_logged_with_purpose_repair(self, tmp_path, backend_200):
        script = [_c("request"), _s("restate", "plan?", _PLAN), _c("request"), _c("confirm"),
                  _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        _run(tmp_path, script, backend_urls=backend_200)
        calls = [json.loads(l) for l in (tmp_path / "run" / "calls.jsonl").read_text().splitlines()]
        assert [c["purpose"] for c in calls].count("repair") == 1


class TestAlwaysEndsWithFinal:
    def test_abort_is_followed_by_final_and_stays_declined(self, tmp_path):
        out = _run(tmp_path, NLIP_ABORT)
        assert out.termination == "declined" and out.client_final["status"] == "declined"

    def test_abort_after_restate_is_followed_by_final(self, tmp_path):
        script = [_c("request"), _s("restate", "plan?", _PLAN), _c("abort", "no"),
                  _c("final", "", _FINAL_DECLINED)]
        out = _run(tmp_path, script)
        assert out.termination == "declined" and out.client_final == _FINAL_DECLINED

    def test_abort_then_non_final_is_repaired(self, tmp_path):
        script = [_c("request"), _s("ask", "which?", asked=["x"]), _c("abort", "no"),
                  _c("abort", "no"), _c("final", "", _FINAL_DECLINED)]
        out = _run(tmp_path, script)
        assert out.termination == "declined" and out.client_final == _FINAL_DECLINED
        assert out.n_action_repairs_client == 1

    def test_server_decline_is_followed_by_final(self, tmp_path):
        out = _run(tmp_path, NLIP_SERVER_DECLINE)
        assert out.termination == "declined" and out.client_final["status"] == "declined"

    def test_server_decline_without_final_object_is_not_silent(self, tmp_path):
        script = [_c("request"), _s("decline", "no"), _c("confirm"), _c("confirm")]
        out = _run(tmp_path, script)
        assert out.termination == "error_model"

    def test_nlip0_decline_is_followed_by_final(self, tmp_path):
        out = _run(tmp_path, NLIP0_DECLINE, condition="NLIP-0")
        assert out.termination == "declined" and out.client_final["status"] == "declined"


class TestRepairCountersRecorded:
    def test_session_record_carries_the_counters(self, tmp_path, monkeypatch):
        import nlipeval.runner.run as runner
        from nlipeval.runner.session import SessionOutcome

        def fake_run_session(task, cfg):
            return SessionOutcome(session_id="s", termination="final",
                                  n_action_repairs_client=2, n_action_repairs_server=1)

        monkeypatch.setattr("nlipeval.runner.session.run_session", fake_run_session)
        adapter, _ = make_adapter(tmp_path, [{"role": "client", "reply": {}}])
        rec, _w = runner._run_one(minimal_task(), "R3", "P2", "NLIP", 1, "r", adapter, {}, {"R3": {}}, 100.0)
        assert rec["n_action_repairs_client"] == 2 and rec["n_action_repairs_server"] == 1


# ===========================================================================
# 08a H3-H6 (review of stage 08a): NLIP-0 report failures, the NLIP-0 report after a rejection,
# the client's confirm in its own history, a correction after a backend rejection
# ===========================================================================

_REJECT = {"status": 400, "body": {"status": 400, "code": "INVALID_ARGUMENT", "message": "bad"}}
_OK = {"status": 200, "body": {"reachable": True, "connectivity": ["DATA"]}}
_PLAN2 = {"method": "POST", "path": "/device-reachability-status/v1/retrieve",
          "body": {"device": {"phoneNumber": "+9901000002"}}}


def _calls(tmp_path):
    return [json.loads(l) for l in (tmp_path / "run" / "calls.jsonl").read_text().splitlines()]


def _backend(responses):
    srv, url = _make_mock_backend_server(responses)
    return srv, {"L1": url, "L2": url, "L3": url}


class TestNlip0Report:
    def test_report_disallowed_twice_is_error_model(self, tmp_path, backend_200):
        script = [_c("request"), _s("execute", "go", _PLAN), _s("ask", "x"), _s("ask", "y")]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_200)
        assert out.termination == "error_model" and out.n_action_repairs_server == 1

    def test_report_repaired_once_is_final(self, tmp_path, backend_200):
        script = [_c("request"), _s("execute", "go", _PLAN), _s("ask", "x"), _s("report", "Reachable."),
                  _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_200)
        assert out.termination == "final" and out.n_action_repairs_server == 1

    def test_report_of_a_rejection_is_used_at_once(self, tmp_path, backend_400_then_200):
        script = [_c("request"), _s("execute", "go", _PLAN), _s("report", "Error 400 INVALID_ARGUMENT."),
                  _c("final", "", _FINAL_DECLINED)]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_400_then_200)
        assert out.termination == "final" and out.client_final == _FINAL_DECLINED
        assert out.n_server_retries == 0 and len(out.executed_calls) == 1
        purposes = [c["purpose"] for c in _calls(tmp_path) if c["role"] == "server"]
        assert purposes == ["plan", "report"]
        final_call = [c for c in _calls(tmp_path) if c["purpose"] == "final"][-1]
        assert final_call["messages"][-1]["content"] == "Error 400 INVALID_ARGUMENT."

    def test_retry_then_report(self, tmp_path, backend_400_then_200):
        script = [_c("request"), _s("execute", "go", _PLAN), _s("execute", "again", _PLAN2),
                  _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_400_then_200)
        assert out.termination == "final" and out.n_server_retries == 1
        assert [e.status for e in out.executed_calls] == [400, 200] and out.n_protocol_slips == 0

    def test_restate_as_retry_is_a_slip(self, tmp_path, backend_400_then_200):
        script = [_c("request"), _s("execute", "go", _PLAN), _s("restate", "again?", _PLAN2),
                  _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, condition="NLIP-0", backend_urls=backend_400_then_200)
        assert out.termination == "final" and out.n_server_retries == 1
        assert out.n_protocol_slips == 1 and out.n_action_repairs_server == 0


class TestClientConfirmInHistory:
    def test_final_sees_its_confirm_before_the_report(self, tmp_path, backend_200):
        script = [_c("request", "Is +9901000001 reachable?"), _s("restate", "plan. Shall I go ahead?", _PLAN),
                  _c("confirm", "Yes, go ahead"), _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_200)
        assert out.termination == "final"
        msgs = [c for c in _calls(tmp_path) if c["purpose"] == "final"][-1]["messages"]
        assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant", "user"]
        assert json.loads(msgs[3]["content"])["action"] == "confirm"
        assert msgs[4]["content"] == "Reachable."

    def test_no_two_user_turns_in_a_row_after_a_rejection(self, tmp_path, backend_400_then_200):
        out = _run(tmp_path, NLIP_BACKEND_REJECTION, backend_urls=backend_400_then_200)
        assert out.termination == "final"
        msgs = [c for c in _calls(tmp_path) if c["purpose"] == "final"][-1]["messages"]
        roles = [m["role"] for m in msgs]
        assert all(a != b for a, b in zip(roles, roles[1:])), roles
        assert [json.loads(m["content"])["action"] for m in msgs if m["role"] == "assistant"] == \
            ["request", "confirm", "confirm"]


class TestCorrectionAfterRejection:
    def test_correction_goes_to_the_server_and_its_new_plan_runs(self, tmp_path, backend_400_then_200):
        script = [_c("request"), _s("restate", "plan A. Shall I go ahead?", _PLAN), _c("confirm"),
                  _s("restate", "Rejected. Plan B. Shall I go ahead?", _PLAN),     # after the rejection
                  _c("correct", "Use +9901000002 instead"),
                  _s("restate", "Plan C with +9901000002. Shall I go ahead?", _PLAN2),
                  _c("confirm"), _s("report", "Reachable."), _c("final", "", _FINAL_DONE)]
        out = _run(tmp_path, script, backend_urls=backend_400_then_200)
        assert out.termination == "final" and out.client_final == _FINAL_DONE
        assert out.n_corrections == 1
        assert [e.body for e in out.executed_calls] == [_PLAN["body"], _PLAN2["body"]]
        server_plan_msgs = [c["messages"] for c in _calls(tmp_path) if c["role"] == "server" and c["purpose"] == "plan"]
        assert server_plan_msgs[-1][-1]["content"] == "Use +9901000002 instead"

    def test_abort_after_rejection_restate_ends_with_final(self, tmp_path, backend_400_then_200):
        script = [_c("request"), _s("restate", "plan?", _PLAN), _c("confirm"),
                  _s("restate", "Rejected. New plan?", _PLAN2), _c("abort", "no"),
                  _c("final", "", _FINAL_DECLINED)]
        out = _run(tmp_path, script, backend_urls=backend_400_then_200)
        assert out.termination == "declined" and out.client_final == _FINAL_DECLINED
        assert len(out.executed_calls) == 1

    def test_restate_after_the_second_execution_is_repaired(self, tmp_path):
        srv, urls = _backend([_REJECT, _REJECT])
        try:
            script = [_c("request"), _s("restate", "plan?", _PLAN), _c("confirm"),
                      _s("restate", "Rejected. New plan?", _PLAN2), _c("confirm"),
                      _s("restate", "Rejected again?", _PLAN),              # not allowed after a second execution
                      _s("report", "Error 400 INVALID_ARGUMENT."), _c("final", "", _FINAL_DECLINED)]
            out = _run(tmp_path, script, backend_urls=urls)
        finally:
            srv.shutdown()
        assert out.termination == "final" and out.n_action_repairs_server == 1
        assert len(out.executed_calls) == 2

    def test_interactions_counted_as_before(self, tmp_path, backend_400_then_200):
        out = _run(tmp_path, NLIP_BACKEND_REJECTION, backend_urls=backend_400_then_200)
        assert (out.n_restatements, out.n_interactions, out.n_corrections) == (2, 1, 0)


# ===========================================================================
# 08a H1-H2 (review of stage 08a): provenance and run IDs
# ===========================================================================

def _matrix_keys(name):
    import yaml
    from nlipeval.runner.run import CONFIG_DIR, _load_part_tasks, _parts
    m = yaml.safe_load((CONFIG_DIR / "runs" / name).read_text())
    return m, {(t["task_id"], r, p, c) for part in _parts(m) for t in _load_part_tasks(part, False)
               for r in part["rungs"] for p in part["prompts"] for c in part["conditions"]}


class TestRunProvenance:
    def test_pilot_slices_make_up_the_pilot(self):
        m, full = _matrix_keys("pilot.yaml")
        m1, r1 = _matrix_keys("pilot-r1.yaml")
        m2, rits = _matrix_keys("pilot-rits.yaml")
        assert r1 | rits == full and not r1 & rits
        assert (len(r1), len(rits)) == (120, 300)
        for x in (m, m1, m2):
            assert not x.get("run_id") and not x.get("allow_round_b") and not x.get("allow_dirty")
            assert x["stage"] == "stage8"

    def test_run_id_uses_the_stage_and_the_override(self):
        from nlipeval.runner.run import _make_run_id
        rid = _make_run_id({"stage": "stage8", "label": "pilot-r1"})
        assert rid.endswith("-stage8-pilot-r1") and len(rid.split("-")[0]) == 8
        assert _make_run_id({"run_id": "fixed", "stage": "stage8"}) == "fixed"
        assert _make_run_id({"run_id": "fixed"}, "given") == "given"

    def test_dirty_inputs_stop_the_run(self, tmp_path, monkeypatch):
        import nlipeval.runner.run as runner
        monkeypatch.setattr(runner, "_git_dirty_paths", lambda: ["experiments/nlipeval/runner/session.py"])
        mp = tmp_path / "m.yaml"
        mp.write_text("label: x\nstage: stage8\nrungs: [R3]\n")
        with pytest.raises(SystemExit, match="Uncommitted changes"):
            runner.run(mp)
        assert not (runner.DATA_DIR / runner._make_run_id({"stage": "stage8", "label": "x"})).exists()

    def test_resume_needs_the_same_provenance(self, tmp_path):
        from nlipeval.runner.run import PROVENANCE_KEYS, _check_resume
        old = {"run_id": "r", "created_utc": "2026-11-18T00:00:00Z", **{k: "a" for k in PROVENANCE_KEYS}}
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(old))
        same = {**old, "created_utc": "2026-11-19T00:00:00Z"}
        _check_resume(mp, same, {})
        assert same["created_utc"] == old["created_utc"] and len(same["resumed_utc"]) == 1
        changed = {**old, "git_commit": "b"}
        with pytest.raises(SystemExit, match="git_commit"):
            _check_resume(mp, changed, {})
        _check_resume(mp, {**old, "tasks_hash": "b"}, {"allow_dirty": True})   # a test run may resume

    def test_new_run_has_no_resume_fields(self, tmp_path):
        from nlipeval.runner.run import _check_resume
        m = {"run_id": "r", "created_utc": "t"}
        _check_resume(tmp_path / "manifest.json", m, {})
        assert m == {"run_id": "r", "created_utc": "t"}

    def test_dirty_paths_cover_only_inputs(self):
        from nlipeval.runner.run import GIT_INPUT_PATHS, _git_dirty_paths
        assert {"nlipeval", "prompts", "tasks", "config", "specs"} <= set(GIT_INPUT_PATHS)
        paths = _git_dirty_paths()
        assert paths is None or all(not p.startswith(("experiments/data/", "experiments/results/",
                                                      "experiments/reports/")) for p in paths)
