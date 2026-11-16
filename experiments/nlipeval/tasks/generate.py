"""Stage 05: generate task instances.

For each intent (L1, L2, L3) × each relevant client version, produce one task instance JSON
at tasks/<api>/<task_id>.json and write tasks/INDEX.csv.

Usage:
    uv run python -m nlipeval.tasks.generate [--api L1] [--dry-run]

The generator calls the stage 04 backends directly (no HTTP) to obtain gold_backend_response
and then passes the response body through the render_answer() function.

Data contract: §1 of bob_plan/data-contract.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
CONFIG_DIR = ROOT / "config"
SPECS_DIR = ROOT / "specs"
RESULTS_DIR = ROOT / "results" / "tasks"


# --- Version tables -----------------------------------------------------------------------

VERSIONS: dict[str, dict] = {
    "L1": {
        "server": "v1.0.0",
        "client_versions": ["v0.5.1", "v0.6.0", "v1.0.0"],
        "stage3_versions": ["v0.5.1", "v0.6.0"],
    },
    "L2": {
        "server": "v3.0.0",
        "client_versions": ["v0.1.0", "v0.2.0", "v1.0.0", "v2.0.0", "v3.0.0"],
        "stage3_versions": ["v0.1.0", "v0.2.0", "v1.0.0", "v2.0.0"],
    },
    "L3": {
        "server": "v1.1.0",
        "client_versions": ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0", "v1.1.0"],
        "stage3_versions": ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0"],
    },
}

# breaking_crossed and breaking_crossed_ops per (api, client_version) from results/specs/ (API-level, stage 04b)
def _load_breaking_crossed() -> dict[tuple[str, str], tuple[int, int]]:
    path = ROOT / "results" / "specs" / "breaking_crossed.csv"
    out: dict[tuple[str, str], tuple[int, int]] = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            out[(row["api"], row["client_version"])] = (
                int(row["breaking_crossed"]), int(row["breaking_crossed_ops"]))
    return out


# --- Backend invocation -------------------------------------------------------------------

class GoldBackends:
    """One backend per API for the whole generation; every call gets its own eval session (no leaking state)."""

    def __init__(self) -> None:
        from nlipeval.backends import l1_reachability, l2_location, l3_qod
        self._backends = {
            "L1": l1_reachability.make_backend(),
            "L2": l2_location.make_backend(),
            "L3": l3_qod.make_backend(),
        }
        self._n = 0

    def call(self, api: str, request: dict[str, Any]) -> dict[str, Any]:
        self._n += 1
        body = request.get("body")
        raw = json.dumps(body).encode() if body is not None else b""
        headers = {"content-type": "application/json", "x-eval-session": f"gold-{self._n}"}
        result, _ = self._backends[api].handle(request["method"], request["path"], "http://localhost", headers, raw)
        return {"status": result.status, "body": result.body}


def answer_from_response(renderer, response: dict[str, Any], client_version: str) -> dict[str, Any]:
    """The client's answer to a backend response: an error body, an empty body (204) or a success body."""
    body = response["body"]
    if response["status"] >= 400:
        return renderer.render_answer(body or {"code": "ERROR"}, client_version)
    return renderer.render_answer(body or None, client_version)


def _renderer(api: str):
    from nlipeval.tasks.render import l1, l2, l3
    return {"L1": l1, "L2": l2, "L3": l3}[api]


# --- Missing info (07b A7) ----------------------------------------------------------------

def _missing_info(api: str, client_version: str, intent: dict) -> tuple[list[str], dict[str, str]]:
    """Server-version fields that are needed, absent from the native request, and not derivable from it.

    Constants fixed by the server interface (`area.areaType`) are excluded. Each field carries the place where the
    client has the value: the intent text or a client fact.
    """
    from nlipeval.tasks.render import ids

    p = intent["params"]
    missing: dict[str, str] = {}
    op = intent.get("operation", "")
    # the second identifier of an NAI-only intent
    field = ids.gold_device_field(intent)
    if field is not None:
        missing[field] = "fact"
    # IPv4: v0.8.1 carries the address but cannot carry the port
    if api == "L3" and client_version == "v0.8.1" and p.get("identifier") == "ipv4_with_port":
        missing["device.ipv4Address.publicPort"] = "intent_text"
    if api == "L2":
        if "gold_max_age" in p:
            missing["maxAge"] = "fact"
        elif client_version == "v0.1.0" and p.get("max_age") is not None:
            missing["maxAge"] = "intent_text"
    if api == "L3" and op == "createSession" and "gold_profile" in p:
        missing["qosProfile"] = "fact"
    return list(missing), missing


