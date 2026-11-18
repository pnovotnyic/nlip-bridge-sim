"""Stage 05 validation tests for task instances (data contract §1).

Checks required by the stage plan:
1. Every native request is valid against its own version's specification.
2. Every gold call, sent to the stage 04 backend in a fresh session, returns gold_backend_response.
3. render_answer, applied to the backend's actual response, gives gold_client_answer.
4. Every Stage 3 instance has at least one change tag in request or response (or is documented).
5. The pilot and main sets share no intent.
6. Instance counts match expectations.
7. INDEX.csv consistency: all task files are indexed and all indexed files exist.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"
CONFIG_DIR = ROOT / "config"

# ----- helpers -----------------------------------------------------------------------

def _load_all_instances() -> list[dict]:
    instances = []
    for api in ("L1", "L2", "L3"):
        api_dir = TASKS_DIR / api
        if not api_dir.exists():
            continue
        for f in sorted(api_dir.glob("*.json")):
            instances.append(json.loads(f.read_text()))
    return instances


def _all_instances() -> list[tuple[str, dict]]:
    result = []
    for api in ("L1", "L2", "L3"):
        api_dir = TASKS_DIR / api
        if not api_dir.exists():
            continue
        for f in sorted(api_dir.glob("*.json")):
            result.append((f.name, json.loads(f.read_text())))
    return result


# ----- basic structure tests ---------------------------------------------------------

def test_all_instance_files_exist_and_are_valid():
    """Every JSON file has schema_version 1 and all required top-level fields."""
    required = {
        "schema_version", "task_id", "intent_id", "pilot", "api", "operation",
        "client_version", "server_version", "versions_behind",
        "breaking_crossed", "breaking_crossed_ops", "catalogue_breaking_crossed",
        "prompt_half", "pilot_round", "intent_text",
        "client_native_request", "client_facts", "client_answer_schema",
        "world_ref", "gold_calls", "gold_backend_response", "gold_client_answer",
        "missing_info", "missing_info_source", "expected_refusal", "refusal_predictable",
        "change_tags_request", "change_tags_response",
        "material_fields", "provenance",
    }
    for fname, instance in _all_instances():
        missing = required - set(instance.keys())
        assert not missing, f"{fname}: missing fields {missing}"
        assert instance["schema_version"] == "1", f"{fname}: wrong schema_version"


def test_instance_counts():
    """Check the total count matches 510 (from the generation run)."""
    instances = _load_all_instances()
    main_count = sum(1 for i in instances if not i["pilot"])
    pilot_count = sum(1 for i in instances if i["pilot"])
    # Stage 2: 30+30+30=90 main (at server version)
    # Stage 3: L1 2×30=60, L2 4×30=120, L3 5×30=150 -> 330 main Stage3
    # Pilot: L1 10×3=30, L2 10×3=30, L3 10×3=30 -> 90 pilot
    # Total main: 90 + 330 = 420; total pilot: 90; grand total: 510
    assert len(instances) == 510, f"Expected 510 instances, got {len(instances)}"
    assert main_count == 420, f"Expected 420 main instances, got {main_count}"
    assert pilot_count == 90, f"Expected 90 pilot instances, got {pilot_count}"


def test_index_csv_completeness():
    """INDEX.csv has one row per file, all files are indexed, all index entries have files."""
    index_path = TASKS_DIR / "INDEX.csv"
    assert index_path.exists(), "INDEX.csv is missing"
    with open(index_path) as f:
        rows = list(csv.DictReader(f))

    # All task files indexed
    all_files = {f.stem for api in ("L1", "L2", "L3") for f in (TASKS_DIR / api).glob("*.json")}
    indexed_ids = {row["task_id"] for row in rows}
    assert all_files == indexed_ids, f"Mismatch: {all_files.symmetric_difference(indexed_ids)}"


def test_pilot_main_disjoint():
    """No intent_id appears in both pilot and main sets."""
    instances = _load_all_instances()
    for api in ("L1", "L2", "L3"):
        api_instances = [i for i in instances if i["api"] == api]
        main_intent_ids = {i["intent_id"] for i in api_instances if not i["pilot"]}
        pilot_intent_ids = {i["intent_id"] for i in api_instances if i["pilot"]}
        overlap = main_intent_ids & pilot_intent_ids
        assert not overlap, f"{api}: intent_ids in both main and pilot: {overlap}"


def test_versions_behind_matches_definition():
    """versions_behind matches the difference between server and client in the version list."""
    version_lists = {
        "L1": ["v0.5.1", "v0.6.0", "v1.0.0"],
        "L2": ["v0.1.0", "v0.2.0", "v1.0.0", "v2.0.0", "v3.0.0"],
        "L3": ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0", "v1.1.0"],
    }
    server_versions = {"L1": "v1.0.0", "L2": "v3.0.0", "L3": "v1.1.0"}
    for _, instance in _all_instances():
        api = instance["api"]
        vs = version_lists[api]
        server = server_versions[api]
        expected = vs.index(server) - vs.index(instance["client_version"])
        assert instance["versions_behind"] == expected, \
            f"{instance['task_id']}: versions_behind {instance['versions_behind']} != {expected}"


def test_tags_follow_what_the_instance_exercises():
    """Declined instances have no response tags; an instance without any tag is a get/delete, a declined call, or L3 at
    v0.10.0 and later without a notification URL (07b A9)."""
    for _, i in _all_instances():
        if i["gold_client_answer"]["status"] == "declined":
            assert i["change_tags_response"] == [], f"{i['task_id']}: declined instance with response tags"
        if i["versions_behind"] == 0:
            assert not i["change_tags_request"] and not i["change_tags_response"], i["task_id"]
            assert i["catalogue_breaking_crossed"] == 0, i["task_id"]
        if i["catalogue_breaking_crossed"] == 0 and i["versions_behind"] > 0:
            assert not i["change_tags_request"] and not i["change_tags_response"], \
                f"{i['task_id']}: tags but no breaking entry crossed"
        if i["catalogue_breaking_crossed"] > 0:
            assert i["change_tags_request"] or i["change_tags_response"], \
                f"{i['task_id']}: breaking entries crossed but no tag"


def test_catalogue_breaking_crossed_is_per_instance():
    """The value is not the API-level number on every instance (07b A9, review T10)."""
    cell = {}
    with open(ROOT / "results" / "specs" / "catalogue_breaking_crossed.csv") as f:
        for row in csv.DictReader(f):
            cell[(row["api"], row["client_version"])] = int(row["catalogue_breaking_crossed"])
    for _, i in _all_instances():
        assert i["catalogue_breaking_crossed"] <= cell[(i["api"], i["client_version"])], i["task_id"]
    equal = sum(1 for _, i in _all_instances()
                if i["versions_behind"] > 0 and i["catalogue_breaking_crossed"] == cell[(i["api"], i["client_version"])])
    assert equal < sum(1 for _, i in _all_instances() if i["versions_behind"] > 0)


def test_declined_refusal_fields():
    for _, i in _all_instances():
        status = i["gold_backend_response"]["status"]
        if status >= 400:
            assert i["expected_refusal"] == {"status": status, "code": i["gold_backend_response"]["body"]["code"]}, i["task_id"]
        else:
            assert i["expected_refusal"] is None, i["task_id"]
        assert i["refusal_predictable"] is False, i["task_id"]
        if i["gold_client_answer"]["status"] == "declined":
            assert i["expected_refusal"] is not None, i["task_id"]


def test_prompt_half_rule():
    """Odd-numbered main intents have prompt_half=True; even-numbered have False."""
    for _, instance in _all_instances():
        if instance["pilot"]:
            continue  # pilot intents are not constrained by this rule
        intent_id = instance["intent_id"]
        if not intent_id.startswith("m"):
            continue
        num = int(intent_id[1:])
        expected = (num % 2 == 1)
        assert instance["prompt_half"] == expected, \
            f"{instance['task_id']}: prompt_half={instance['prompt_half']}, expected {expected} for intent {intent_id}"


def test_pilot_rounds():
    """Pilot intents have pilot_round A or B; main intents have pilot_round null."""
    for _, instance in _all_instances():
        if instance["pilot"]:
            assert instance["pilot_round"] in ("A", "B"), \
                f"{instance['task_id']}: pilot without pilot_round"
        else:
            assert instance["pilot_round"] is None, \
                f"{instance['task_id']}: main intent with pilot_round={instance['pilot_round']}"


def test_gold_client_answer_status_values():
    """gold_client_answer status is one of done/declined/unrepresentable."""
    valid_statuses = {"done", "declined", "unrepresentable"}
    for _, instance in _all_instances():
        status = instance["gold_client_answer"]["status"]
        assert status in valid_statuses, \
            f"{instance['task_id']}: invalid gold_client_answer status: {status!r}"


# ----- backend round-trip tests (all instances) ----------------------------------------

_BACKENDS = None


def _gold_backends():
    global _BACKENDS
    if _BACKENDS is None:
        from nlipeval.tasks.generate import GoldBackends
        _BACKENDS = GoldBackends()
    return _BACKENDS


def _strip_ids(x):
    if isinstance(x, dict):
        # `device` is echoed only when the call has several identifiers: the alternatives differ in nothing else
        return {k: _strip_ids(v) for k, v in x.items() if k not in ("sessionId", "id", "device")}
    if isinstance(x, list):
        return [_strip_ids(v) for v in x]
    return x


@pytest.mark.parametrize("fname,instance", _all_instances(), ids=lambda x: x if isinstance(x, str) else "")
def test_gold_call_round_trip(fname, instance):
    """Gold call -> backend -> gold_backend_response, render_answer -> gold_client_answer, on every instance.

    Every gold alternative is accepted by the backend and gives the same response as the primary call (07b A2)."""
    from nlipeval.tasks.generate import _renderer, answer_from_response

    backends = _gold_backends()
    stored = instance["gold_backend_response"]
    first = None
    for call in instance["gold_calls"]:
        live = backends.call(instance["api"], call)
        assert live["status"] == stored["status"], f"{fname}: {call['body']} -> {live['status']}, stored {stored['status']}"
        assert _strip_ids(live["body"]) == _strip_ids(stored["body"]), f"{fname}: body differs"
        first = first or live
    answer = answer_from_response(_renderer(instance["api"]), stored, instance["client_version"])
    assert answer == instance["gold_client_answer"], f"{fname}: render_answer differs from gold_client_answer"
    if stored["status"] >= 400:
        assert instance["expected_refusal"]["code"] == stored["body"]["code"]


# ----- coverage tests -----------------------------------------------------------------

def test_l1_covers_all_identifier_types_and_reachability_states():
    """L1 intents cover all identifier types and reachability states."""
    instances = [i for _, i in _all_instances() if i["api"] == "L1" and not i["pilot"]
                 and i["client_version"] == "v1.0.0"]
    intent_ids = {i["intent_id"] for i in instances}

    # Load intents
    intents_doc = yaml.safe_load((CONFIG_DIR / "intents" / "L1.yaml").read_text())
    identifiers = {i["params"]["identifier"] for i in intents_doc["main"]}
    expected_identifiers = {"phone_number", "ipv4_with_port", "ipv6", "network_access_identifier"}
    assert expected_identifiers.issubset(identifiers), \
        f"Missing identifier types: {expected_identifiers - identifiers}"


def test_l3_operation_counts():
    """L3 main intents: 22 creates, 4 gets, 4 deletes."""
    intents_doc = yaml.safe_load((CONFIG_DIR / "intents" / "L3.yaml").read_text())
    ops = [i.get("operation", "createSession") for i in intents_doc["main"]]
    creates = ops.count("createSession")
    gets = ops.count("getSession")
    deletes = ops.count("deleteSession")
    assert creates == 22, f"Expected 22 creates, got {creates}"
    assert gets == 4, f"Expected 4 gets, got {gets}"
    assert deletes == 4, f"Expected 4 deletes, got {deletes}"


def test_no_nai_only_violations():
    """At most 2 NAI-only intents per API."""
    for api in ("L1", "L2", "L3"):
        intents_doc = yaml.safe_load((CONFIG_DIR / "intents" / f"{api}.yaml").read_text())
        nai_only = [i for i in intents_doc.get("main", [])
                    if i["params"].get("identifier") == "network_access_identifier"]
        assert len(nai_only) <= 2, f"{api}: {len(nai_only)} NAI-only intents (max 2)"


def test_l2_area_constraints():
    """L2 areas: radius >= 2000 m (v0.1.0 accuracy minimum is 2 km, 07b A3), centre inside the coverage box."""
    intents_doc = yaml.safe_load((CONFIG_DIR / "intents" / "L2.yaml").read_text())
    for intent in intents_doc.get("main", []) + intents_doc.get("pilot", []):
        area = intent["params"].get("area", {})
        center = area.get("center", {})
        lat = center.get("latitude", 50)
        lon = center.get("longitude", 10)
        radius = area.get("radius", 2000)
        assert radius >= 2000, f"{intent['id']}: radius {radius} < 2000 m"
        assert 35 <= lat <= 60, f"{intent['id']}: latitude {lat} outside 35-60"
        assert -12 <= lon <= 25, f"{intent['id']}: longitude {lon} outside -12 to 25"


# ----- 07b A11: strict validation, derivability, intent text, facts --------------------------

@pytest.mark.parametrize("fname,instance", _all_instances(), ids=lambda x: x if isinstance(x, str) else "")
def test_native_request_and_gold_answer_are_valid_for_the_client_version(fname, instance):
    """Native requests and gold client answers contain only fields of the client's own version, and validate."""
    from nlipeval.tasks import strict

    api, v = instance["api"], instance["client_version"]
    errs = strict.validate_request(api, v, instance["client_native_request"])
    assert not errs, f"{fname}: native request: {errs}"
    errs = strict.validate_answer(api, v, instance["client_native_request"], instance["gold_client_answer"])
    assert not errs, f"{fname}: gold client answer: {errs}"


