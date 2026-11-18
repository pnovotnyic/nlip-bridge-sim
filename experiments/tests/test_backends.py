"""Stage 04 tests: the mock backends against their pinned specifications and the world files.

Everything runs in-process (no sockets) except `test_launcher_http`, which starts the real processes.
Run from experiments/:  uv run pytest tests/test_backends.py
"""
from __future__ import annotations

import json
import math
import shutil
import warnings
from pathlib import Path

import httpx
import pytest
import yaml
from openapi_core import OpenAPI

from nlipeval.backends import launcher
from nlipeval.backends.l1_reachability import make_backend as make_l1
from nlipeval.backends.l2_location import classify, haversine_m, lens_area, make_backend as make_l2
from nlipeval.backends.l3_qod import make_backend as make_l3
from nlipeval.backends.profile_table import render_profile_table
from nlipeval.backends.world import ROOT, World

warnings.filterwarnings("ignore", message="Unsupported scheme type")

L1, L2, L3 = "/device-reachability-status/v1", "/location-verification/v3", "/quality-on-demand/v1"
PHONE = lambda n: f"+990100{n:04d}"  # noqa: E731


@pytest.fixture(scope="module")
def world() -> World:
    return World()


class Client:
    def __init__(self, backend, session="t1", clock=None):
        self.b, self.session, self.clock = backend, session, clock

    def call(self, method, path, body=None, headers=None):
        h = {"X-Eval-Session": self.session, **(headers or {})}
        if self.clock:
            h["X-Eval-Clock"] = self.clock
        raw = json.dumps(body).encode() if body is not None else b""
        result, _ = self.b.handle(method, path, "http://127.0.0.1:1", h, raw)
        return result

    def post(self, path, body, **kw):
        return self.call("POST", path, body, **kw)


def circle(lat, lon, r):
    return {"areaType": "CIRCLE", "center": {"latitude": lat, "longitude": lon}, "radius": r}


# --- the world ------------------------------------------------------------------------------------
def test_world_is_consistent(world):
    assert world.check() == []
    assert len(world.devices) == 40
    assert len(world.hash) == 64


def test_world_files_use_only_documented_ranges(world):
    text = "".join((ROOT / "config" / "world" / n).read_text() for n in ("devices.yaml", "sessions.yaml"))
    import re
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text):
        assert ip.startswith(("192.0.2.", "198.51.100.", "203.0.113.")), ip
    for v6 in re.findall(r"\b2001:[0-9a-f:]+", text):
        assert v6.startswith("2001:db8:"), v6


def test_world_covers_every_state(world):
    assert {d.reach_state for d in world.devices} == {"DATA_SMS", "DATA_ONLY", "SMS_ONLY", "NONE"}
    assert any(d.location is None for d in world.devices)
    assert any(d.location and not d.location.fresh_available for d in world.devices)
    assert {p.status for p in world.profiles.values()} == {"ACTIVE", "INACTIVE", "DEPRECATED"}
    assert {s.qos_status for s in world.sessions.values()} == {"AVAILABLE", "UNAVAILABLE"}


def test_profile_table_matches_world(world):
    table = render_profile_table(world).splitlines()
    assert table[0].startswith("name | status")
    assert len(table) == 1 + len(world.profiles)
    for p, row in zip(world.profiles.values(), table[1:]):
        assert row.startswith(f"{p.name} | {p.status} | ")


# --- L1 -------------------------------------------------------------------------------------------
def test_l1_all_reachability_states(world):
    c = Client(make_l1())
    for d in world.devices:
        r = c.post(f"{L1}/retrieve", {"device": {"phoneNumber": d.phone_number}})
        assert r.status == 200, r.body
        assert r.body["reachable"] == (d.reach_state != "NONE")
        assert r.body.get("connectivity") == {"DATA_SMS": ["DATA", "SMS"], "DATA_ONLY": ["DATA"],
                                               "SMS_ONLY": ["SMS"], "NONE": None}[d.reach_state]
        assert "device" not in r.body


