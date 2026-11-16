"""Shared machinery of the three mock backends (stage 04).

One FastAPI application per API. A single catch-all route does the same steps for every request:

1. read the headers `X-Eval-Session` and `X-Eval-Clock`;
2. validate the request against the pinned specification (openapi-core);
3. on a validation error, answer with the error format and codes *that specification* defines;
4. otherwise call the API's handler, which answers from the world;
5. validate the response against the specification (a failure is a bug and is answered with 500 BACKEND_BUG);
6. append one line to `backend.jsonl` (data contract section 2.5).
"""
from __future__ import annotations

import json
import re
import threading
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from openapi_core import OpenAPI
from openapi_core.testing import MockRequest, MockResponse
from openapi_schema_validator import OAS30Validator

from nlipeval.backends.world import ROOT, World, fmt_ts, parse_ts

warnings.filterwarnings("ignore", message="Unsupported scheme type")

SPEC_DIR = ROOT / "specs"
SESSION_HEADER = "x-eval-session"
CLOCK_HEADER = "x-eval-clock"
DEFAULT_SESSION = "default"
ID_NAMESPACE = uuid.UUID("6f1c5a1e-04b0-4e0a-9d5e-3b6a0c0de004")


class Err(Exception):
    """An error answer in the specification's error format (status, code, message)."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message = status, code, message

    def body(self) -> dict:
        return {"status": self.status, "code": self.code, "message": self.message}


@dataclass
class Result:
    status: int
    body: Any = None            # None means an empty body (204)
    effect: dict | None = None  # recorded as `world_effect`


@dataclass
class QodSession:
    """A QoD session in per-eval-session state: from the world file, or created during the session."""
    id: str
    device_id: str
    application_server: dict
    qos_profile: str
    duration_s: int
    qos_status: str
    status_info: str | None = None
    device_ports: dict | None = None
    application_server_ports: dict | None = None
    sink: str | None = None
    device_echo: dict | None = None     # the single identifier returned in `device` (several given)
    started_at: datetime | None = None
    started_ago_s: int | None = None    # world sessions: relative to the clock of the request

    def started(self, clock: datetime) -> datetime:
        if self.started_at is not None:
            return self.started_at
        return clock - timedelta(seconds=self.started_ago_s or 0)


@dataclass
class SessionState:
    """State of one `X-Eval-Session`: nothing here is shared with other sessions."""
    counter: int = 0
    seq: int = 0
    created: dict[str, QodSession] = field(default_factory=dict)
    deleted: set[str] = field(default_factory=set)
    world_loaded: bool = False
    world_sessions: dict[str, QodSession] = field(default_factory=dict)


@dataclass
class Ctx:
    world: World
    state: SessionState
    session_id: str
    clock: datetime
    method: str
    path: str                    # relative to the API base path, e.g. /sessions/{id}
    params: dict[str, str]
    body: dict | list | None
    headers: dict[str, str]
    # validates `instance` against components/schemas/<name> of the pinned spec; raises Err(400)
    check_schema: Callable[[str, Any], None] = field(default=lambda name, instance: None)
    api: str = ""
    resolved_device: str | None = None
    identifiers_consistent: bool | None = None

    def new_id(self) -> str:
        """UUIDv5 of the eval-session ID and a counter: the same calls give the same IDs."""
        self.state.counter += 1
        return str(uuid.uuid5(ID_NAMESPACE, f"{self.session_id}:{self.state.counter}"))


Handler = Callable[[Ctx], Result]


@dataclass
class ApiDef:
    api: str                          # L1 | L2 | L3
    spec: str                         # file under specs/
    base_path: str                    # path prefix from the spec's servers entry
    routes: list[tuple[str, str, Handler]]   # (method, path template, handler)
    allows_out_of_range: bool         # the spec's 400 response lists OUT_OF_RANGE
    sink_error: bool = False          # L3: pattern violation on `sink` is INVALID_SINK


def _compile(template: str) -> re.Pattern:
    return re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", template) + "$")


class Backend:
    def __init__(self, api: ApiDef, world: World | None = None, run_dir: Path | None = None):
        self.api = api
        self.world = world or World()
        self.openapi = OpenAPI.from_file_path(str(SPEC_DIR / api.spec))
        self.spec_doc = yaml.safe_load((SPEC_DIR / api.spec).read_text())
        self.routes = [(m, t, _compile(t), h) for m, t, h in api.routes]
        self.run_dir = Path(run_dir) if run_dir else None
        self.states: dict[str, SessionState] = {}
        self._log_lock = threading.Lock()
        if self.run_dir:
            self.run_dir.mkdir(parents=True, exist_ok=True)

    # --- state -------------------------------------------------------------------------------
    def state(self, session_id: str) -> SessionState:
        st = self.states.get(session_id)
        if st is None:
            st = self.states[session_id] = SessionState()
        return st

    def reset(self, session_id: str | None) -> list[str]:
        if session_id is None:
            gone = sorted(self.states)
            self.states.clear()
        else:
            gone = [session_id] if self.states.pop(session_id, None) is not None else []
        return gone

    # --- logging -----------------------------------------------------------------------------
    def _log(self, record: dict) -> None:
        if not self.run_dir:
            return
        line = json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n"
        with self._log_lock, open(self.run_dir / "backend.jsonl", "a", encoding="utf-8") as f:
            f.write(line)

    # --- request handling --------------------------------------------------------------------
    def _match(self, method: str, rel_path: str):
        path_known = False
        for m, _t, rx, h in self.routes:
            mt = rx.match(rel_path)
            if mt:
                path_known = True
                if m == method:
                    return h, mt.groupdict(), True
        return None, {}, path_known

    def _err_from_schema_errors(self, schema_errors: list, fallback: list[str]) -> Err:
        """400 answer in the specification's format from jsonschema errors (or plain texts)."""
        texts: list[str] = []
        code = "INVALID_ARGUMENT"
        schema_errors = sorted(schema_errors, key=lambda s: ([str(p) for p in s.absolute_path], s.validator))
        for s in schema_errors:
            where = ".".join(str(p) for p in s.absolute_path) or "body"
            texts.append(f"{where}: {s.message}")
        if schema_errors:
            first = schema_errors[0]
            if self.api.allows_out_of_range and first.validator in ("minimum", "maximum"):
                code = "OUT_OF_RANGE"
            if self.api.sink_error and list(first.absolute_path) == ["sink"]:
                code = "INVALID_SINK"
        texts += fallback
        return Err(400, code, "; ".join(texts)[:300] or "Client specified an invalid argument.")

    def _map_request_errors(self, errors: list[Exception]) -> Err:
        """Turn openapi-core errors into the specification's 400 answer."""
        schema_errors, plain = [], []
        for e in errors:
            cause = e.__cause__
            found = list(getattr(cause, "schema_errors", None) or [])
            if found:
                schema_errors += found
            else:
                plain.append(str(cause or e).splitlines()[0])
        return self._err_from_schema_errors(schema_errors, plain)

    def check_schema(self, name: str, instance: Any) -> None:
        """openapi-core does not follow `discriminator` mappings (Area -> Circle, SinkCredential -> ...), so
        handlers validate those subschemas explicitly against the same pinned specification."""
        schema = {"components": self.spec_doc["components"], "$ref": f"#/components/schemas/{name}"}
        validator = OAS30Validator(schema, format_checker=OAS30Validator.FORMAT_CHECKER)
        errors = list(validator.iter_errors(instance))
        if errors:
            raise self._err_from_schema_errors(errors, [])

    def handle(self, method: str, url_path: str, host_url: str, headers: dict[str, str], raw: bytes) -> tuple[Result, dict]:
        """Returns (result, log fields). Never raises for client errors."""
        low = {k.lower(): v for k, v in headers.items()}
        session_id = low.get(SESSION_HEADER) or DEFAULT_SESSION
        state = self.state(session_id)
        state.seq += 1
        info: dict[str, Any] = {"session_id": session_id, "seq": state.seq, "api": self.api.api,
                                "method": method, "path": url_path, "request_body": None,
                                "validation_ok": True, "validation_errors": [], "response_valid": None,
                                "response_errors": [], "world_effect": None}
        if raw:
            try:
                info["request_body"] = json.loads(raw)
            except ValueError:
                info["request_body"] = raw.decode("utf-8", "replace")
        try:
            clock = parse_ts(low[CLOCK_HEADER]) if CLOCK_HEADER in low else self.world.clock_default
        except ValueError:
            return self._finish(info, Result(400, Err(400, "INVALID_ARGUMENT", "Bad X-Eval-Clock header").body()), None, clock=None)
        info["clock"] = fmt_ts(clock)

        if not url_path.startswith(self.api.base_path):
            return self._finish(info, Result(404, Err(404, "NOT_FOUND", "The specified resource is not found.").body()),
                                None, outside_spec=True, clock=clock)
        rel = url_path[len(self.api.base_path):] or "/"
        handler, params, path_known = self._match(method, rel)

        req = MockRequest(host_url, method, url_path, headers=headers, data=raw or None,
                          content_type=(low.get("content-type", "application/json").split(";")[0].strip()
                                        or "application/json"))
        errors = list(self.openapi.iter_request_errors(req))
        if handler is None:
            info["validation_ok"] = False
            info["validation_errors"] = [str(e).splitlines()[0] for e in errors]
            return self._finish(info, Result(404, Err(404, "NOT_FOUND", "The specified resource is not found.").body()),
                                None, outside_spec=True, clock=clock)
        if errors:
            info["validation_ok"] = False
            info["validation_errors"] = [str(e.__cause__ or e).splitlines()[0] for e in errors]
            err = self._map_request_errors(errors)
            return self._finish(info, Result(err.status, err.body()), req, clock=clock)

        body = json.loads(raw) if raw else None
        ctx = Ctx(self.world, state, session_id, clock, method, rel, params, body, low, self.check_schema, self.api.api)
        try:
            result = handler(ctx)
        except Err as err:
            result = Result(err.status, err.body())
        info["world_effect"] = result.effect
        info["resolved_device"] = ctx.resolved_device
        info["identifiers_consistent"] = ctx.identifiers_consistent
        return self._finish(info, result, req, clock=clock)

    def _finish(self, info: dict, result: Result, req: MockRequest | None, outside_spec: bool = False, clock=None):
        if req is not None and not outside_spec:
            data = b"" if result.body is None else json.dumps(result.body).encode()
            res = MockResponse(data, result.status)
            errs = [str(e.__cause__ or e).splitlines()[0] for e in self.openapi.iter_response_errors(req, res)]
            info["response_valid"] = not errs
            info["response_errors"] = errs
            if errs:   # a backend that sends invalid responses is a bug: make it loud
                result = Result(500, {"status": 500, "code": "BACKEND_BUG",
                                      "message": "response failed validation: " + errs[0][:200]}, result.effect)
        info["status"] = result.status
        info["response_body"] = result.body
        self._log({"schema_version": "1", **{k: info[k] for k in (
            "session_id", "seq", "api", "method", "path", "request_body", "validation_ok", "validation_errors",
            "status", "response_body", "world_effect")},
            "resolved_device": info.get("resolved_device"),
            "identifiers_consistent": info.get("identifiers_consistent"),
            "clock": info.get("clock"), "response_valid": info["response_valid"],
            "response_errors": info["response_errors"],
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")})
        return result, info

    # --- application -------------------------------------------------------------------------
    def build_app(self) -> FastAPI:
        app = FastAPI(title=f"mock backend {self.api.api}", docs_url=None, redoc_url=None, openapi_url=None)
        backend = self

        @app.get("/__admin/health")
        async def health():
            return {"api": backend.api.api, "spec": backend.api.spec, "world_hash": backend.world.hash,
                    "sessions": sorted(backend.states)}

        @app.post("/__admin/reset")
        async def reset(session: str | None = None):
            return {"reset": backend.reset(session)}

        @app.get("/__admin/state")
        async def admin_state(session: str = DEFAULT_SESSION):
            st = backend.states.get(session)
            if st is None:
                return {"session": session, "exists": False}
            clock = backend.world.clock_default
            return {"session": session, "exists": True, "requests": st.seq, "counter": st.counter,
                    "deleted": sorted(st.deleted),
                    "created": [{"sessionId": s.id, "device": s.device_id, "applicationServer": s.application_server,
                                 "qosProfile": s.qos_profile, "duration": s.duration_s, "qosStatus": s.qos_status,
                                 "startedAt": fmt_ts(s.started(clock))}
                                for s in sorted(st.created.values(), key=lambda s: s.id)]}

        @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
        async def dispatch(full_path: str, request: Request):
            raw = await request.body()
            host_url = f"{request.url.scheme}://{request.url.netloc}"
            result, _ = backend.handle(request.method, request.url.path, host_url, dict(request.headers), raw)
            hdrs = {}
            corr = request.headers.get("x-correlator")
            if corr:
                hdrs["x-correlator"] = corr
            if result.body is None:
                return Response(status_code=result.status, headers=hdrs)
            return JSONResponse(result.body, status_code=result.status, headers=hdrs)

        return app