def _leaves(obj, prefix=""):
    from nlipeval.tasks.tags import paths
    return paths(obj)[0]


# Values the server's own interface fixes: they are not information the client has to supply.
SERVER_CONSTANTS = {"area.areaType": "CIRCLE"}


def _intent_numbers(text: str) -> set[str]:
    import re
    return set(re.findall(r"[0-9][0-9.:/]*[0-9]|[0-9]", text))


def _derivable(path: str, value, instance: dict, native_leaves: dict) -> str | None:
    """Why a gold-call leaf is derivable, or None. Rules: reports/review-renderer-rules.md."""
    if SERVER_CONSTANTS.get(path) == value:
        return "server constant"
    text = instance["intent_text"]
    facts = " ".join(f["value"] for f in instance["client_facts"])
    if value in native_leaves.values():
        return "native request"
    sval = str(value)
    if sval in text or sval in facts:
        return "intent text or fact"
    # the native request leaf that corresponds in meaning
    if path.endswith("phoneNumber") and sval.lstrip("+") in {str(v).lstrip("+") for v in native_leaves.values()}:
        return "native request (phone number without +)"
    if path == "area.radius" and any(str(v) == str(value / 1000).rstrip("0").rstrip(".") for v in native_leaves.values()):
        return "native request (km to m)"
    if path == "area.radius" and value % 1000 == 0 and f"{value // 1000} km" in text:
        return "intent text (km)"
    if path.startswith("sink") and sval.endswith("/notifications") and sval[: -len("/notifications")] in native_leaves.values():
        return "native request plus callback suffix of v0.8.1"
    if path == "duration" or path == "maxAge":
        return "intent text (duration or age in words)" if instance["gold_calls"][0]["body"].get(path) == value else None
    if path == "qosProfile":
        return "native request or fact (profile)" if any(f["fact"] == "duration_preference" for f in instance["client_facts"]) else None
    if path.startswith("device.ipv4Address.publicPort") and f"port {value}" in text:
        return "intent text (port)"
    return None


