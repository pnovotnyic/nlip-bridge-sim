"""Renderers for L3 (Quality-on-Demand).

render_request(intent, version)        -> {method, path, body}: the client's native request
render_gold_calls(intent, version)     -> [{method, path, body}, ...]: acceptable calls at the server version
render_answer(world_outcome, version)  -> {status, result}

Request fields per client version (each checked against its own version's specification, 07b A4):
  v0.8.1:            duration, ueId{msisdn|externalId|ipv4addr|ipv6addr}, asId{ipv4addr|ipv6addr}, uePorts, asPorts,
                     qos, notificationUrl
  v0.9.0, v0.10.0:   duration, device, applicationServer, devicePorts, applicationServerPorts, qosProfile,
                     webhook{notificationUrl}
  v0.11.0 .. v1.1.0: duration, device, applicationServer, devicePorts, applicationServerPorts, qosProfile, sink
Response fields per version:
  v0.8.1:            id, startedAt/expiresAt (Unix seconds), duration, ueId, asId, uePorts, asPorts, qos
  v0.9.0, v0.10.0:   sessionId, startedAt/expiresAt (Unix seconds), qosStatus, duration, device, applicationServer,
                     devicePorts, applicationServerPorts, qosProfile, webhook{notificationUrl}
  v0.11.0 .. v1.1.0: sessionId, startedAt/expiresAt (RFC 3339), qosStatus, [statusInfo], duration, device, ..., sink

Notification callback (07b A12): v0.8.1 calls `<notificationUrl>/notifications`, v0.9.0 and v0.10.0 call
`webhook.notificationUrl`, v0.11.0 and later call `sink`. The gold `sink` of a v0.8.1 intent is therefore the client's
URL plus "/notifications". The v0.8.1 answer does not echo `notificationUrl`: a world session's sink cannot be mapped
back to a base URL.

Native requests never contain the gold profile (07b A5): an intent's `gold_profile` appears only in gold calls.

Client versions: v0.8.1, v0.9.0, v0.10.0, v0.11.0, v1.0.0, v1.1.0
Server version: v1.1.0
"""
from __future__ import annotations

import datetime
from typing import Any

from nlipeval.tasks.render import ids

API = "L3"
SERVER_VERSION = "v1.1.0"
SERVER_BASE = "/quality-on-demand/v1"
NOTIFICATIONS_SUFFIX = "/notifications"

_BASE = {
    "v0.8.1": "/qod/v0",
    "v0.9.0": "/qod/v0",
    "v0.10.0": "/qod/v0",
    "v0.11.0": "/quality-on-demand/v0.11",
    "v1.0.0": "/quality-on-demand/v1",
    "v1.1.0": "/quality-on-demand/v1",
}

# The native request carries publicAddress and publicPort at v0.9.0 and later, never a privateAddress (07b A2)
NATIVE_HAS_PRIVATE: dict[str, bool] = {v: False for v in _BASE}


# --- native request, per version ---------------------------------------------------------------

def _ue_id_v081(intent: dict) -> dict:
    """ueId of v0.8.1 (L3-C3..C9). `ipv4addr` is a string: the port cannot be carried."""
    p = intent["params"]
    n = ids.num(p["device_id"])
    ident = p["identifier"]
    if ident == "phone_number":
        return {"msisdn": ids.phone(n, ids.phone_plus("L3", "v0.8.1", intent))}
    if ident == "ipv4_with_port":
        return {"ipv4addr": ids.public_ipv4(n)}
    if ident == "ipv6":
        return {"ipv6addr": ids.ipv6(n)}
    if ident == ids.NAI_ONLY:
        return {"externalId": ids.nai(n)}
    raise ValueError(f"Unknown identifier type: {ident!r}")


def _as_id_v081(intent: dict) -> dict:
    """asId of v0.8.1 (L3-C10..C12)."""
    a = intent["params"]["application_server"]
    out = {}
    if "ipv4Address" in a:
        out["ipv4addr"] = a["ipv4Address"]
    if "ipv6Address" in a:
        out["ipv6addr"] = a["ipv6Address"]
    return out


def _application_server(intent: dict) -> dict:
    a = intent["params"]["application_server"]
    out = {}
    if "ipv4Address" in a:
        out["ipv4Address"] = a["ipv4Address"]
    if "ipv6Address" in a:
        out["ipv6Address"] = a["ipv6Address"]
    return out


def _create_body_v081(intent: dict) -> dict:
    p = intent["params"]
    body: dict = {}
    if p.get("duration_s") is not None:
        body["duration"] = p["duration_s"]
    body["ueId"] = _ue_id_v081(intent)
    body["asId"] = _as_id_v081(intent)
    if "device_ports" in p:
        body["uePorts"] = p["device_ports"]
    if "application_server_ports" in p:
        body["asPorts"] = p["application_server_ports"]
    body["qos"] = p["profile"]
    if "sink" in p:
        body["notificationUrl"] = p["sink"]
    return body


def _create_body_server_form(intent: dict, version: str) -> dict:
    """Native body at v0.9.0 and later: `webhook` at v0.9.0/v0.10.0, `sink` from v0.11.0."""
    p = intent["params"]
    body: dict = {}
    if p.get("duration_s") is not None:
        body["duration"] = p["duration_s"]
    body["device"] = ids.server_form_device(intent)
    body["applicationServer"] = _application_server(intent)
    if "device_ports" in p:
        body["devicePorts"] = p["device_ports"]
    if "application_server_ports" in p:
        body["applicationServerPorts"] = p["application_server_ports"]
    body["qosProfile"] = p["profile"]
    if "sink" in p:
        if version in ("v0.9.0", "v0.10.0"):
            body["webhook"] = {"notificationUrl": p["sink"]}
        else:
            body["sink"] = p["sink"]
    return body


