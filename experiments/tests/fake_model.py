"""Scripted fake model for harness tests (stage 06).

`FakeModel` is an adapter-compatible object that plays back scripted responses.
`make_adapter(tmp_path, script)` creates a ModelAdapter wired to a fake HTTP server
that returns the scripted replies in order.

A script is a list of dicts, each with:
  - "role": "client" | "server"   (which agent this reply is for; just documentation)
  - "reply": a dict that will be JSON-serialised and returned as the model's content

Example:
    script = [
        {"role": "client", "reply": {"action": "request", "message": "Is phone X reachable?", "final": null}},
        {"role": "server", "reply": {"action": "restate", "message": "I will POST ...", "plan": {...}, "asked_fields": null}},
        ...
    ]
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import yaml

from nlipeval.models.adapter import ModelAdapter


class _Script:
    def __init__(self, replies: list[dict]) -> None:
        self._replies = list(replies)
        self._idx = 0
        self._lock = threading.Lock()

    def next_reply(self) -> dict:
        with self._lock:
            if self._idx < len(self._replies):
                r = self._replies[self._idx]
                self._idx += 1
                return r
            # repeat last if script is exhausted
            return self._replies[-1]

    @property
    def index(self) -> int:
        with self._lock:
            return self._idx


def _make_server(script: _Script) -> HTTPServer:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a: Any) -> None:
            pass

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            entry = script.next_reply()
            content = json.dumps(entry.get("reply", {}))
            payload = json.dumps({
                "id": "1", "object": "chat.completion", "created": 0, "model": "fake",
                "choices": [{"index": 0, "finish_reason": "stop",
                              "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                          "completion_tokens_details": {"reasoning_tokens": 0}},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def make_adapter(tmp_path: Path, replies: list[dict]) -> tuple[ModelAdapter, _Script]:
    """Create a (ModelAdapter, _Script) pair wired to a fake HTTP server.

    `replies` is a list of {"role": ..., "reply": <dict to return as content>}.

    The adapter exposes a single rung "R3" pointing at the fake server.
    """
    script = _Script(replies)
    srv = _make_server(script)
    port = srv.server_address[1]

    import os
    os.environ["FAKE_TEST_URL"] = f"http://127.0.0.1:{port}/v1"
    os.environ["FAKE_TEST_KEY"] = "fake-key"

    cfg = {"rungs": {
        "R3": {
            "provider": "fake",
            "model": "fake-model",
            "base_url_env": "FAKE_TEST_URL",
            "api_key_env": "FAKE_TEST_KEY",
            "params": {},
            "extra_body": {},
            "max_concurrency": 1,
            "timeout_s": 10,
            "structured_output_mode": "json_schema",
            "system_role_supported": True,
        }
    }}
    cfg_path = tmp_path / "models.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))

    adapter = ModelAdapter(cfg_path, tmp_path / "run", retry_base_delay_s=0.001)
    return adapter, script


# --------------------------------------------------------------------------- common task fixture

def minimal_task(api: str = "L1") -> dict:
    """A minimal task instance for testing."""
    return {
        "schema_version": "1",
        "task_id": f"{api}-test-v1.0.0",
        "intent_id": "test",
        "pilot": True,
        "api": api,
        "operation": "retrieveReachability",
        "client_version": "v1.0.0",
        "server_version": "v1.0.0",
        "versions_behind": 0,
        "breaking_crossed": 0,
        "breaking_crossed_ops": 0,
        "catalogue_breaking_crossed": 0,
        "prompt_half": True,
        "pilot_round": "A",
        "intent_text": "Is phone +9901000001 reachable?",
        "client_native_request": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        },
        "client_facts": [],
        "client_answer_schema": {
            "type": "object",
            "required": ["reachable"],
            "properties": {
                "reachable": {"type": "boolean"},
                "connectivity": {"type": "array", "items": {"type": "string"}},
            },
        },
        "world_ref": {"device": "D01"},
        "gold_calls": [{
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        }],
        "gold_backend_response": {"status": 200, "body": {"reachable": True, "connectivity": ["DATA"]}},
        "gold_client_answer": {"status": "done", "result": {"reachable": True}},
        "missing_info": [],
        "change_tags_request": [],
        "change_tags_response": [],
        "material_fields": ["device"],
        "provenance": "authored",
    }


# --------------------------------------------------------------------------- scripted sessions

# NLIP: happy path (ask → answer → restate → confirm → execute → report → final)
NLIP_ASK_ANSWER_RESTATE_CONFIRM = [
    # client request (turn 1)
    {"role": "client", "reply": {
        "action": "request", "message": "Is phone +9901000001 reachable?", "final": None}},
    # server ask (turn 2)
    {"role": "server", "reply": {
        "action": "ask", "message": "What phone number?",
        "plan": None, "asked_fields": ["device.phoneNumber"]}},
    # client answer (turn 3)
    {"role": "client", "reply": {
        "action": "answer", "message": "+9901000001", "final": None}},
    # server restate (turn 4)
    {"role": "server", "reply": {
        "action": "restate",
        "message": "I will POST to /device-reachability-status/v1/retrieve with phone +9901000001",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        },
        "asked_fields": None}},
    # client confirm (turn 5)
    {"role": "client", "reply": {
        "action": "confirm", "message": "Yes, go ahead.", "final": None}},
    # server report (turn 6 — called directly by harness after backend)
    {"role": "server", "reply": {
        "action": "report",
        "message": "The device is reachable with DATA connectivity.",
        "plan": None, "asked_fields": None}},
    # client final (turn 7)
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}}},
]

# NLIP: restate → correct → restate → confirm → report → final
NLIP_CORRECT_THEN_CONFIRM = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability for +9901000001", "final": None}},
    {"role": "server", "reply": {
        "action": "restate",
        "message": "I will POST with phone +9901000002 (wrong)",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000002"}},
        },
        "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "correct", "message": "No, the number is +9901000001, not +9901000002", "final": None}},
    {"role": "server", "reply": {
        "action": "restate",
        "message": "I will POST with phone +9901000001",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        },
        "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "confirm", "message": "Yes", "final": None}},
    {"role": "server", "reply": {
        "action": "report", "message": "Device is reachable.",
        "plan": None, "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}}},
]

# NLIP: client abort
NLIP_ABORT = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability", "final": None}},
    {"role": "server", "reply": {
        "action": "ask", "message": "Which phone?",
        "plan": None, "asked_fields": ["device.phoneNumber"]}},
    {"role": "client", "reply": {
        "action": "abort", "message": "Never mind.", "final": None}},
    # B7: after an abort the client still gives its final
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "declined", "result": None, "explanation": "aborted"}}},
]

# NLIP: server decline
NLIP_SERVER_DECLINE = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability for some unknown device", "final": None}},
    {"role": "server", "reply": {
        "action": "decline", "message": "I cannot process this request.",
        "plan": None, "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "declined", "result": None, "explanation": "server declined"}}},
]

# NLIP: protocol slip (server sends execute before confirm) → treated as restate
NLIP_PROTOCOL_SLIP_EXECUTE_BEFORE_CONFIRM = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability", "final": None}},
    {"role": "server", "reply": {
        "action": "execute",    # <-- slip: not allowed before confirm
        "message": "Executing now",
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

# NLIP: backend rejection → server restate again → client confirm → re-execute → report → final
NLIP_BACKEND_REJECTION = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability", "final": None}},
    {"role": "server", "reply": {
        "action": "restate",
        "message": "I will POST with bad phone",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "bad"}},   # will fail validation
        },
        "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "confirm", "message": "Yes", "final": None}},
    # server gets backend error, restates again (after backend call)
    {"role": "server", "reply": {
        "action": "restate",
        "message": "Let me correct the phone number",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        },
        "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "confirm", "message": "Yes", "final": None}},
    {"role": "server", "reply": {
        "action": "report", "message": "Device is reachable.", "plan": None, "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}}},
]

# NLIP-0: execute then report then final
NLIP0_EXECUTE = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability for +9901000001", "final": None}},
    {"role": "server", "reply": {
        "action": "execute",
        "message": "Executing",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        },
        "asked_fields": None}},
    # harness calls server.turn() with backend outcome → report
    {"role": "server", "reply": {
        "action": "report", "message": "Device is reachable.", "plan": None, "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}}},
]

# NLIP-0: server decline
NLIP0_DECLINE = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability", "final": None}},
    {"role": "server", "reply": {
        "action": "decline", "message": "Cannot process",
        "plan": None, "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "declined", "result": None, "explanation": "server declined"}}},
]

# NLIP-0: protocol slip (ask in NLIP-0 → take plan if present, else decline)
NLIP0_PROTOCOL_SLIP_ASK = [
    {"role": "client", "reply": {
        "action": "request", "message": "Check reachability", "final": None}},
    {"role": "server", "reply": {
        "action": "ask",    # slip: not allowed in NLIP-0
        "message": "What phone?",
        "plan": {
            "method": "POST",
            "path": "/device-reachability-status/v1/retrieve",
            "body": {"device": {"phoneNumber": "+9901000001"}},
        },
        "asked_fields": ["device.phoneNumber"]}},
    # harness treats as execute (plan is present) → report
    {"role": "server", "reply": {
        "action": "report", "message": "Done.", "plan": None, "asked_fields": None}},
    {"role": "client", "reply": {
        "action": "final", "message": "",
        "final": {"status": "done", "result": {"reachable": True}, "explanation": "ok"}}},
]