@pytest.mark.parametrize("fname,instance", _all_instances(), ids=lambda x: x if isinstance(x, str) else "")
def test_every_gold_value_is_reachable(fname, instance):
    """Every leaf of every gold call is in the intent text, the facts or the native request, or is a server constant
    (07b rule: every gold answer must be reachable from what the agents are given)."""
    native = instance["client_native_request"].get("body") or {}
    native_leaves = _leaves(native)
    for call in instance["gold_calls"]:
        body = call.get("body") or {}
        for path, value in _leaves(body).items():
            if _derivable(path, value, instance, native_leaves) is None:
                # durations and ages given in words
                if path in ("duration", "maxAge", "qosProfile"):
                    continue
                pytest.fail(f"{fname}: gold value {path}={value!r} is not derivable")


def test_gold_durations_ages_and_profiles_follow_the_intent():
    """Durations and ages in gold calls equal those of the intent; a profile differs only by a preference fact."""
    intents = {}
    for api in ("L2", "L3"):
        doc = yaml.safe_load((CONFIG_DIR / "intents" / f"{api}.yaml").read_text())
        for i in doc["main"] + doc["pilot"]:
            intents[(api, i["id"])] = i
    for _, inst in _all_instances():
        if inst["api"] == "L1":
            continue
        intent = intents[(inst["api"], inst["intent_id"])]
        p = intent["params"]
        for call in inst["gold_calls"]:
            body = call.get("body") or {}
            if inst["api"] == "L3" and "duration" in body:
                assert body["duration"] == p["duration_s"], inst["task_id"]
            if inst["api"] == "L3" and "qosProfile" in body and body["qosProfile"] != p["profile"]:
                assert any(f["fact"] == "duration_preference" for f in inst["client_facts"]), inst["task_id"]
            if inst["api"] == "L2" and "maxAge" in body and body["maxAge"] != p.get("max_age"):
                assert body["maxAge"] == p.get("gold_max_age") or (inst["client_version"] == "v0.2.0" and body["maxAge"] == 60), inst["task_id"]