def render_request(intent: dict, version: str) -> dict[str, Any]:
    """Return {method, path, body} for the client's native request at `version`."""
    base = _BASE.get(version)
    if base is None:
        raise ValueError(f"Unknown L3 version: {version!r}")
    op = intent.get("operation", "createSession")
    p = intent["params"]
    if op == "createSession":
        body = _create_body_v081(intent) if version == "v0.8.1" else _create_body_server_form(intent, version)
        return {"method": "POST", "path": f"{base}/sessions", "body": body}
    if op == "getSession":
        return {"method": "GET", "path": f"{base}/sessions/{p['session_id']}", "body": None}
    if op == "deleteSession":
        return {"method": "DELETE", "path": f"{base}/sessions/{p['session_id']}", "body": None}
    raise ValueError(f"Unknown L3 operation: {op!r}")


# --- gold calls (server version) ---------------------------------------------------------------

def render_gold_calls(intent: dict, client_version: str) -> list[dict[str, Any]]:
    """Acceptable calls at the server version, primary first.

    The gold profile (`gold_profile`) replaces the requested profile where the requested one cannot give the full
    duration (m01, m11). The v0.8.1 `sink` is the client's `notificationUrl` plus "/notifications".
    """
    op = intent.get("operation", "createSession")
    p = intent["params"]
    if op == "getSession":
        return [{"method": "GET", "path": f"{SERVER_BASE}/sessions/{p['session_id']}", "body": None}]
    if op == "deleteSession":
        return [{"method": "DELETE", "path": f"{SERVER_BASE}/sessions/{p['session_id']}", "body": None}]
    calls = []
    for dev in ids.gold_devices(intent, native_has_private=NATIVE_HAS_PRIVATE[client_version]):
        body: dict = {}
        if p.get("duration_s") is not None:
            body["duration"] = p["duration_s"]
        body["device"] = dev
        body["applicationServer"] = _application_server(intent)
        if "device_ports" in p:
            body["devicePorts"] = p["device_ports"]
        if "application_server_ports" in p:
            body["applicationServerPorts"] = p["application_server_ports"]
        body["qosProfile"] = p.get("gold_profile", p["profile"])
        if "sink" in p:
            body["sink"] = p["sink"] + (NOTIFICATIONS_SUFFIX if client_version == "v0.8.1" else "")
        calls.append({"method": "POST", "path": f"{SERVER_BASE}/sessions", "body": body})
    return calls


# --- answers -----------------------------------------------------------------------------------

def _unix(ts: str | None) -> int | None:
    if not ts:
        return None
    return int(datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())


def _ue_id_from_device(device: dict) -> dict:
    ue: dict = {}
    if "phoneNumber" in device:
        ue["msisdn"] = device["phoneNumber"]
    if "networkAccessIdentifier" in device:
        ue["externalId"] = device["networkAccessIdentifier"]
    if "ipv4Address" in device:
        ue["ipv4addr"] = device["ipv4Address"]["publicAddress"]
    if "ipv6Address" in device:
        ue["ipv6addr"] = device["ipv6Address"]
    return ue


def _as_id_from_server(app_server: dict) -> dict:
    out = {}
    if "ipv4Address" in app_server:
        out["ipv4addr"] = app_server["ipv4Address"]
    if "ipv6Address" in app_server:
        out["ipv6addr"] = app_server["ipv6Address"]
    return out


def render_answer(world_outcome: dict | None, version: str) -> dict[str, Any]:
    """Return {status, result} for the client at `version`, given the server's response body.

    A 204 (delete) has no body: {done, null}. An error body has "code": declined (no result, the service refused).
    """
    if version not in _BASE:
        raise ValueError(f"Unknown L3 version: {version!r}")
    if not world_outcome:
        return {"status": "done", "result": None}
    if "code" in world_outcome:
        return {"status": "declined", "result": None}

    o = world_outcome
    device = o.get("device")
    app_server = o.get("applicationServer", {})
    result: dict = {}
    if o.get("duration") is not None:
        result["duration"] = o["duration"]

    if version == "v0.8.1":
        if device:
            result["ueId"] = _ue_id_from_device(device)
        result["asId"] = _as_id_from_server(app_server)
        if o.get("devicePorts"):
            result["uePorts"] = o["devicePorts"]
        if o.get("applicationServerPorts"):
            result["asPorts"] = o["applicationServerPorts"]
        if o.get("qosProfile"):
            result["qos"] = o["qosProfile"]
        result["id"] = o["sessionId"]
        result["startedAt"] = _unix(o["startedAt"])
        result["expiresAt"] = _unix(o["expiresAt"])
        return {"status": "done", "result": result}

    if device:
        result["device"] = device
    result["applicationServer"] = app_server
    if o.get("devicePorts"):
        result["devicePorts"] = o["devicePorts"]
    if o.get("applicationServerPorts"):
        result["applicationServerPorts"] = o["applicationServerPorts"]
    if o.get("qosProfile"):
        result["qosProfile"] = o["qosProfile"]
    result["sessionId"] = o["sessionId"]

    if version in ("v0.9.0", "v0.10.0"):
        if o.get("sink"):
            result["webhook"] = {"notificationUrl": o["sink"]}
        result["startedAt"] = _unix(o["startedAt"])
        result["expiresAt"] = _unix(o["expiresAt"])
        result["qosStatus"] = o["qosStatus"]
        return {"status": "done", "result": result}

    if o.get("sink"):
        result["sink"] = o["sink"]
    result["startedAt"] = o["startedAt"]
    result["expiresAt"] = o["expiresAt"]
    result["qosStatus"] = o["qosStatus"]
    if o.get("statusInfo"):
        result["statusInfo"] = o["statusInfo"]
    return {"status": "done", "result": result}
