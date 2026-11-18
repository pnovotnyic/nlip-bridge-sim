"""Session state machines for NLIP and NLIP-0 (stage 06).

`run_session(task, config)` plays one session end-to-end and returns a
`SessionOutcome` whose fields map directly to data contract §2.2.

NLIP state machine (interaction allowed):
  1. client request
  2. server: ask | restate | decline  (execute → treated as restate + slip logged)
  3. client: answer (back to 2+1i) | correct (back to 2+1i) | confirm (→ 4) | abort (→ declined)
  4. harness executes the plan
  5. server report (or, once, after the first execution: server restate after a backend rejection → back to 3+1i)
  6. client final
  Limits: ≤5 interactions, ≤30 model calls total, wall-time limit.

NLIP-0 state machine (no interaction):
  1. client request
  2. server execute | decline  (ask/restate → slip; take plan or decline)
  3. harness executes; on rejection the server may retry once (n_server_retries += 1; a restate is a slip)
  4. server report (or the server's report of the rejection, if it does not retry)
  5. client final
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import uvicorn

from nlipeval.agents.client import ClientAgent, ClientTurn
from nlipeval.agents.repair import turn_with_action_check
from nlipeval.agents.server import ServerAgent, ServerTurn, make_server_app
from nlipeval.nlip.message import Message
from nlipeval.nlip.transport import NLIPClient
from nlipeval.nlip.validate import validate

START_MESSAGE = "Begin the session."
MAX_INTERACTIONS = 5
MAX_MODEL_CALLS = 30

# B6: the actions allowed in each state. A disallowed action is repaired once; `tolerated` actions are
# not repaired, the state machine handles them as protocol slips.
CLIENT_FIRST = ("request",)
CLIENT_AFTER_ASK = ("answer", "abort")
CLIENT_AFTER_RESTATE = ("confirm", "correct", "abort")
CLIENT_FINAL = ("final",)
NLIP_SERVER_PLAN = ("ask", "restate", "decline")
NLIP_SERVER_PLAN_TOLERATED = ("execute",)
NLIP0_SERVER_PLAN = ("execute", "decline")
NLIP0_SERVER_PLAN_TOLERATED = ("ask", "restate")
ABORT_NOTICE = "The session has ended because you aborted it. Reply with action \"final\" and your final result."


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


# --------------------------------------------------------------------------- outcome

@dataclass
class ExecutedCall:
    method: str
    path: str
    body: Any
    status: int
    response_body: Any
    ts: str


@dataclass
class PlanRecord:
    turn: int
    action: str                   # restate | execute | restate_after_rejection
    plan: dict | None
    asked_fields: list[str] | None
    client_reply: str | None = None   # confirm | correct | abort | answer | None (no client reply)


@dataclass
class SessionOutcome:
    session_id: str
    termination: str              # final | declined | max_interactions | timeout | error_model | error_harness
    n_interactions: int = 0
    n_questions: int = 0
    n_corrections: int = 0
    n_restatements: int = 0
    n_server_retries: int = 0
    n_protocol_slips: int = 0
    n_action_repairs_client: int = 0
    n_action_repairs_server: int = 0
    plans: list[PlanRecord] = field(default_factory=list)
    executed_calls: list[ExecutedCall] = field(default_factory=list)
    client_final: dict | None = None
    calls_client: int = 0
    calls_server: int = 0
    errors: list[str] = field(default_factory=list)
    started_utc: str = ""
    ended_utc: str = ""
    wall_seconds: float = 0.0
    # token totals accumulated from model Results
    tokens: dict = field(default_factory=lambda: {
        "client_in": None, "client_out": None,
        "server_in": None, "server_out": None, "reasoning": None})
    cost_usd: float | None = None
    wire_log: list[dict] = field(default_factory=list)   # kept for wire.jsonl


# --------------------------------------------------------------------------- wire logging

def _wire_record(
    session_id: str,
    seq: int,
    direction: str,
    body: Any,
    http_status: int | None = None,
    headers: dict | None = None,
) -> dict:
    ok, violations = validate(body) if body else (False, [])
    return {
        "schema_version": "1",
        "session_id": session_id,
        "seq": seq,
        "direction": direction,
        "http_method": "POST",
        "path": "/nlip",
        "http_status": http_status,
        "headers": {k: v for k, v in (headers or {}).items() if k.lower() != "authorization"},
        "message": body,
        "valid_ecma430": ok,
        "ts": _utc_now(),
    }


# --------------------------------------------------------------------------- token accumulation

def _add_tokens(totals: dict, usage: dict | None, role: str) -> None:
    if not usage:
        return
    if role == "client":
        for k, field in (("client_in", "prompt_tokens"), ("client_out", "completion_tokens")):
            v = usage.get(field)
            if v is not None:
                totals[k] = (totals[k] or 0) + v
        r = usage.get("reasoning_tokens")
        if r is not None:
            totals["reasoning"] = (totals["reasoning"] or 0) + r
    else:
        for k, field in (("server_in", "prompt_tokens"), ("server_out", "completion_tokens")):
            v = usage.get(field)
            if v is not None:
                totals[k] = (totals[k] or 0) + v
        r = usage.get("reasoning_tokens")
        if r is not None:
            totals["reasoning"] = (totals["reasoning"] or 0) + r


# --------------------------------------------------------------------------- backend call

def _call_backend(
    plan: dict,
    backend_urls: dict[str, str],
    api: str,
    session_id: str,
) -> ExecutedCall:
    """POST the plan to the appropriate mock backend and return the result."""
    url_base = backend_urls[api]
    method = plan.get("method", "POST").upper()
    path = plan.get("path", "/")
    body = plan.get("body")
    url = url_base.rstrip("/") + path
    headers = {
        "X-Eval-Session": session_id,
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=30.0) as hc:
            resp = hc.request(method, url, json=body, headers=headers)
        try:
            resp_body = resp.json()
        except Exception:
            resp_body = resp.text
        return ExecutedCall(
            method=method, path=path, body=body,
            status=resp.status_code, response_body=resp_body,
            ts=_utc_now(),
        )
    except Exception as e:
        raise RuntimeError(f"Backend call failed: {e}") from e


# --------------------------------------------------------------------------- inline server (for the NLIP wire)

class _InlineServer:
    """Runs the server agent's FastAPI app in a background thread on a free port."""

    def __init__(self, agent: ServerAgent) -> None:
        self._turns: dict[str, tuple[ServerTurn | None, Any]] = {}
        self._last_conv_id: str | None = None

        def on_turn(turn, result, conv_id):
            self._turns[conv_id] = (turn, result)
            self._last_conv_id = conv_id

        self._app = make_server_app(agent, on_turn=on_turn)
        self._port = self._find_port()
        self.url = f"http://127.0.0.1:{self._port}"
        cfg = uvicorn.Config(self._app, host="127.0.0.1", port=self._port,
                             log_level="error", loop="asyncio")
        self._server = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        # wait until the server is accepting connections
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                httpx.get(self.url + "/docs", timeout=0.3)
                break
            except Exception:
                time.sleep(0.05)

    def last_turn(self, conv_id: str | None = None) -> tuple[ServerTurn | None, Any] | None:
        key = conv_id or self._last_conv_id
        return self._turns.get(key) if key else None

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)

    @staticmethod
    def _find_port() -> int:
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _note_missing_final(out: "SessionOutcome", turn) -> None:
    """The client's last turn carried no `final` object (e.g. action 'confirm'). The session ends, the
    executed calls stay scoreable, the answer scores as missing, and the slip is counted."""
    out.n_protocol_slips += 1
    out.errors.append(f"protocol_slip: client's last turn had action {turn.action!r} and no final answer")