# --- Material fields ----------------------------------------------------------------------

MATERIAL_FIELDS: dict[str, list[str]] = {
    "L1": ["device"],
    "L2": ["device", "area.center.latitude", "area.center.longitude", "area.radius", "maxAge"],
    "L3": ["operation", "sessionId", "device", "applicationServer", "qosProfile", "duration"],
}


# --- Main generator -----------------------------------------------------------------------

def _load_answer_schema(api: str, version: str, operation: str | None = None) -> dict:
    """Load the client_answer_schema for a given API version."""
    path = CONFIG_DIR / "answer_schemas" / f"{api}.yaml"
    doc = yaml.safe_load(path.read_text())
    schemas = doc["schemas"]
    if api == "L3":
        op = operation or "createSession"
        v_schemas = schemas.get(version, {})
        return v_schemas.get(op, {})
    return schemas.get(version, {})


def generate_instance(
    api: str,
    intent: dict,
    client_version: str,
    server_version: str,
    breaking_data: dict[tuple[str, str], tuple[int, int]],
    backends: GoldBackends,
    is_pilot: bool,
    pilot_round: str | None,
) -> dict[str, Any]:
    """Generate one task instance JSON (data contract section 1)."""
    from nlipeval.tasks import tags as tagmod

    r = _renderer(api)
    intent_id = intent["id"]
    operation = intent.get("operation", "retrieveReachability" if api == "L1" else "verifyLocation" if api == "L2" else "createSession")
    task_id = f"{api}-{intent_id}-{client_version}"

    versions_behind = VERSIONS[api]["client_versions"].index(server_version) - VERSIONS[api]["client_versions"].index(client_version)
    bc, bc_ops = breaking_data.get((api, client_version), (0, 0))

    client_native = r.render_request(intent, client_version)
    gold_calls = r.render_gold_calls(intent, client_version)
    primary = gold_calls[0]

    gold_backend_resp = backends.call(api, primary)
    status = gold_backend_resp["status"]
    body = gold_backend_resp["body"]
    expected_refusal = None
    if status >= 400:
        expected_refusal = {"status": status, "code": (body or {}).get("code", "ERROR")}
    gold_client_answer = answer_from_response(r, gold_backend_resp, client_version)

    tag = tagmod.instance_tags(api, client_version, operation, client_native.get("body"), primary.get("body"),
                               gold_client_answer, server_version)
    if gold_client_answer["status"] == "declined":
        tag["change_tags_response"] = []
    missing, missing_source = _missing_info(api, client_version, intent)

    return {
        "schema_version": "1",
        "task_id": task_id,
        "intent_id": intent_id,
        "pilot": is_pilot,
        "api": api,
        "operation": operation,
        "client_version": client_version,
        "server_version": server_version,
        "versions_behind": versions_behind,
        "breaking_crossed": bc,
        "breaking_crossed_ops": bc_ops,
        "catalogue_breaking_crossed": tag["catalogue_breaking_crossed"],
        "prompt_half": intent.get("prompt_half", False),
        "pilot_round": pilot_round,
        "intent_text": intent["intent_text"],
        "client_native_request": client_native,
        "client_facts": intent.get("client_facts", []),
        "client_answer_schema": _load_answer_schema(api, client_version, operation),
        "world_ref": intent["world_ref"],
        "gold_calls": gold_calls,
        "gold_backend_response": gold_backend_resp,
        "gold_client_answer": gold_client_answer,
        "expected_refusal": expected_refusal,
        "refusal_predictable": False,
        "missing_info": missing,
        "missing_info_source": missing_source,
        "change_tags_request": tag["change_tags_request"],
        "change_tags_response": tag["change_tags_response"],
        "material_fields": MATERIAL_FIELDS.get(api, []),
        "provenance": intent.get("provenance", "authored"),
    }


