"""L3 mock backend: Quality-on-Demand v1.1.0 (specs/L3/v1.1.0.yaml).

Implemented: POST /sessions (createSession), GET /sessions/{sessionId} (getSession),
DELETE /sessions/{sessionId} (deleteSession). The other two operations of the specification
(/sessions/{id}/extend and /retrieve-sessions) are not used by any task and answer 404 NOT_FOUND.
The QoS Profiles API is not implemented: the server agent learns the profiles from the profile table
built from config/world/qos_profiles.yaml (nlipeval/backends/profile_table.py).

createSession, in this order (first failure wins; every code is in the specification's responses):
 1. schema validation of the request (400 INVALID_ARGUMENT / OUT_OF_RANGE; `sink` pattern: 400 INVALID_SINK);
 2. `sinkCredential` (400 INVALID_CREDENTIAL when its type is not ACCESSTOKEN; INVALID_TOKEN when the token
    type is not bearer; INVALID_ARGUMENT for other schema violations);
 3. `applicationServer` addresses must be valid IPv4/IPv6 addresses or networks (400 INVALID_ARGUMENT);
 4. device (422 MISSING_IDENTIFIER, 422 UNSUPPORTED_IDENTIFIER, 404 IDENTIFIER_NOT_FOUND);
 5. profile: unknown name -> 404 NOT_FOUND (the specification has no dedicated code; the QoS Profiles API
    uses NOT_FOUND for an unknown profile); status not ACTIVE -> 422 QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE
    (text of the specification: "exists but is currently not available ... INACTIVE or DEPRECATED");
 6. duration outside the profile's [min, max] -> 400 QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE;
 7. an existing, not deleted session of the same device for the same flow (application server and ports)
    -> 409 CONFLICT ("Conflict with an existing session for the same device").
Then the session is created with qosStatus AVAILABLE, startedAt = clock, expiresAt = clock + duration,
the granted duration equal to the requested one. `sink` is only validated, never called. `sinkCredential`
is never echoed back. `device` is returned only when several identifiers were given (one of them).
"""
from __future__ import annotations

import copy
import ipaddress
from datetime import timedelta
from pathlib import Path

from nlipeval.backends.core import ApiDef, Backend, Ctx, Err, QodSession, Result
from nlipeval.backends.identify import resolve_device
from nlipeval.backends.world import World, fmt_ts

CREDENTIAL_SCHEMAS = {"ACCESSTOKEN": "AccessTokenCredential"}


def _check_application_server(asv: dict) -> None:
    for fam, parse in (("ipv4Address", ipaddress.IPv4Network), ("ipv6Address", ipaddress.IPv6Network)):
        if fam in asv:
            try:
                parse(asv[fam], strict=False)
            except ValueError as exc:
                raise Err(400, "INVALID_ARGUMENT", f"applicationServer.{fam}: {exc}") from None


def _check_credential(ctx: Ctx, cred: dict) -> None:
    ctype = cred.get("credentialType")
    if ctype != "ACCESSTOKEN":
        raise Err(400, "INVALID_CREDENTIAL", "Only Access token is supported")
    probe = copy.deepcopy(cred)
    tt = probe.get("accessTokenType")
    if isinstance(tt, str):
        if tt.lower() != "bearer":
            raise Err(400, "INVALID_TOKEN", "Only bearer token is supported")
        probe["accessTokenType"] = "bearer"   # the schema enum is lowercase, its description says `Bearer`
    ctx.check_schema(CREDENTIAL_SCHEMAS[ctype], probe)


def _flow(asv: dict, dp, asp) -> tuple:
    return (repr(sorted(asv.items())), repr(dp), repr(asp))


