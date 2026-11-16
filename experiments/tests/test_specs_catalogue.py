import csv
from pathlib import Path

import pytest
import yaml

from nlipeval.tasks import changes
from nlipeval.tasks.specs import SPECS, VERSIONS

ROOT = Path(__file__).resolve().parents[1]

# Counts from the earlier run with the same tool (plan, stage 02 sanity check)
EARLIER_ERR = {"L1": [6, 2], "L2": [7, 0, 1, 0], "L3": [4, 2, 10, 5, 0]}


def _rows(name):
    with open(ROOT / "results" / "specs" / name) as f:
        return list(csv.DictReader(f))


def test_manifest_covers_all_pinned_files():
    m = yaml.safe_load((SPECS / "MANIFEST.yaml").read_text())
    assert len(m["files"]) == 15  # 14 versions + qos-profiles v1.1.0
    for f in m["files"]:
        assert (SPECS / f["file"]).exists()
        assert len(f["commit_sha"]) == 40 and len(f["sha256"]) == 64


def test_breaking_changes_match_earlier_run():
    rows = _rows("breaking_changes.csv")
    for api, expected in EARLIER_ERR.items():
        assert [int(r["breaking_err"]) for r in rows if r["api"] == api] == expected


def test_breaking_crossed_is_suffix_sum():
    steps = {}
    for r in _rows("breaking_changes.csv"):
        steps.setdefault(r["api"], []).append(int(r["breaking_err"]))
    for r in _rows("breaking_crossed.csv"):
        api, behind = r["api"], int(r["versions_behind"])
        n = len(steps[api])
        assert int(r["breaking_crossed"]) == sum(steps[api][n - behind :])
    assert {(r["api"], r["client_version"]): r["versions_behind"] for r in _rows("breaking_crossed.csv")}[("L3", "v0.8.1")] == "5"


def test_excerpt_sizes_cover_every_version():
    rows = _rows("excerpt_sizes.csv")
    have = {(r["api"], r["version"]) for r in rows}
    for api, c in VERSIONS.items():
        for v, _, _ in c["versions"]:
            assert (api, v) in have
            assert (SPECS / "excerpts" / api / f"{v}.yaml").exists()


@pytest.mark.parametrize("api", ["L1", "L2", "L3"])
def test_catalogue_complete_and_evidenced(api):
    doc = yaml.safe_load((SPECS / "changes" / f"{api}.yaml").read_text())
    assert doc["status"] == "reviewed" and doc["reviewed"]
    assert "interpretation changed" in doc["kind_definitions"]["changed_meaning"]
    assert (SPECS / "changes" / f"{api}.yaml").read_text().startswith("# `changed_meaning`: a field or value that still exists")
    assert set(doc["client_versions"]) == {v for v, _, _ in VERSIONS[api]["versions"]}
    for v, x in doc["client_versions"].items():
        assert x["entries"]
        for e in x["entries"]:
            assert e["evidence"], (api, v, e["client_path"])
            assert e["kind"] in e["kinds"]
            assert e["direction"] in ("request", "response")
        if x["versions_behind"] == 0:
            assert all(e["kind"] == "unchanged" for e in x["entries"])


def _entry(api, v, cp, direction="request"):
    (e,) = [e for e in changes.entries(api, v, direction=direction) if e["client_path"] == cp][:1]
    return e