def test_l1_identifiers_and_errors(world):
    c = Client(make_l1())
    d = world.device("D02")
    ok = lambda dev: c.post(f"{L1}/retrieve", {"device": dev})  # noqa: E731
    v4 = {"publicAddress": d.public_address, "publicPort": d.public_port}
    assert ok({"ipv4Address": v4}).status == 200
    assert ok({"ipv4Address": {"publicAddress": d.public_address, "privateAddress": d.private_address}}).status == 200
    assert ok({"ipv6Address": "2001:db8:a:2::77"}).status == 200       # any address in the /64
    assert ok({"ipv4Address": {"publicAddress": d.public_address, "publicPort": 1}}).body["code"] == "IDENTIFIER_NOT_FOUND"
    # several identifiers: when mismatched on L1, we get IDENTIFIER_MISMATCH (422)
    r = ok({"phoneNumber": d.phone_number, "ipv6Address": "2001:db8:a:9::1"})
    assert r.status == 422 and r.body["code"] == "IDENTIFIER_MISMATCH"
    # when consistent, it succeeds
    r = ok({"phoneNumber": d.phone_number, "ipv6Address": d.ipv6_address})
    assert r.status == 200 and r.body["lastStatusTime"].startswith("2026-12-01T11:59")
    assert c.post(f"{L1}/retrieve", {}).body["code"] == "MISSING_IDENTIFIER"
    assert ok({"networkAccessIdentifier": "dev002@nlipeval.example"}).body["code"] == "UNSUPPORTED_IDENTIFIER"
    assert ok({"phoneNumber": PHONE(999)}).body["code"] == "IDENTIFIER_NOT_FOUND"


@pytest.mark.parametrize("body,status", [
    ({"device": {"phoneNumber": "12345"}}, 400),
    ({"device": {"ipv6Address": "not-an-address"}}, 400),
    ({"device": {}}, 400),
    ({"device": {"ipv4Address": {"publicAddress": "999.1.1.1", "publicPort": 5}}}, 400),
])
def test_l1_invalid_requests(body, status):
    r = Client(make_l1()).post(f"{L1}/retrieve", body)
    assert r.status == status and r.body["code"] == "INVALID_ARGUMENT"


def test_l1_clock_header_and_malformed_body():
    c = Client(make_l1(), clock="2027-01-01T00:00:00Z")
    r = c.post(f"{L1}/retrieve", {"device": {"phoneNumber": PHONE(1)}})
    assert r.body["lastStatusTime"] == "2026-12-31T23:59:50Z"
    r, _ = c.b.handle("POST", f"{L1}/retrieve", "http://x", {}, b"{bad")
    assert r.status == 400 and r.body["code"] == "INVALID_ARGUMENT"
    assert Client(make_l1()).call("GET", f"{L1}/retrieve").status == 404
    assert Client(make_l1()).call("GET", "/elsewhere").status == 404


# --- L2: geometry ---------------------------------------------------------------------------------
def test_haversine_known_distance():
    # one degree of latitude is 111.2 km on this sphere
    assert haversine_m(50, 7, 51, 7, 6371008.8) == pytest.approx(111195, rel=1e-3)


def test_lens_area_limits():
    assert lens_area(10, 1, 1) == 0
    assert lens_area(0, 2, 5) == pytest.approx(math.pi * 4)
    assert lens_area(1, 1, 1) == pytest.approx(2 * math.acos(0.5) - 0.5 * math.sqrt(3))


@pytest.mark.parametrize("d,rr,rn,expect", [
    (0, 1000, 800, ("TRUE", None)),         # network area inside the request
    (200, 1000, 800, ("TRUE", None)),       # exactly inside: d + rn == rr
    (2500, 1000, 800, ("FALSE", None)),     # apart
    (1800, 1000, 800, ("FALSE", None)),     # touching from outside: no overlap
    (0, 800, 1500, ("PARTIAL", 28)),        # the request is inside the (larger) network area
])
def test_classify(d, rr, rn, expect):
    got = classify(d, rr, rn)
    assert got[0] == expect[0]
    if expect[1] is not None:
        assert abs(got[1] - expect[1]) <= 1


def test_classify_match_rate_is_in_range_and_monotone():
    rates = [classify(d, 1000, 1000)[1] for d in range(100, 1900, 100)]
    assert all(1 <= r <= 99 for r in rates) and rates == sorted(rates, reverse=True)


