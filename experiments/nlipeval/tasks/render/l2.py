"""Renderers for L2 (Location Verification).

render_request(intent, version)        -> {method, path, body}: the client's native request
render_gold_calls(intent, version)     -> [{method, path, body}, ...]: acceptable calls at the server version
render_answer(world_outcome, version)  -> {status, result}

Change catalogue entries implemented:
  - [restructured+renamed] ueId -> device (v0.1.0 -> v0.2.0, L2-C1)
  - [unit_format+renamed]  ueId.msisdn -> device.phoneNumber (L2-C2); the msisdn pattern allows numbers without
    "+", the native request of intents numbered 1 or 2 mod 4 has none (08a D11), the gold keeps "+"
  - [renamed]              ueId.externalId -> device.networkAccessIdentifier (L2-C3)
  - [restructured+newly_required] ueId.ipv4Addr (string) -> device.ipv4Address.publicAddress (L2-C4)
  - [restructured]         uePort -> device.ipv4Address.publicPort (L2-C5)
  - [newly_required]       device.ipv4Address.privateAddress: not used; the client knows public address and port only
  - [renamed]              ueId.ipv6Addr -> device.ipv6Address (L2-C7)
  - [newly_required]       area.areaType added (L2-C8); a constant of the server interface (CIRCLE)
  - [restructured]         latitude, longitude -> area.center.latitude, area.center.longitude (L2-C9, C10)
  - [restructured+unit_format] accuracy (km) -> area.radius (metres) (L2-C11); never clamped (07b A3)
  - [added_optional]       maxAge added from v0.2.0 (L2-C12); v0.2.0 has a minimum of 60 s
  - [changed_meaning+unit_format] verificationResult: boolean -> enum TRUE/FALSE/PARTIAL/UNKNOWN (L2-C13)
  - [newly_required+added_optional] lastLocationTime (L2-C14)

Client versions: v0.1.0, v0.2.0, v1.0.0, v2.0.0, v3.0.0
Server version: v3.0.0
"""
from __future__ import annotations

from typing import Any

from nlipeval.tasks.render import ids

API = "L2"
SERVER_VERSION = "v3.0.0"
SERVER_PATH = "/location-verification/v3/verify"

_PATHS = {
    "v0.1.0": "/location/v0/verify",
    "v0.2.0": "/location-verification/v0/verify",
    "v1.0.0": "/location-verification/v1/verify",
    "v2.0.0": "/location-verification/v2/verify",
    "v3.0.0": SERVER_PATH,
}

# The native request never carries a privateAddress: the client knows public address and port only (07b A2)
NATIVE_HAS_PRIVATE: dict[str, bool] = {v: False for v in _PATHS}

# v0.2.0 `maxAge` minimum in seconds (specs/L2/v0.2.0.yaml, MaxAge)
V020_MIN_MAX_AGE = 60

# v0.1.0 `accuracy` range in km (specs/L2/v0.1.0.yaml, Accuracy)
ACCURACY_MIN_KM = 2.0
ACCURACY_MAX_KM = 200.0


def _area_body_server(intent: dict) -> dict:
    """Build the `area` object in server (v0.2.0+) form."""
    a = intent["params"]["area"]
    return {
        "areaType": "CIRCLE",
        "center": {"latitude": a["center"]["latitude"], "longitude": a["center"]["longitude"]},
        "radius": a["radius"],  # metres
    }


def _area_body_v010(intent: dict) -> dict:
    """v0.1.0 area fields: latitude, longitude, accuracy in km (L2-C9, C10, C11).

    The value is never clamped: an intent that v0.1.0 cannot express makes generation fail (07b A3).
    """
    a = intent["params"]["area"]
    accuracy_km = a["radius"] / 1000.0
    if not ACCURACY_MIN_KM <= accuracy_km <= ACCURACY_MAX_KM:
        raise ValueError(
            f"{intent['id']}: radius {a['radius']} m is {accuracy_km} km, outside the v0.1.0 accuracy range "
            f"{ACCURACY_MIN_KM}-{ACCURACY_MAX_KM} km")
    return {"latitude": a["center"]["latitude"], "longitude": a["center"]["longitude"], "accuracy": accuracy_km}


def _device_body_v010(intent: dict) -> dict:
    """`ueId` plus the separate `uePort` of v0.1.0 (L2-C1..C7)."""
    p = intent["params"]
    n = ids.num(p["device_id"])
    ident = p["identifier"]
    extra: dict = {}
    if ident == "phone_number":
        ue_id = {"msisdn": ids.phone(n, ids.phone_plus("L2", "v0.1.0", intent))}
    elif ident == "ipv4_with_port":
        ue_id = {"ipv4Addr": ids.public_ipv4(n)}
        extra["uePort"] = ids.public_port(n)
    elif ident == "ipv6":
        ue_id = {"ipv6Addr": ids.ipv6(n)}
    elif ident == ids.NAI_ONLY:
        ue_id = {"externalId": ids.nai(n)}
    else:
        raise ValueError(f"Unknown identifier type: {ident!r}")
    return {"ueId": ue_id, **extra}