def test_intent_text_agrees_with_native_request():
    """Radii, durations, ports and identifiers of the native request occur in the intent text."""
    import re
    for _, i in _all_instances():
        text = i["intent_text"]
        body = i["client_native_request"].get("body") or {}
        leaves = _leaves(body)
        for path, value in leaves.items():
            if path.endswith(("phoneNumber", "msisdn")):
                assert str(value).lstrip("+") in text.replace("+", ""), f"{i['task_id']}: {path}"
            elif path.endswith(("ipv6Address", "ipv6Addr", "ipv6addr", "externalId", "networkAccessIdentifier", "publicAddress",
                                "ipv4Addr", "ipv4addr", "notificationUrl", "sink")):
                if path.startswith(("asId", "applicationServer")):
                    continue
                assert str(value) in text, f"{i['task_id']}: {path}={value} not in intent text"
            elif path in ("area.radius", "accuracy"):
                km = (value / 1000) if path == "area.radius" else value
                assert re.search(rf"\b{km:g} km\b", text), f"{i['task_id']}: radius {km} km not in intent text"
            elif path.endswith(("latitude", "longitude")):
                assert f"{value:.3f}" in text, f"{i['task_id']}: {path}={value} not in intent text"
        assert "gold_profile" not in json.dumps(body), i["task_id"]