# --- L2: API --------------------------------------------------------------------------------------
def _verify(c, n, area, **extra):
    return c.post(f"{L2}/verify", {"device": {"phoneNumber": PHONE(n)}, "area": area, **extra})


def test_l2_true_false_partial(world):
    c = Client(make_l2())
    d = world.device("D01")                                    # Berlin, accuracy 800 m, age 30 s
    lat, lon = d.location.latitude, d.location.longitude
    r = _verify(c, 1, circle(lat, lon, 5000))
    assert (r.status, r.body["verificationResult"]) == (200, "TRUE") and "matchRate" not in r.body
    assert r.body["lastLocationTime"] == "2026-12-01T11:59:30Z"
    r = _verify(c, 1, circle(lat + 1.0, lon, 5000))             # about 111 km away
    assert r.body["verificationResult"] == "FALSE" and "matchRate" not in r.body
    r = _verify(c, 1, circle(lat + 0.01, lon, 1000))            # about 1.1 km away, circles overlap
    assert r.body["verificationResult"] == "PARTIAL" and 1 <= r.body["matchRate"] <= 99


def test_l2_errors(world):
    c = Client(make_l2())
    d = world.device("D01")
    lat, lon = d.location.latitude, d.location.longitude
    code = lambda r: (r.status, r.body["code"])  # noqa: E731
    assert code(_verify(c, 1, circle(lat, lon, 500))) == (422, "LOCATION_VERIFICATION.INVALID_AREA")
    assert code(_verify(c, 1, circle(10.0, 10.0, 5000))) == (422, "LOCATION_VERIFICATION.AREA_NOT_COVERED")
    no_loc = next(x for x in world.devices if x.location is None)
    assert code(c.post(f"{L2}/verify", {"device": {"phoneNumber": no_loc.phone_number}, "area": circle(lat, lon, 5000)})) \
        == (422, "LOCATION_VERIFICATION.UNABLE_TO_LOCATE")
    assert code(c.post(f"{L2}/verify", {"device": {"phoneNumber": no_loc.phone_number}, "area": circle(lat, lon, 5000),
                                        "maxAge": 60})) == (422, "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE")
    assert code(c.post(f"{L2}/verify", {"area": circle(lat, lon, 5000)})) == (422, "MISSING_IDENTIFIER")
    assert code(_verify(c, 99, circle(lat, lon, 5000))) == (404, "IDENTIFIER_NOT_FOUND")
    assert code(_verify(c, 1, circle(95, lon, 5000))) == (400, "OUT_OF_RANGE")
    assert code(_verify(c, 1, {"areaType": "CIRCLE"})) == (400, "INVALID_ARGUMENT")      # discriminator subschema
    assert code(_verify(c, 1, {"areaType": "SQUARE"})) == (400, "INVALID_ARGUMENT")


def test_l2_max_age(world):
    c = Client(make_l2())
    fresh = next(d for d in world.devices if d.location and d.location.fresh_available and d.location.age_s > 600)
    stale = next(d for d in world.devices if d.location and not d.location.fresh_available and d.location.age_s > 600)
    for d, expect in ((fresh, 200), (stale, 422)):
        r = c.post(f"{L2}/verify", {"device": {"phoneNumber": d.phone_number},
                                    "area": circle(d.location.latitude, d.location.longitude, 5000), "maxAge": 600})
        assert r.status == expect
        if expect == 200:
            assert r.body["lastLocationTime"] == "2026-12-01T12:00:00Z"     # a fresh fix
        else:
            assert r.body["code"] == "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE"
    ok = c.post(f"{L2}/verify", {"device": {"phoneNumber": fresh.phone_number}, "maxAge": 10 ** 6,
                                 "area": circle(fresh.location.latitude, fresh.location.longitude, 5000)})
    assert ok.status == 200 and ok.body["lastLocationTime"] != "2026-12-01T12:00:00Z"   # stored fix is young enough


# --- L3 -------------------------------------------------------------------------------------------
def _create(c, n=1, profile="QOS_E", duration=600, server="198.51.100.20", **extra):
    return c.post(f"{L3}/sessions", {"device": {"phoneNumber": PHONE(n)}, "applicationServer": {"ipv4Address": server},
                                     "qosProfile": profile, "duration": duration, **extra})