def render_request(intent: dict, version: str) -> dict[str, Any]:
    """Return {method, path, body} for the client's native request at `version`.

    v0.1.0: fields ueId, [uePort], latitude, longitude, accuracy (km); no maxAge field.
    v0.2.0 and later: device, area {areaType, center, radius}, [maxAge].
    """
    if version not in _PATHS:
        raise ValueError(f"Unknown L2 version: {version!r}")
    if version == "v0.1.0":
        body = {**_device_body_v010(intent), **_area_body_v010(intent)}
        return {"method": "POST", "path": _PATHS[version], "body": body}
    body = {"device": ids.server_form_device(intent), "area": _area_body_server(intent)}
    max_age = intent["params"].get("max_age")
    if max_age is not None:
        # v0.2.0 allows maxAge >= 60 only: "a fresh reading" is sent as the smallest value the version accepts
        body["maxAge"] = max(max_age, V020_MIN_MAX_AGE) if version == "v0.2.0" else max_age
    return {"method": "POST", "path": _PATHS[version], "body": body}


def render_gold_calls(intent: dict, client_version: str) -> list[dict[str, Any]]:
    """Acceptable calls at the server version, primary first.

    `gold_max_age` (L2 m30) replaces the intent's `max_age` in the gold call: the client's fact makes a reading
    up to one hour old acceptable.
    """
    p = intent["params"]
    max_age = p.get("gold_max_age", p.get("max_age"))
    calls = []
    for dev in ids.gold_devices(intent, native_has_private=NATIVE_HAS_PRIVATE[client_version]):
        body: dict = {"device": dev, "area": _area_body_server(intent)}
        if max_age is not None:
            body["maxAge"] = max_age
        calls.append({"method": "POST", "path": SERVER_PATH, "body": body})
    # v0.2.0 cannot send maxAge below 60: its native request carries 60, and the same call at the server is an alternative
    native_max_age = max(max_age, V020_MIN_MAX_AGE) if max_age is not None else None
    if client_version == "v0.2.0" and native_max_age is not None and native_max_age != max_age:
        calls += [{**c, "body": {**c["body"], "maxAge": native_max_age}} for c in list(calls)]
    return calls


def render_answer(world_outcome: dict | None, version: str) -> dict[str, Any]:
    """Return {status, result} for the client at `version`, given the server's response body.

    Server response fields: verificationResult (TRUE/FALSE/PARTIAL), [matchRate], lastLocationTime.
    An error body has "code" (for example LOCATION_VERIFICATION.UNABLE_TO_LOCATE).

    v0.1.0: verificationResult is a boolean (L2-C13); PARTIAL and UNABLE_TO_LOCATE have no boolean: unrepresentable.
    v0.2.0 to v2.0.0: verificationResult is TRUE/FALSE/PARTIAL/UNKNOWN; UNABLE_TO_LOCATE gives UNKNOWN (done).
    v3.0.0: UNABLE_TO_LOCATE is an error: declined.
    Every other error code gives declined: no result, the service refused.
    """
    world_outcome = world_outcome or {}
    if "code" in world_outcome:
        if world_outcome["code"] == "LOCATION_VERIFICATION.UNABLE_TO_LOCATE":
            if version in ("v0.2.0", "v1.0.0", "v2.0.0"):
                return {"status": "done", "result": {"verificationResult": "UNKNOWN"}}
            if version == "v0.1.0":
                return {"status": "unrepresentable", "result": None}
        return {"status": "declined", "result": None}

    result_str = world_outcome["verificationResult"]
    last_location_time = world_outcome.get("lastLocationTime")
    match_rate = world_outcome.get("matchRate")

    if version == "v0.1.0":
        if result_str == "PARTIAL":
            return {"status": "unrepresentable", "result": None}
        return {"status": "done", "result": {"verificationResult": result_str == "TRUE"}}

    if version in ("v0.2.0", "v1.0.0", "v2.0.0", "v3.0.0"):
        result: dict = {"verificationResult": result_str}
        if last_location_time:
            result["lastLocationTime"] = last_location_time
        if match_rate is not None:
            result["matchRate"] = match_rate
        return {"status": "done", "result": result}

    raise ValueError(f"Unknown L2 version: {version!r}")