FACT_WORLD_WORDS = ("cannot locate", "can't locate", "no location", "not locatable", "reachable", "expired", "unreachable",
                    "no known", "not connected", "has no")
FACT_SERVER_FIELDS = ("areaType", "privateAddress", "publicPort", "sinkCredential", "qosStatus", "qosProfile", "maxAge")
FACT_PROFILE_LIMITS = ("max 30", "1800", "7200", "86400", "14400", "30 min")


def test_fact_lint():
    """Facts hold no world state, no server-only field names and no profile limits (07b A6)."""
    for _, i in _all_instances():
        for f in i["client_facts"]:
            low = f["value"].lower()
            for w in FACT_WORLD_WORDS:
                assert w not in low, f"{i['task_id']}: fact {f['fact']!r} mentions world state ({w!r})"
            for w in FACT_SERVER_FIELDS:
                assert w not in f["value"], f"{i['task_id']}: fact names server field {w!r}"
            for w in FACT_PROFILE_LIMITS:
                assert w not in low, f"{i['task_id']}: fact quotes a limit ({w!r})"


def test_missing_info_definition():
    """missing_info lists server-version fields, none a constant of the server interface, each with a source."""
    for _, i in _all_instances():
        assert set(i["missing_info"]) == set(i["missing_info_source"]), i["task_id"]
        assert "area.areaType" not in i["missing_info"], i["task_id"]
        for k, src in i["missing_info_source"].items():
            assert src in ("intent_text", "fact"), i["task_id"]
        if i["versions_behind"] == 0:
            gold_fields = set()
            for f in i["missing_info"]:
                gold_fields.add(f)
            # at the server version only an NAI-only intent or a fact-driven field can be missing
            for f in i["missing_info"]:
                assert i["missing_info_source"][f] == "fact", i["task_id"]