def test_l3_create_get_delete_cycle():
    c = Client(make_l3())
    r = _create(c, sink="https://app.example.org/n")
    assert r.status == 201 and r.body["qosStatus"] == "AVAILABLE"
    assert r.body["startedAt"] == "2026-12-01T12:00:00Z" and r.body["expiresAt"] == "2026-12-01T12:10:00Z"
    sid = r.body["sessionId"]
    g = c.call("GET", f"{L3}/sessions/{sid}")
    assert g.status == 200 and g.body == r.body
    assert c.call("DELETE", f"{L3}/sessions/{sid}").status == 204
    assert c.call("GET", f"{L3}/sessions/{sid}").body["code"] == "NOT_FOUND"
    assert c.call("DELETE", f"{L3}/sessions/{sid}").status == 404
    assert _create(c).status == 201          # the flow is free again


def test_l3_errors():
    c = Client(make_l3())
    code = lambda r: (r.status, r.body["code"])  # noqa: E731
    assert code(_create(c, duration=3600)) == (400, "QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE")   # QOS_E max 30 min
    assert code(_create(c, profile="QOS_L", duration=60)) == (400, "QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE")
    assert code(_create(c, profile="QOS_XL")) == (422, "QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE")
    assert code(_create(c, profile="voice")) == (422, "QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE")
    assert code(_create(c, profile="platinum")) == (404, "NOT_FOUND")
    assert code(_create(c, duration=0)) == (400, "OUT_OF_RANGE")
    assert code(_create(c, sink="http://insecure.example")) == (400, "INVALID_SINK")
    assert code(_create(c, server="999.0.0.1")) == (400, "INVALID_ARGUMENT")
    assert code(_create(c, n=99)) == (404, "IDENTIFIER_NOT_FOUND")
    assert code(c.post(f"{L3}/sessions", {"applicationServer": {"ipv4Address": "198.51.100.1"},
                                          "qosProfile": "QOS_E", "duration": 60})) == (422, "MISSING_IDENTIFIER")
    assert code(c.post(f"{L3}/sessions", {"device": {"networkAccessIdentifier": "a@b"},
                                          "applicationServer": {"ipv4Address": "198.51.100.1"},
                                          "qosProfile": "QOS_E", "duration": 60})) == (422, "UNSUPPORTED_IDENTIFIER")
    assert code(_create(c, qosProfile=None)) == (400, "INVALID_ARGUMENT")
    assert code(c.call("GET", f"{L3}/sessions/not-a-uuid")) == (400, "INVALID_ARGUMENT")


def test_l3_credentials():
    c = Client(make_l3())
    tok = {"credentialType": "ACCESSTOKEN", "accessToken": "t", "accessTokenExpiresUtc": "2030-01-01T00:00:00Z",
           "accessTokenType": "bearer"}
    assert _create(c, 1, sink="https://a.example/x", sinkCredential=tok).status == 201
    assert "sinkCredential" not in _create(c, 2, sink="https://a.example/x", sinkCredential=tok).body
    r = _create(c, 3, sink="https://a.example/x", sinkCredential={"credentialType": "PLAIN"})
    assert r.body["code"] == "INVALID_CREDENTIAL"
    r = _create(c, 3, sink="https://a.example/x", sinkCredential={**tok, "accessTokenType": "mac"})
    assert r.status == 400


def test_l3_conflict_is_per_device_and_flow():
    c = Client(make_l3())
    assert _create(c, 1).status == 201
    assert _create(c, 1).body["code"] == "CONFLICT"
    assert _create(c, 2).status == 201                                   # another device
    assert _create(c, 1, server="198.51.100.21").status == 201            # another application server
    assert _create(c, 1, devicePorts={"ports": [5060]}).status == 201    # another flow