# --------------------------------------------------------------------------- run_session

@dataclass
class SessionConfig:
    rung: str
    prompt: str                   # P1 | P2 | P3
    condition: str                # NLIP | NLIP-0
    attempt: int
    run_id: str
    client_agent: ClientAgent
    server_agent: ServerAgent
    backend_urls: dict[str, str]  # api → "http://host:port"
    wall_time_limit_s: float = 600.0
    session_id: str | None = None      # shared with the agents so calls.jsonl and sessions.jsonl join on it
    nlip_http_timeout_s: float = 60.0   # must exceed one model call's worst case + 30 s (adapter.max_call_seconds)
    price_per_million: dict | None = None   # {input, output} for R5


def run_session(task: dict, cfg: SessionConfig) -> SessionOutcome:
    """Play one session and return the outcome."""
    session_id = cfg.session_id or str(uuid.uuid4())
    t_start = time.monotonic()
    started = _utc_now()
    out = SessionOutcome(session_id=session_id, termination="error_harness", started_utc=started)

    api = task["api"]
    condition = cfg.condition

    # start the inline NLIP server
    try:
        srv = _InlineServer(cfg.server_agent)
    except Exception as e:
        out.errors.append(f"error_harness: could not start server: {e}")
        out.ended_utc = _utc_now()
        out.wall_seconds = time.monotonic() - t_start
        return out

    nlip_client = NLIPClient(srv.url, timeout=cfg.nlip_http_timeout_s)
    try:
        if condition == "NLIP":
            _run_nlip(task, cfg, session_id, out, nlip_client, srv, t_start)
        else:
            _run_nlip0(task, cfg, session_id, out, nlip_client, srv, t_start)
    except _ModelError as e:
        out.termination = "error_model"
        out.errors.append(str(e))
    except _TimeoutError:
        out.termination = "timeout"
    except _HarnessError as e:
        out.termination = "error_harness"
        out.errors.append(str(e))
    except Exception as e:
        out.termination = "error_harness"
        out.errors.append(f"unexpected: {e}")
    finally:
        srv.stop()
        out.calls_client = cfg.client_agent.call_count
        out.calls_server = cfg.server_agent.call_count
        out.n_action_repairs_client = cfg.client_agent.n_action_repairs
        out.n_action_repairs_server = cfg.server_agent.n_action_repairs
        out.ended_utc = _utc_now()
        out.wall_seconds = time.monotonic() - t_start
        # Convert nlip_client.wire to data contract format (body → message)
        out.wire_log = [
            {
                "schema_version": "1",
                "session_id": session_id,
                "seq": i + 1,
                "direction": ("client_to_server" if e["direction"] == "request"
                              else "server_to_client"),
                "http_method": "POST",
                "path": "/nlip",
                "http_status": None,
                "headers": {},
                "message": e["body"],
                "valid_ecma430": e["ok"],
                "ts": _utc_now(),
            }
            for i, e in enumerate(nlip_client.wire)
        ]

    return out


