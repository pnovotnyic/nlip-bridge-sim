"""Renderers for L1 (Device Reachability Status).

render_request(intent, version)        -> {method, path, body}: the client's native request
render_gold_calls(intent, version)     -> [{method, path, body}, ...]: acceptable calls at the server version
render_answer(world_outcome, version)  -> {status, result}

Change catalogue entries implemented:
  - [renamed] POST /connectivity -> POST /retrieve (v0.5.1 -> v0.6.0, L1-C1)
  - [unit_format] phoneNumber pattern tightened at v1.0.0 (L1-C2): at v0.5.1 the pattern allows numbers
    without "+"; the native request of even-numbered intents has none (07b A10), the gold keeps "+"
  - [restructured+renamed] connectivityStatus/reachabilityStatus -> reachable+connectivity[] (L1-C3,C4)

Gold device (07b A1, A2): only what the client can know, see render/ids.py.

Client versions: v0.5.1, v0.6.0, v1.0.0
Server version: v1.0.0
"""
from __future__ import annotations

from typing import Any

from nlipeval.tasks.render import ids

API = "L1"
SERVER_VERSION = "v1.0.0"
SERVER_PATH = "/device-reachability-status/v1/retrieve"

# True where the native request carries a privateAddress next to the public one (never at L1)
NATIVE_HAS_PRIVATE: dict[str, bool] = {"v0.5.1": False, "v0.6.0": False, "v1.0.0": False}


def _native_device(intent: dict, version: str) -> dict:
    """The `device` object of the native request: the intent's own identifier."""
    return ids.server_form_device(intent, plus=ids.phone_plus(API, version, intent))


def render_request(intent: dict, version: str) -> dict[str, Any]:
    """Return {method, path, body} for the client's native request at `version`.

    v0.5.1: POST /connectivity  (body field: device)
    v0.6.0: POST /retrieve      (body field: device)
    v1.0.0: POST /retrieve      (body field: device)

    Catalogue entry L1-C1 (renamed): path changed from /connectivity to /retrieve at v0.6.0.
    """
    if version == "v0.5.1":
        return {"method": "POST", "path": "/device-status/v0/connectivity",
                "body": {"device": _native_device(intent, version)}}
    if version == "v0.6.0":
        return {"method": "POST", "path": "/device-reachability-status/v0.6/retrieve",
                "body": {"device": _native_device(intent, version)}}
    if version == "v1.0.0":
        return {"method": "POST", "path": SERVER_PATH, "body": {"device": _native_device(intent, version)}}
    raise ValueError(f"Unknown L1 version: {version!r}")


def render_gold_calls(intent: dict, client_version: str) -> list[dict[str, Any]]:
    """Acceptable calls at the server version, primary first."""
    devices = ids.gold_devices(intent, native_has_private=NATIVE_HAS_PRIVATE[client_version])
    return [{"method": "POST", "path": SERVER_PATH, "body": {"device": d}} for d in devices]


def render_answer(world_outcome: dict | None, version: str) -> dict[str, Any]:
    """Return {status, result} for the client at `version`, given the server's response body.

    world_outcome keys: reachable (bool), connectivity (list|None), lastStatusTime (str).

    v0.5.1 response: {connectivityStatus: "CONNECTED_DATA"|"CONNECTED_SMS"|"NOT_CONNECTED"}
      Catalogue L1-C3 (restructured+renamed): rule is:
        - connectivity includes DATA -> CONNECTED_DATA
        - connectivity includes SMS only -> CONNECTED_SMS
        - not reachable -> NOT_CONNECTED
    v0.6.0 response: {reachabilityStatus: same three values, lastStatusTime}
    v1.0.0 response: {reachable, connectivity[], lastStatusTime} (unchanged)

    If the world_outcome is an error body (has "code"), status is "declined": no result, the service refused.
    """
    world_outcome = world_outcome or {}
    if "code" in world_outcome:
        return {"status": "declined", "result": None}

    reachable = world_outcome.get("reachable", False)
    connectivity = world_outcome.get("connectivity")
    last_status_time = world_outcome.get("lastStatusTime")

    if version in ("v0.5.1", "v0.6.0"):
        if not reachable:
            cs = "NOT_CONNECTED"
        elif connectivity and "DATA" in connectivity:
            cs = "CONNECTED_DATA"
        else:
            cs = "CONNECTED_SMS"
        if version == "v0.5.1":
            return {"status": "done", "result": {"connectivityStatus": cs}}
        result: dict = {"reachabilityStatus": cs}
        if last_status_time:
            result["lastStatusTime"] = last_status_time
        return {"status": "done", "result": result}

    if version == "v1.0.0":
        result = {"reachable": reachable}
        if connectivity:
            result["connectivity"] = connectivity
        if last_status_time:
            result["lastStatusTime"] = last_status_time
        return {"status": "done", "result": result}

    raise ValueError(f"Unknown L1 version: {version!r}")