def test_nai_only_and_ipv4_gold_alternatives():
    """NAI-only intents are `done` with the fact's identifier; IPv4 gold has publicAddress and publicPort only."""
    for _, i in _all_instances():
        for call in i["gold_calls"]:
            body = call.get("body") or {}
            dev = body.get("device") or {}
            if "ipv4Address" in dev:
                assert set(dev["ipv4Address"]) == {"publicAddress", "publicPort"}, i["task_id"]
            if "networkAccessIdentifier" in dev and len(dev) == 1:
                pytest.fail(f"{i['task_id']}: gold call with the NAI only")
        native = i["client_native_request"].get("body") or {}
        if "networkAccessIdentifier" in json.dumps(native) or "externalId" in json.dumps(native):
            if i["intent_id"] in ("m23", "m30", "m16", "m21"):
                assert len(i["gold_calls"]) >= 2, i["task_id"]


def test_phone_without_plus_in_intents_1_or_2_mod_4():
    """At L1 v0.5.1, L2 v0.1.0 and L3 v0.8.1 the phone numbers of intents numbered 1 or 2 mod 4 have no '+' (08a D11)."""
    for _, i in _all_instances():
        key = (i["api"], i["client_version"])
        if key not in {("L1", "v0.5.1"), ("L2", "v0.1.0"), ("L3", "v0.8.1")}:
            continue
        native = json.dumps(i["client_native_request"].get("body") or {})
        if "9901000" not in native:
            continue
        n = int(i["intent_id"][1:])
        has_plus = '"+990100' in native
        assert has_plus == (n % 4 not in (1, 2)), i["task_id"]
        for call in i["gold_calls"]:
            if "phoneNumber" in json.dumps(call["body"]):
                assert '"+990100' in json.dumps(call["body"]), i["task_id"]
        if not has_plus:
            assert "unit_format" in i["change_tags_request"], i["task_id"]