def test_l3_world_sessions_and_echoed_device(world):
    c = Client(make_l3())
    s = next(iter(world.sessions.values()))
    g = c.call("GET", f"{L3}/sessions/{s.id}")
    assert g.status == 200 and g.body["qosStatus"] == "AVAILABLE" and g.body["startedAt"] == "2026-12-01T11:55:00Z"
    gone = c.call("GET", f"{L3}/sessions/a1b2c3d4-0001-4000-8000-000000000010")
    assert gone.body["statusInfo"] == "NETWORK_TERMINATED" and gone.body["qosStatus"] == "UNAVAILABLE"
    # a create that clashes with a world session
    dev = int(s.device_id[1:])
    assert _create(c, dev, server=s.application_server["ipv4Address"],
                   **{k: v for k, v in (("devicePorts", s.device_ports),
                                        ("applicationServerPorts", s.application_server_ports)) if v}).status == 409
    # two identifiers: the response carries exactly one of them
    r = c.post(f"{L3}/sessions", {"device": {"phoneNumber": PHONE(5), "ipv6Address": "2001:db8:a:5::9"},
                                  "applicationServer": {"ipv4Address": "198.51.100.5"}, "qosProfile": "QOS_S",
                                  "duration": 120})
    assert r.status == 201 and r.body["device"] == {"phoneNumber": PHONE(5)}


# --- sessions, determinism, logs ------------------------------------------------------------------
def test_state_is_isolated_between_eval_sessions_and_reset():
    b = make_l3()
    a, other = Client(b, "A"), Client(b, "B")
    ra, rb = _create(a), _create(other)
    assert ra.status == rb.status == 201
    assert _create(a).status == 409 and _create(other).status == 409
    assert b.reset("A") == ["A"]
    assert _create(a).status == 201 and _create(other).status == 409


def test_identical_runs_give_identical_answers():
    def run():
        b = make_l3()
        c = Client(b, "same", clock="2026-12-02T08:00:00Z")
        r1, r2 = _create(c, 1), _create(c, 2, profile="QOS_M", duration=1200)
        return [r1.body, r2.body, c.call("GET", f"{L3}/sessions/{r1.body['sessionId']}").body]
    assert run() == run()
    ids = {Client(make_l3(), s).post(f"{L3}/sessions", {"device": {"phoneNumber": PHONE(1)},
           "applicationServer": {"ipv4Address": "198.51.100.1"}, "qosProfile": "QOS_E", "duration": 60}).body["sessionId"]
           for s in ("s1", "s2")}
    assert len(ids) == 2                  # a different eval session gives a different ID


def test_every_response_validates_and_is_logged(tmp_path, world):
    """Replays a request mix and checks `backend.jsonl` against the data contract (section 2.5 fields)."""
    run = tmp_path / "run"
    for make, calls in (
        (make_l1, [(f"{L1}/retrieve", {"device": {"phoneNumber": d.phone_number}}) for d in world.devices[:8]]),
        (make_l2, [(f"{L2}/verify", {"device": {"phoneNumber": PHONE(n)}, "area": circle(52.52, 13.41, 5000)})
                   for n in range(1, 9)]),
        (make_l3, [(f"{L3}/sessions", {"device": {"phoneNumber": PHONE(n)}, "applicationServer": {"ipv4Address": "198.51.100.9"},
                                      "qosProfile": "QOS_S", "duration": 300}) for n in range(1, 9)]),
    ):
        c = Client(make(run_dir=run))
        for path, body in calls:
            c.post(path, body)
    lines = [json.loads(x) for x in (run / "backend.jsonl").read_text().splitlines()]
    assert len(lines) == 24
    for rec in lines:
        assert {"session_id", "seq", "api", "method", "path", "request_body", "validation_ok", "status",
                "response_body", "world_effect", "clock", "response_valid", "resolved_device", "identifiers_consistent"} <= rec.keys()
        assert rec["response_valid"] is True, rec          # the backend never answers outside its specification
        assert rec["status"] != 500
    assert [r["seq"] for r in lines if r["api"] == "L3"] == list(range(1, 9))


def _spec_response_codes(spec_file: str, path: str, method: str) -> set[str]:
    spec = yaml.safe_load((ROOT / "specs" / spec_file).read_text())
    node = spec["paths"][path][method]
    out: set[str] = set()
    for status, resp in node["responses"].items():
        if "$ref" in resp:
            resp = spec["components"]["responses"][resp["$ref"].split("/")[-1]]
        for media in resp.get("content", {}).values():
            for part in media.get("schema", {}).get("allOf", []):
                if "properties" in part and "code" in part["properties"]:
                    out |= {f"{status}:{c}" for c in part["properties"]["code"]["enum"]}
    return out