def _visible_sessions(ctx: Ctx) -> dict[str, QodSession]:
    """World sessions that were not deleted in this eval session, plus the ones created in it."""
    st = ctx.state
    out: dict[str, QodSession] = {}
    for ws in ctx.world.sessions.values():
        if ws.id in st.deleted:
            continue
        out[ws.id] = QodSession(ws.id, ws.device_id, ws.application_server, ws.qos_profile, ws.duration_s,
                                ws.qos_status, ws.status_info, ws.device_ports, ws.application_server_ports,
                                ws.sink, started_ago_s=ws.started_ago_s)
    out.update(st.created)
    return out


def _info(ctx: Ctx, s: QodSession) -> dict:
    started = s.started(ctx.clock)
    info: dict = {}
    if s.device_echo:
        info["device"] = s.device_echo
    info["applicationServer"] = s.application_server
    if s.device_ports:
        info["devicePorts"] = s.device_ports
    if s.application_server_ports:
        info["applicationServerPorts"] = s.application_server_ports
    info["qosProfile"] = s.qos_profile
    if s.sink:
        info["sink"] = s.sink
    info.update({"sessionId": s.id, "duration": s.duration_s,
                 "startedAt": fmt_ts(started), "expiresAt": fmt_ts(started + timedelta(seconds=s.duration_s)),
                 "qosStatus": s.qos_status})
    if s.status_info:
        info["statusInfo"] = s.status_info
    return info


def create_session(ctx: Ctx) -> Result:
    body = ctx.body
    if "sinkCredential" in body:
        _check_credential(ctx, body["sinkCredential"])
    _check_application_server(body["applicationServer"])
    dev, echo = resolve_device(ctx)

    prof = ctx.world.profiles.get(body["qosProfile"])
    if prof is None:
        raise Err(404, "NOT_FOUND", "The specified resource is not found.")
    if prof.status != "ACTIVE":
        raise Err(422, "QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE",
                  "The requested QoS Profile is currently not available for session creation.")
    dur = body["duration"]
    if not prof.min_duration_s <= dur <= prof.max_duration_s:
        raise Err(400, "QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE",
                  "The requested duration is out of the allowed range for the specific QoS profile")

    flow = _flow(body["applicationServer"], body.get("devicePorts"), body.get("applicationServerPorts"))
    for other in _visible_sessions(ctx).values():
        if other.device_id == dev.id and _flow(other.application_server, other.device_ports,
                                               other.application_server_ports) == flow:
            raise Err(409, "CONFLICT", "Conflict with an existing session for the same device.")

    s = QodSession(ctx.new_id(), dev.id, body["applicationServer"], prof.name, dur, "AVAILABLE",
                   device_ports=body.get("devicePorts"), application_server_ports=body.get("applicationServerPorts"),
                   sink=body.get("sink"), device_echo=echo, started_at=ctx.clock)
    ctx.state.created[s.id] = s
    return Result(201, _info(ctx, s), {"op": "create", "session": s.id, "device": dev.id, "profile": prof.name})


def get_session(ctx: Ctx) -> Result:
    s = _visible_sessions(ctx).get(ctx.params["sessionId"])
    if s is None:
        raise Err(404, "NOT_FOUND", "The specified resource is not found.")
    return Result(200, _info(ctx, s), {"op": "get", "session": s.id})


def delete_session(ctx: Ctx) -> Result:
    sid = ctx.params["sessionId"]
    if sid not in _visible_sessions(ctx):
        raise Err(404, "NOT_FOUND", "The specified resource is not found.")
    ctx.state.created.pop(sid, None)
    ctx.state.deleted.add(sid)
    return Result(204, None, {"op": "delete", "session": sid})


API = ApiDef(api="L3", spec="L3/v1.1.0.yaml", base_path="/quality-on-demand/v1",
             routes=[("POST", "/sessions", create_session),
                     ("GET", "/sessions/{sessionId}", get_session),
                     ("DELETE", "/sessions/{sessionId}", delete_session)],
             allows_out_of_range=True, sink_error=True)


def make_backend(world: World | None = None, run_dir: Path | None = None) -> Backend:
    return Backend(API, world, run_dir)