def test_known_examples_l3():
    assert "renamed" in _entry("L3", "v0.8.1", "ueId")["kinds"] and _entry("L3", "v0.8.1", "ueId")["server_path"] == "device"
    assert _entry("L3", "v0.8.1", "asId")["server_path"] == "applicationServer"
    q = _entry("L3", "v0.8.1", "qos")
    assert q["server_path"] == "qosProfile" and "unit_format" in q["kinds"]
    assert "changed_meaning" in _entry("L3", "v0.8.1", "notificationUrl")["kinds"]
    assert _entry("L3", "v0.8.1", "notificationUrl")["server_path"] == "sink"
    assert _entry("L3", "v0.8.1", "notificationAuthToken")["server_path"] == "sinkCredential.accessToken"
    assert _entry("L3", "v0.10.0", "duration")["kind"] == "newly_required"
    assert _entry("L3", "v0.8.1", "uePorts.ranges[].from")["server_path"] == "devicePorts.ranges[].from"
    assert _entry("L3", "v0.8.1", "id", "response")["server_path"] == "sessionId"
    assert _entry("L3", "v0.10.0", "startedAt", "response")["kind"] == "unit_format"
    ipv4 = changes.entries("L3", "v0.8.1", direction="request")
    assert any(e["server_path"] == "device.ipv4Address.privateAddress" and e["kind"] == "newly_required" for e in ipv4)


def test_known_examples_l2():
    r = _entry("L2", "v0.1.0", "accuracy")
    assert r["server_path"] == "area.radius" and set(r["kinds"]) == {"restructured", "unit_format"}  # D6, D7
    assert "restructured" in _entry("L2", "v0.1.0", "latitude")["kinds"]
    vr = _entry("L2", "v0.1.0", "verificationResult", "response")
    assert "unit_format" in vr["kinds"] and "changed_meaning" in vr["kinds"]
    unk = _entry("L2", "v2.0.0", "verificationResult", "response")
    assert unk["kind"] == "unchanged"  # same field; UNKNOWN is a separate value-level entry
    assert _entry("L2", "v2.0.0", "verificationResult=UNKNOWN", "response")["kind"] == "changed_meaning"  # D6
    assert _entry("L2", "v2.0.0", "lastLocationTime", "response")["kind"] == "newly_required"
    assert _entry("L2", "v3.0.0", "lastLocationTime", "response")["kind"] == "unchanged"


def test_known_examples_l1():
    op = _entry("L1", "v0.5.1", "POST /connectivity")
    assert op["server_path"] == "POST /retrieve" and op["element"] == "operation"
    cs = _entry("L1", "v0.5.1", "connectivityStatus", "response")
    assert "renamed" in cs["kinds"] and "restructured" in cs["kinds"] and "changed_meaning" not in cs["kinds"]  # D6
    assert "CONNECTED_DATA" in cs["note"] and "NOT_CONNECTED" in cs["note"]  # fixed rule for the renderer
    assert _entry("L1", "v0.6.0", "reachabilityStatus", "response")["server_path"] == "reachable"


def test_reader_tags():
    t = changes.change_tags("L3", "v0.8.1", "createSession", ["ueId", "qos", "duration"], ["id", "startedAt"])
    assert t["request"] == ["renamed", "restructured", "unit_format", "newly_required"]
    assert t["response"] == ["renamed", "unit_format"]
    assert changes.change_tags("L3", "v1.1.0", "createSession", ["device.phoneNumber"], ["sessionId"]) == {"request": [], "response": []}
    t = changes.change_tags("L1", "v0.6.0", "retrieveReachability", ["device.phoneNumber"], ["reachabilityStatus"])
    assert t == {"request": [], "response": ["restructured"]}


def test_reader_rejects_unknown_field():
    with pytest.raises(KeyError):
        changes.change_tags("L3", "v0.8.1", "createSession", ["nosuchfield"], [])
    with pytest.raises(KeyError):
        changes.entries("L3", "v9.9.9")


def test_changed_meaning_only_where_decided():
    """D6-D8: changed_meaning remains on L3 notificationUrl and on L2 verificationResult=UNKNOWN (+ the boolean->enum change)."""
    found = {}
    for api in ("L1", "L2", "L3"):
        for v, x in yaml.safe_load((SPECS / "changes" / f"{api}.yaml").read_text())["client_versions"].items():
            for e in x["entries"]:
                if "changed_meaning" in e["kinds"]:
                    found.setdefault(api, set()).add(e["client_path"])
    assert "L1" not in found and found["L3"] == {"notificationUrl"}
    assert found["L2"] == {"verificationResult", "verificationResult=UNKNOWN"}


