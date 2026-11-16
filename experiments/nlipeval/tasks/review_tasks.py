"""Generate reports/review-tasks.md showing all intent details."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
CONFIG_DIR = ROOT / "config"
REPORTS_DIR = ROOT / "reports"


def show_intent_block(api: str, intent: dict, main_instances: list[dict]) -> str:
    lines = []
    intent_id = intent["id"]
    # Find task instances for this intent (sorted oldest→newest client version)
    instances = sorted(
        [i for i in main_instances if i["intent_id"] == intent_id],
        key=lambda x: x["versions_behind"],
        reverse=True,
    )
    if not instances:
        return ""

    oldest = instances[0]
    current = instances[-1]

    lines.append(f"### {api}-{intent_id}")
    lines.append(f"**Intent:** {intent['intent_text']}")
    lines.append(f"**Operation:** {oldest['operation']}")
    lines.append(f"**prompt_half:** {intent.get('prompt_half', False)} | versions_behind (oldest): {oldest['versions_behind']}")
    lines.append("")
    lines.append(f"**Native request at `{oldest['client_version']}` (oldest):**")
    lines.append("```json")
    lines.append(json.dumps(oldest["client_native_request"], indent=2))
    lines.append("```")
    if current["client_version"] != oldest["client_version"]:
        lines.append(f"**Gold call at `{current['client_version']}` (server):**")
        lines.append("```json")
        lines.append(json.dumps(current["gold_calls"][0], indent=2))
        lines.append("```")
        if len(current["gold_calls"]) > 1:
            lines.append(f"({len(current['gold_calls'])} gold alternatives: "
                         + "; ".join(json.dumps((c.get('body') or {}).get('device') or c.get('body'))[:90] for c in current["gold_calls"][1:]) + ")")
    lines.append(f"**Gold backend response:** HTTP {current['gold_backend_response']['status']}"
                 + (f", expected refusal `{current['expected_refusal']['code']}`" if current.get("expected_refusal") else ""))
    lines.append("")
    lines.append("**Gold client answers by version:**")
    lines.append("")
    lines.append("| client_version | status | result summary | tags request | tags response | breaking crossed |")
    lines.append("|---|---|---|---|---|---|")
    for inst in instances:
        gca = inst["gold_client_answer"]
        result_summary = "null"
        if gca.get("result"):
            # First key-value pair
            r = gca["result"]
            first_kv = list(r.items())[:2]
            result_summary = ", ".join(f"`{k}`: {json.dumps(v)}" for k, v in first_kv)
        lines.append(f"| `{inst['client_version']}` | `{gca['status']}` | {result_summary} | "
                     f"{','.join(inst['change_tags_request'])} | {','.join(inst['change_tags_response'])} | "
                     f"{inst['catalogue_breaking_crossed']} |")
    lines.append("")
    if oldest.get("client_facts"):
        facts_str = "; ".join(f"{cf['fact']}={cf['value']}" for cf in oldest["client_facts"])
        lines.append(f"**client_facts:** {facts_str}")
    if oldest.get("missing_info"):
        lines.append(f"**missing_info:** {oldest['missing_info_source']}")
    tags_req = oldest.get("change_tags_request") or []
    tags_resp = oldest.get("change_tags_response") or []
    lines.append(f"**change_tags (oldest):** request={tags_req}, response={tags_resp}")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def run() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "review-tasks.md"

    # Load all main task instances
    all_instances: dict[str, list[dict]] = {}
    for api in ("L1", "L2", "L3"):
        api_dir = TASKS_DIR / api
        if not api_dir.exists():
            continue
        all_instances[api] = []
        for f in sorted(api_dir.glob("*.json")):
            inst = json.loads(f.read_text())
            if not inst["pilot"]:
                all_instances[api].append(inst)

    sections = []
    sections.append("# Task review — stage 05, corrected in stage 07b\n")
    sections.append("All 30 main intents per API with native requests, gold calls, and gold client answers.\n")
    sections.append("Pilot intents are not included (they re-use a subset of main devices/sessions).\n\n")

    for api in ("L1", "L2", "L3"):
        intents_doc = yaml.safe_load((CONFIG_DIR / "intents" / f"{api}.yaml").read_text())
        sections.append(f"## {api}\n")
        for intent in intents_doc.get("main", []):
            block = show_intent_block(api, intent, all_instances.get(api, []))
            sections.append(block)

    out_path.write_text("".join(sections), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