def test_error_codes_are_in_the_specifications():
    """Every error code the handlers can return exists in the pinned spec for that operation."""
    allowed = {
        "L1": _spec_response_codes("L1/v1.0.0.yaml", "/retrieve", "post"),
        "L2": _spec_response_codes("L2/v3.0.0.yaml", "/verify", "post"),
        "L3": _spec_response_codes("L3/v1.1.0.yaml", "/sessions", "post"),
    }
    used = {
        "L1": {"400:INVALID_ARGUMENT", "422:MISSING_IDENTIFIER", "422:UNSUPPORTED_IDENTIFIER", "404:IDENTIFIER_NOT_FOUND", "422:IDENTIFIER_MISMATCH"},
        "L2": {"400:INVALID_ARGUMENT", "400:OUT_OF_RANGE", "422:MISSING_IDENTIFIER", "422:UNSUPPORTED_IDENTIFIER",
               "404:IDENTIFIER_NOT_FOUND", "422:LOCATION_VERIFICATION.INVALID_AREA",
               "422:LOCATION_VERIFICATION.AREA_NOT_COVERED", "422:LOCATION_VERIFICATION.UNABLE_TO_LOCATE",
               "422:LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE"},
        "L3": {"400:INVALID_ARGUMENT", "400:OUT_OF_RANGE", "400:QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE",
               "400:INVALID_CREDENTIAL", "400:INVALID_TOKEN", "400:INVALID_SINK", "404:IDENTIFIER_NOT_FOUND",
               "404:NOT_FOUND", "409:CONFLICT", "422:MISSING_IDENTIFIER", "422:UNSUPPORTED_IDENTIFIER",
               "422:QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE"},
    }
    for api in used:
        assert used[api] <= allowed[api], (api, used[api] - allowed[api])


def test_stage_04b_identifier_mismatches_and_fields(tmp_path, world):
    # Setup backends with logging run_dir
    run = tmp_path / "run"
    b_l1 = make_l1(world, run_dir=run)
    b_l2 = make_l2(world, run_dir=run)
    b_l3 = make_l3(world, run_dir=run)

    d1 = world.device("D01")
    d2 = world.device("D02")

    # 1. L1 with two identifiers of different devices gives 422 IDENTIFIER_MISMATCH
    headers = {"X-Eval-Session": "s1"}
    body_mismatched = {
        "device": {
            "phoneNumber": d1.phone_number,
            "ipv6Address": d2.ipv6_address
        }
    }
    res_l1_mismatched, info_l1_mismatched = b_l1.handle("POST", f"{L1}/retrieve", "http://127.0.0.1:1", headers, json.dumps(body_mismatched).encode())
    assert res_l1_mismatched.status == 422
    assert res_l1_mismatched.body["code"] == "IDENTIFIER_MISMATCH"
    assert info_l1_mismatched["resolved_device"] == "D01"
    assert info_l1_mismatched["identifiers_consistent"] is False

    # 2. L1 with two identifiers of the same device succeeds
    body_consistent = {
        "device": {
            "phoneNumber": d1.phone_number,
            "ipv6Address": d1.ipv6_address
        }
    }
    res_l1_consistent, info_l1_consistent = b_l1.handle("POST", f"{L1}/retrieve", "http://127.0.0.1:1", headers, json.dumps(body_consistent).encode())
    assert res_l1_consistent.status == 200
    assert info_l1_consistent["resolved_device"] == "D01"
    assert info_l1_consistent["identifiers_consistent"] is True

    # 3. L2 and L3 with mismatched identifiers use the first, and log identifiers_consistent: false
    # L2 mismatched
    body_l2_mismatched = {
        "device": {
            "phoneNumber": d1.phone_number,
            "ipv6Address": d2.ipv6_address
        },
        "area": circle(d1.location.latitude, d1.location.longitude, 5000) if d1.location else circle(52.52, 13.41, 5000)
    }
    res_l2, info_l2 = b_l2.handle("POST", f"{L2}/verify", "http://127.0.0.1:1", headers, json.dumps(body_l2_mismatched).encode())
    assert res_l2.status == 200
    assert info_l2["resolved_device"] == "D01"
    assert info_l2["identifiers_consistent"] is False

    # L3 mismatched
    body_l3_mismatched = {
        "device": {
            "phoneNumber": d1.phone_number,
            "ipv6Address": d2.ipv6_address
        },
        "applicationServer": {"ipv4Address": "198.51.100.9"},
        "qosProfile": "QOS_S",
        "duration": 300
    }
    res_l3, info_l3 = b_l3.handle("POST", f"{L3}/sessions", "http://127.0.0.1:1", headers, json.dumps(body_l3_mismatched).encode())
    assert res_l3.status == 201
    assert info_l3["resolved_device"] == "D01"
    assert info_l3["identifiers_consistent"] is False

    # Read backend.jsonl to verify log lines
    lines = [json.loads(x) for x in (run / "backend.jsonl").read_text().splitlines()]
    assert len(lines) == 4
    for line in lines:
        assert "resolved_device" in line
        assert "identifiers_consistent" in line
        # verify fields on L2/L3 mismatched
        if line["api"] == "L2":
            assert line["resolved_device"] == "D01"
            assert line["identifiers_consistent"] is False
        elif line["api"] == "L3":
            assert line["resolved_device"] == "D01"
            assert line["identifiers_consistent"] is False