def test_response_side_relaxation_noted_not_tagged():
    e = _entry("L3", "v0.10.0", "startedAt", "response")
    assert e["kinds"] == ["unit_format"] and "optional" in e["note"] and "absence" in e["note"]


def test_per_operation_breaking_columns():
    rows = _rows("breaking_changes.csv")
    assert {"breaking_err_ops", "breaking_warn_ops"} <= set(rows[0])
    assert all(int(r["breaking_err_ops"]) <= int(r["breaking_err"]) for r in rows)
    l1 = [r for r in rows if r["api"] == "L1"][0]
    assert int(l1["breaking_err_ops"]) >= 1  # the filter keeps both /connectivity and /retrieve: the removed path is counted
    crossed = {(r["api"], r["client_version"]): r for r in _rows("breaking_crossed.csv")}
    assert crossed[("L3", "v0.8.1")]["breaking_crossed_ops"] == "14"


def test_prompt_excerpts_drop_examples_keep_descriptions():
    import json

    from nlipeval.tasks.specs import PROMPT_DIR

    def keys(n, acc, skip_examples=False):
        if isinstance(n, dict):
            for k, v in n.items():
                if skip_examples and k in ("example", "examples") and not isinstance(v, str | int | float | bool | type(None)):
                    continue  # descriptions inside example payloads are not spec descriptions
                acc.append(k)
                keys(v, acc, skip_examples)
        elif isinstance(n, list):
            for v in n:
                keys(v, acc, skip_examples)
        return acc

    for api, c in VERSIONS.items():
        for v, _, _ in c["versions"]:
            ref = keys(yaml.safe_load((SPECS / "excerpts" / api / f"{v}.yaml").read_text()), [], True)
            j = json.loads((PROMPT_DIR / api / f"{v}.json").read_text())
            y = yaml.safe_load((PROMPT_DIR / api / f"{v}.yaml").read_text())
            assert j == y
            new = keys(j, [])
            assert new.count("description") == ref.count("description")
            assert "examples" not in new
            assert new.count("example") <= ref.count("example")


def test_prompt_sizes_table():
    rows = _rows("prompt_excerpt_sizes.csv")
    assert set(rows[0]) == {"api", "version", "serialisation", "rung", "tokens"}
    assert {r["rung"] for r in rows} == {"R1", "R2", "R3", "R4"} and {r["serialisation"] for r in rows} == {"json", "yaml"}
    assert len(rows) == 4 * 2 * 14


def test_catalogue_breaking_crossed_csv_exists_and_valid():
    rows = _rows("catalogue_breaking_crossed.csv")
    assert len(rows) == 14  # total versions across L1, L2, L3 is 14
    for r in rows:
        assert {"api", "client_version", "versions_behind", "catalogue_breaking_crossed",
                "catalogue_breaking_request", "catalogue_breaking_response"} <= set(r)
        
        # Test that the server versions give 0
        if r["versions_behind"] == "0":
            assert int(r["catalogue_breaking_crossed"]) == 0
            assert int(r["catalogue_breaking_request"]) == 0
            assert int(r["catalogue_breaking_response"]) == 0
            
    # Test L1 v0.5.1 counts are correct
    l1_051 = [r for r in rows if r["api"] == "L1" and r["client_version"] == "v0.5.1"][0]
    assert int(l1_051["catalogue_breaking_crossed"]) == 4
    assert int(l1_051["catalogue_breaking_request"]) == 2
    assert int(l1_051["catalogue_breaking_response"]) == 2


def test_catalogue_breaking_counts_direct_function():
    # server version gives 0
    assert changes.catalogue_breaking_counts("L1", "v1.0.0") == (0, 0, 0)
    assert changes.catalogue_breaking_counts("L2", "v3.0.0") == (0, 0, 0)
    assert changes.catalogue_breaking_counts("L3", "v1.1.0") == (0, 0, 0)
    
    # L1 v0.5.1 counts are correct
    assert changes.catalogue_breaking_counts("L1", "v0.5.1") == (4, 2, 2)