# --------------------------------------------------------------------------- private error types

class _ModelError(Exception):
    pass


class _TimeoutError(Exception):
    pass


class _HarnessError(Exception):
    pass


def _fail(res: Any, what: str) -> None:
    """Raise the right session error for a failed model call.

    error_model: the reply did not parse, or used a disallowed action, after repair, or the model refused (or gave no turn).
    error_harness: infrastructure failures (429, 5xx, connection errors, per-call timeouts, bad credentials).
    """
    et = getattr(res, "error_type", None) if res is not None else None
    err = getattr(res, "error", None) if res is not None else None
    if et not in (None, "parse_failure", "refusal", "action_failure"):
        raise _HarnessError(f"{what}: {err}")
    raise _ModelError(f"{what}: {err}")


# --------------------------------------------------------------------------- shared helpers

def _check_limits(
    out: SessionOutcome,
    t_start: float,
    wall_limit: float,
    total_calls: int,
) -> None:
    if time.monotonic() - t_start > wall_limit:
        raise _TimeoutError
    if out.n_interactions >= MAX_INTERACTIONS:
        out.termination = "max_interactions"
        raise StopIteration
    if total_calls >= MAX_MODEL_CALLS:
        out.termination = "max_interactions"
        raise StopIteration


def _nlip_send(
    nlip_client: NLIPClient,
    text: str,
) -> str:
    """Send a client text message and return the server's reply text.

    Wire messages are captured automatically in `nlip_client.wire`.
    """
    msg = Message.text(text)
    resp = nlip_client.send(msg)
    texts = resp.texts("english") or resp.texts(None)
    return " ".join(texts).strip() if texts else (resp.content or "")