# --- real processes -------------------------------------------------------------------------------
def test_launcher_http(tmp_path, monkeypatch):
    # 08a E12: use a state file of its own, so that a state file left by an earlier run or test (or running
    # backends) can neither make the test skip or fail nor be touched by it.
    monkeypatch.setattr(launcher, "STATE_FILE", tmp_path / "state.json")
    try:
        procs = launcher.up("127.0.0.1", 19400, tmp_path)
        l1, l2, l3 = (procs[a]["url"] for a in ("L1", "L2", "L3"))
        h = httpx.get(l3 + "/__admin/health").json()
        assert h["api"] == "L3" and h["world_hash"] == World().hash
        r = httpx.post(l1 + f"{L1}/retrieve", json={"device": {"phoneNumber": PHONE(1)}},
                       headers={"X-Eval-Session": "http1", "x-correlator": "abc-1"})
        assert r.status_code == 200 and r.headers["x-correlator"] == "abc-1" and r.json()["reachable"] is True
        body = {"device": {"phoneNumber": PHONE(1)}, "applicationServer": {"ipv4Address": "198.51.100.3"},
                "qosProfile": "QOS_E", "duration": 600}
        hdr = {"X-Eval-Session": "http1"}
        c = httpx.post(l3 + f"{L3}/sessions", json=body, headers=hdr)
        assert c.status_code == 201
        assert httpx.delete(l3 + f"{L3}/sessions/{c.json()['sessionId']}", headers=hdr).status_code == 204
        assert httpx.get(l3 + "/__admin/state", params={"session": "http1"}).json()["deleted"]
        assert httpx.post(l3 + "/__admin/reset", params={"session": "http1"}).json() == {"reset": ["http1"]}
        assert httpx.post(l2 + f"{L2}/verify", content=b"{bad", headers={"content-type": "application/json"}).status_code == 400
    finally:
        launcher.down()
    lines = [json.loads(x) for x in (tmp_path / "backend.jsonl").read_text().splitlines()]
    assert {r["api"] for r in lines} == {"L1", "L2", "L3"}
    assert not launcher.status()


def test_profile_table_and_backend_agree_on_every_profile(world):
    """For each profile in the table: the backend accepts the table's max duration if ACTIVE,
    refuses max + 1 with DURATION_OUT_OF_RANGE, and refuses INACTIVE / DEPRECATED ones as not applicable."""
    table = {row.split(" | ")[0]: row.split(" | ") for row in render_profile_table(world).splitlines()[1:]}
    for i, p in enumerate(world.profiles.values(), start=1):
        assert table[p.name][1] == p.status
        c = Client(make_l3(), session=f"prof{i}")
        if p.status == "ACTIVE":
            assert _create(c, 1, p.name, p.max_duration_s).status == 201
            c2 = Client(make_l3(), session=f"prof{i}b")
            assert _create(c2, 1, p.name, p.max_duration_s + 1).body["code"] == "QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE"
            assert _create(c2, 1, p.name, p.min_duration_s - 1).body["code"] == "QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE"
        else:
            assert _create(c, 1, p.name, p.min_duration_s).body["code"] == "QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE"