def run(apis: list[str] | None = None, dry_run: bool = False) -> None:
    """Generate all task instances."""
    if apis is None:
        apis = ["L1", "L2", "L3"]

    breaking_data = _load_breaking_crossed()
    backends = GoldBackends()

    index_rows: list[dict] = []

    for api in apis:
        intents_path = CONFIG_DIR / "intents" / f"{api}.yaml"
        doc = yaml.safe_load(intents_path.read_text())
        server_version = VERSIONS[api]["server"]
        client_versions = VERSIONS[api]["client_versions"]

        all_intents = []
        for intent in doc.get("main", []):
            all_intents.append((intent, False, None))
        for intent in doc.get("pilot", []):
            pilot_round = intent.get("pilot_round")
            all_intents.append((intent, True, pilot_round))

        api_dir = TASKS_DIR / api
        api_dir.mkdir(parents=True, exist_ok=True)

        for intent, is_pilot, pilot_round in all_intents:
            intent_id = intent["id"]

            # Determine which client versions apply
            if is_pilot:
                # Pilot: current, 1 behind (oldest if only 1), and the oldest version (stage 05 §task counts)
                pilot_versions_set: set[str] = {server_version}  # current
                if len(client_versions) > 1:
                    pilot_versions_set.add(client_versions[-2])  # 1 behind
                pilot_versions_set.add(client_versions[0])  # oldest
                pilot_versions = [v for v in client_versions if v in pilot_versions_set]
            else:
                pilot_versions = client_versions

            for client_version in pilot_versions:
                task_id = f"{api}-{intent_id}-{client_version}"
                print(f"  Generating {task_id}...", end=" ", flush=True)

                try:
                    instance = generate_instance(
                        api, intent, client_version, server_version,
                        breaking_data, backends,
                        is_pilot, pilot_round,
                    )

                    if not dry_run:
                        out_path = api_dir / f"{task_id}.json"
                        out_path.write_text(json.dumps(instance, indent=2, ensure_ascii=False))

                    # Index row
                    index_rows.append({
                        "task_id": task_id,
                        "intent_id": intent_id,
                        "pilot": is_pilot,
                        "api": api,
                        "operation": instance["operation"],
                        "client_version": client_version,
                        "server_version": server_version,
                        "versions_behind": instance["versions_behind"],
                        "breaking_crossed": instance["breaking_crossed"],
                        "breaking_crossed_ops": instance["breaking_crossed_ops"],
                        "catalogue_breaking_crossed": instance["catalogue_breaking_crossed"],
                        "prompt_half": instance["prompt_half"],
                        "pilot_round": pilot_round or "",
                        "gold_status": instance["gold_client_answer"]["status"],
                        "expected_refusal": (instance["expected_refusal"] or {}).get("code", ""),
                        "missing_info": "|".join(instance["missing_info"]),
                        "change_tags_request": "|".join(instance["change_tags_request"]),
                        "change_tags_response": "|".join(instance["change_tags_response"]),
                    })
                    print("ok")
                except Exception as exc:
                    print(f"ERROR: {exc}")
                    raise

    if not dry_run:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        index_path = TASKS_DIR / "INDEX.csv"
        fieldnames = ["task_id", "intent_id", "pilot", "api", "operation", "client_version",
                      "server_version", "versions_behind", "breaking_crossed", "breaking_crossed_ops",
                      "catalogue_breaking_crossed", "prompt_half", "pilot_round", "gold_status",
                      "expected_refusal", "missing_info", "change_tags_request", "change_tags_response"]
        with open(index_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(index_rows)
        print(f"\nWrote {len(index_rows)} instances to {index_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate task instances (stage 05)")
    parser.add_argument("--api", nargs="*", choices=["L1", "L2", "L3"], help="APIs to generate (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Render but do not write files")
    args = parser.parse_args()
    run(apis=args.api, dry_run=args.dry_run)