def _client_turn(cfg: SessionConfig, history: list[dict], purpose: str, allowed: tuple[str, ...]):
    """One client turn, with one repair if the action is not allowed in this state (B6)."""
    return turn_with_action_check(cfg.client_agent, history, purpose, allowed)


def _client_final(cfg: SessionConfig, out: SessionOutcome, history: list[dict]) -> None:
    """Ask the client for its `final` and record it (B6, B7)."""
    turn, res = _client_turn(cfg, history, "final", CLIENT_FINAL)
    _add_tokens(out.tokens, res.usage, "client")
    if turn is None or res.error:
        _fail(res, "client error on final")
    if turn.final:
        out.client_final = turn.final
    else:
        _note_missing_final(out, turn)


def _client_aborted(cfg: SessionConfig, out: SessionOutcome, history: list[dict], abort_turn) -> None:
    """The client aborted: it still gives its `final` (B7). The termination stays `declined`."""
    history.append({"role": "assistant", "content": json.dumps(abort_turn.raw)})
    history.append({"role": "user", "content": ABORT_NOTICE})
    _client_final(cfg, out, history)
    out.termination = "declined"


# --------------------------------------------------------------------------- NLIP state machine

def _run_nlip(
    task: dict,
    cfg: SessionConfig,
    session_id: str,
    out: SessionOutcome,
    nlip_client: NLIPClient,
    srv: _InlineServer,
    t_start: float,
) -> None:
    api = task["api"]
    client_history: list[dict] = [{"role": "user", "content": START_MESSAGE}]
    total_calls = 0
    cfg.server_agent.plan_allowed = NLIP_SERVER_PLAN
    cfg.server_agent.plan_tolerated = NLIP_SERVER_PLAN_TOLERATED

    # --- step 1: client request ---
    _check_limits_simple(t_start, cfg.wall_time_limit_s)
    client_turn, cr = _client_turn(cfg, client_history, "compose", CLIENT_FIRST)
    total_calls += 1
    _add_tokens(out.tokens, cr.usage, "client")
    if client_turn is None or cr.error:
        _fail(cr, "client error on request")

    # send client's request text to server via NLIP
    server_reply_text = _nlip_send(nlip_client, client_turn.message)
    client_history.append({"role": "assistant", "content": json.dumps(client_turn.raw)})

    # capture the structured server turn the inline server produced
    server_structured = srv.last_turn()
    if server_structured is None:
        raise _HarnessError("Server produced no structured turn after client request")
    server_turn, sr = server_structured
    total_calls += 1
    _add_tokens(out.tokens, sr.usage if sr else None, "server")
    if server_turn is None or (sr and sr.error):
        _fail(sr, "server error on first reply")

    # start the client's conversation turn history (the client sees server messages as user turns)
    # The client history already has request; we add server reply
    client_history.append({"role": "user", "content": server_reply_text})

    # first_restate_confirmed tracks whether the first restate+confirm pair has happened (0 interactions)
    first_plan_done = False

    while True:
        _check_limits_simple(t_start, cfg.wall_time_limit_s)

        # --- protocol-slip: server sent execute before confirmation ---
        # Every server turn seen here answers a client message (or reports a rejection), so an `execute`
        # always comes before a confirmation, also after a correction that follows a rejection (08a H6).
        effective_action = server_turn.action
        if effective_action == "execute":
            out.errors.append(f"protocol_slip: server sent execute before client confirmation (turn {total_calls})")
            out.n_protocol_slips += 1
            effective_action = "restate"

        if effective_action == "decline":
            # server declined; client should still produce a final
            out.plans.append(PlanRecord(turn=total_calls, action="decline", plan=None, asked_fields=None))
            # give client the reply to produce final
            _client_final(cfg, out, client_history)
            out.termination = "declined"
            return

        if effective_action == "ask":
            ask_rec = PlanRecord(turn=total_calls, action="ask",
                                 plan=None, asked_fields=server_turn.asked_fields)
            out.plans.append(ask_rec)
            out.n_questions += 1
            out.n_interactions += 1   # every ask/answer pair is +1 interaction
            # check interaction limit
            if out.n_interactions >= MAX_INTERACTIONS:
                out.termination = "max_interactions"
                return
            # client answers
            client_turn2, cr2 = _client_turn(cfg, client_history, "compose", CLIENT_AFTER_ASK)
            total_calls += 1
            _add_tokens(out.tokens, cr2.usage, "client")
            if client_turn2 is None or cr2.error:
                _fail(cr2, "client error on answer")
            ask_rec.client_reply = client_turn2.action
            if client_turn2.action == "abort":
                _client_aborted(cfg, out, client_history, client_turn2)
                return
            # send client answer to server
            server_reply_text = _nlip_send(nlip_client, client_turn2.message)
            client_history.append({"role": "assistant", "content": json.dumps(client_turn2.raw)})
            # update server turn
            server_structured = srv.last_turn()
            if server_structured is None:
                raise _HarnessError("Server produced no structured turn after client answer")
            server_turn, sr = server_structured
            total_calls += 1
            _add_tokens(out.tokens, sr.usage if sr else None, "server")
            if server_turn is None or (sr and sr.error):
                _fail(sr, "server error after answer")
            client_history.append({"role": "user", "content": server_reply_text})
            if total_calls >= MAX_MODEL_CALLS:
                out.termination = "max_interactions"
                return
            continue

        if effective_action == "restate":
            out.n_restatements += 1
            if first_plan_done:
                out.n_interactions += 1   # second and later restates are +1 interaction
            if out.n_interactions >= MAX_INTERACTIONS:
                out.termination = "max_interactions"
                return
            plan_rec = PlanRecord(turn=total_calls, action="restate",
                                  plan=server_turn.plan, asked_fields=None)
            out.plans.append(plan_rec)
            # client replies with confirm or correct
            client_turn2, cr2 = _client_turn(cfg, client_history, "compose", CLIENT_AFTER_RESTATE)
            total_calls += 1
            _add_tokens(out.tokens, cr2.usage, "client")
            if client_turn2 is None or cr2.error:
                _fail(cr2, "client error on restate reply")
            plan_rec.client_reply = client_turn2.action
            if client_turn2.action == "abort":
                _client_aborted(cfg, out, client_history, client_turn2)
                return
            if client_turn2.action == "correct":
                out.n_corrections += 1
                out.n_interactions += 1   # every correction is +1 interaction
                if out.n_interactions >= MAX_INTERACTIONS:
                    out.termination = "max_interactions"
                    return
                # send correction to server
                server_reply_text = _nlip_send(nlip_client, client_turn2.message)
                client_history.append({"role": "assistant", "content": json.dumps(client_turn2.raw)})
                server_structured = srv.last_turn()
                if server_structured is None:
                    raise _HarnessError("Server produced no structured turn after correction")
                server_turn, sr = server_structured
                total_calls += 1
                _add_tokens(out.tokens, sr.usage if sr else None, "server")
                if server_turn is None or (sr and sr.error):
                    _fail(sr, "server error after correction")
                client_history.append({"role": "user", "content": server_reply_text})
                if total_calls >= MAX_MODEL_CALLS:
                    out.termination = "max_interactions"
                    return
                continue

            # client confirmed the plan; its confirm stays in its own history (08a H5)
            client_history.append({"role": "assistant", "content": json.dumps(client_turn2.raw)})
            first_plan_done = True

            # --- step 4: execute ---
            plan = server_turn.plan
            if not plan:
                raise _HarnessError("Server restate has no plan")
            try:
                ec = _call_backend(plan, cfg.backend_urls, api, session_id)
            except Exception as e:
                raise _HarnessError(f"backend call failed: {e}") from e
            out.executed_calls.append(ec)

            # --- step 5: server report ---
            # Give server the backend outcome directly (not via NLIP wire). After the first execution a
            # rejected call may be restated once; after a later execution only a report is allowed.
            first_execution = len(out.executed_calls) == 1
            allowed = ("report", "restate") if ec.status >= 400 and first_execution else ("report",)
            server_turn, sr = _tell_server_backend(cfg.server_agent, ec, t_start, cfg.wall_time_limit_s,
                                                   allowed)
            total_calls += 1
            _add_tokens(out.tokens, sr.usage if sr else None, "server")
            if server_turn is None or (sr and sr.error):
                _fail(sr, "server error on report")

            # the server restates after a backend rejection: back to the client, through the restate
            # branch above, so that a confirm, a correction or an abort is handled as for any restatement
            # (08a H6: a correction here used to be ignored and the old plan executed)
            if server_turn.action == "restate":
                client_history.append({"role": "user", "content": server_turn.message})
                continue

            # server should now be reporting
            # relay the report text to the client
            server_report_text = server_turn.message
            client_history.append({"role": "user", "content": server_report_text})

            # --- step 6: client final ---
            _client_final(cfg, out, client_history)
            out.termination = "final"
            return

        # server returned an unexpected action — treat as error
        raise _ModelError(f"server returned unexpected action {server_turn.action!r}")


def _tell_server_backend(
    agent: ServerAgent,
    ec: ExecutedCall,
    t_start: float,
    wall_limit: float,
    allowed: tuple[str, ...] | None = None,
    tolerated: tuple[str, ...] = (),
) -> tuple["ServerTurn | None", Any]:
    """Tell the server agent the backend execution result directly (not via NLIP wire).

    Returns (server_turn, result) from the direct model call.
    This call is not sent over the NLIP wire.
    """
    _check_limits_simple(t_start, wall_limit)
    backend_msg = (
        f"The backend returned HTTP {ec.status}. "
        f"Response body: {json.dumps(ec.response_body)}"
    )
    # The harness injects the backend outcome as the next user turn, after the conversation so far.
    history = getattr(agent, "history", None)
    if history is None:
        history = []
    history.append({"role": "user", "content": backend_msg})
    turn, res = turn_with_action_check(agent, list(history), "report", allowed, tolerated)
    if turn is not None:
        history.append({"role": "assistant", "content": json.dumps(turn.raw)})
    return turn, res


def _check_limits_simple(t_start: float, wall_limit: float) -> None:
    if time.monotonic() - t_start > wall_limit:
        raise _TimeoutError


# --------------------------------------------------------------------------- NLIP-0 state machine

def _run_nlip0(
    task: dict,
    cfg: SessionConfig,
    session_id: str,
    out: SessionOutcome,
    nlip_client: NLIPClient,
    srv: _InlineServer,
    t_start: float,
) -> None:
    api = task["api"]
    client_history: list[dict] = [{"role": "user", "content": START_MESSAGE}]
    cfg.server_agent.plan_allowed = NLIP0_SERVER_PLAN
    cfg.server_agent.plan_tolerated = NLIP0_SERVER_PLAN_TOLERATED

    # --- step 1: client request ---
    _check_limits_simple(t_start, cfg.wall_time_limit_s)
    client_turn, cr = _client_turn(cfg, client_history, "compose", CLIENT_FIRST)
    _add_tokens(out.tokens, cr.usage, "client")
    if client_turn is None or cr.error:
        _fail(cr, "client error on request")

    # send to server via NLIP
    server_reply_text = _nlip_send(nlip_client, client_turn.message)
    client_history.append({"role": "assistant", "content": json.dumps(client_turn.raw)})

    # capture the structured server turn
    server_structured = srv.last_turn()
    if server_structured is None:
        raise _HarnessError("Server produced no structured turn after client request")
    server_turn, sr = server_structured
    _add_tokens(out.tokens, sr.usage if sr else None, "server")
    if server_turn is None or (sr and sr.error):
        _fail(sr, "server error on first reply")

    # check protocol slips
    effective_action = server_turn.action
    if effective_action in ("ask", "restate"):
        out.errors.append(f"protocol_slip: server sent {effective_action!r} in NLIP-0 (turn 1)")
        out.n_protocol_slips += 1
        # take plan if present, otherwise decline
        if server_turn.plan:
            effective_action = "execute"
        else:
            effective_action = "decline"

    if effective_action == "decline":
        out.plans.append(PlanRecord(turn=1, action="decline", plan=None, asked_fields=None))
        client_history.append({"role": "user", "content": server_reply_text})
        _client_final(cfg, out, client_history)
        out.termination = "declined"
        return

    # --- step 3: execute ---
    out.plans.append(PlanRecord(turn=1, action="execute", plan=server_turn.plan, asked_fields=None))
    plan = server_turn.plan
    if not plan:
        raise _HarnessError("Server execute has no plan")
    try:
        ec = _call_backend(plan, cfg.backend_urls, api, session_id)
    except Exception as e:
        raise _HarnessError(f"backend call failed: {e}") from e
    out.executed_calls.append(ec)

    # server retry on backend rejection (once, without client)
    server_turn_report = sr_report = None
    if ec.status >= 400:
        server_turn2, sr2 = _tell_server_backend(cfg.server_agent, ec, t_start, cfg.wall_time_limit_s,
                                                 ("report", "execute"), ("restate",))
        _add_tokens(out.tokens, sr2.usage if sr2 else None, "server")
        if server_turn2 is None or (sr2 and sr2.error):
            _fail(sr2, "server error after backend rejection")
        if server_turn2.action == "report":
            # 08a H4: the server reported the rejection at once; that is its report
            server_turn_report, sr_report = server_turn2, sr2
        elif server_turn2.plan:
            if server_turn2.action == "restate":
                # 08a H4: a restatement is a protocol slip in NLIP-0, as on the first turn; its plan is retried
                out.errors.append("protocol_slip: server sent 'restate' in NLIP-0 (retry)")
                out.n_protocol_slips += 1
            out.n_server_retries += 1
            try:
                ec2 = _call_backend(server_turn2.plan, cfg.backend_urls, api, session_id)
            except Exception as e:
                raise _HarnessError(f"server retry backend call failed: {e}") from e
            out.executed_calls.append(ec2)
            ec = ec2  # use the retried result for the report

    # --- step 4: server report ---
    if server_turn_report is None:
        server_turn_report, sr_report = _tell_server_backend(cfg.server_agent, ec, t_start,
                                                             cfg.wall_time_limit_s, ("report",))
        _add_tokens(out.tokens, sr_report.usage if sr_report else None, "server")
        if server_turn_report is None or (sr_report and sr_report.error):
            # 08a H3: no parse or no allowed action after repair is a model failure, as under NLIP
            _fail(sr_report, "server error on report")

    report_text = server_turn_report.message
    client_history.append({"role": "user", "content": report_text})

    # --- step 5: client final ---
    _client_final(cfg, out, client_history)
    out.termination = "final"
