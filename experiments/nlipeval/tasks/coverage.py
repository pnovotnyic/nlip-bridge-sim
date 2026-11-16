"""Stage 05: generate coverage table (results/tasks/coverage.csv).

Stage 3 main instances per change kind, per direction, per API (07b A9: tags follow what an instance exercises),
the prompt-half count per kind (the Stage 3 ablation needs at least 5), the gold status distribution and the share of
instances with a non-empty `missing_info`.
Writes results/tasks/coverage.csv, results/tasks/prompt_half_coverage.csv, results/tasks/gold_status.csv and
results/tasks/missing_info_share.csv.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
RESULTS_DIR = ROOT / "results" / "tasks"

TAG_KINDS = ("renamed", "restructured", "unit_format", "newly_required", "changed_meaning", "removed")


def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Count Stage 3 instances per (api, direction, kind)
    # direction: request | response | either
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    half: dict[tuple[str, str], int] = defaultdict(int)
    status: dict[tuple[str, int, str], int] = defaultdict(int)
    missing: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])

    for api in ("L1", "L2", "L3"):
        api_dir = TASKS_DIR / api
        if not api_dir.exists():
            continue
        for f in sorted(api_dir.glob("*.json")):
            inst = json.loads(f.read_text())
            if inst["pilot"]:
                continue
            stage = 2 if inst["versions_behind"] == 0 else 3
            status[(api, stage, inst["gold_client_answer"]["status"])] += 1
            m = missing[(api, inst["client_version"])]
            m[1] += 1
            m[0] += 1 if inst["missing_info"] else 0
            if inst["versions_behind"] == 0:
                continue
            for kind in inst.get("change_tags_request", []):
                counts[(api, "request", kind)] += 1
            for kind in inst.get("change_tags_response", []):
                counts[(api, "response", kind)] += 1
            # 'either': instance has this kind in at least one direction
            all_kinds = set(inst.get("change_tags_request", [])) | set(inst.get("change_tags_response", []))
            for kind in all_kinds:
                counts[(api, "either", kind)] += 1
                if inst["prompt_half"]:
                    half[(api, kind)] += 1

    # Write coverage CSV
    rows = []
    for api in ("L1", "L2", "L3"):
        for direction in ("request", "response", "either"):
            for kind in TAG_KINDS:
                n = counts.get((api, direction, kind), 0)
                rows.append({"api": api, "direction": direction, "kind": kind, "n_stage3_instances": n})

    out = RESULTS_DIR / "coverage.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["api", "direction", "kind", "n_stage3_instances"])
        w.writeheader()
        w.writerows(rows)

    with open(RESULTS_DIR / "prompt_half_coverage.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["api", "kind", "n_stage3_instances", "n_prompt_half"])
        for api in ("L1", "L2", "L3"):
            for kind in TAG_KINDS:
                w.writerow([api, kind, counts.get((api, "either", kind), 0), half.get((api, kind), 0)])
    with open(RESULTS_DIR / "gold_status.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["api", "stage", "status", "n"])
        for (api, stage, st), n in sorted(status.items()):
            w.writerow([api, stage, st, n])
    with open(RESULTS_DIR / "missing_info_share.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["api", "client_version", "n_main", "n_missing_info", "share"])
        for (api, v), (k, n) in sorted(missing.items()):
            w.writerow([api, v, n, k, round(k / n, 3)])

    # Print a summary
    print("Stage 3 coverage (instances per kind, 'either' direction):")
    for api in ("L1", "L2", "L3"):
        for kind in TAG_KINDS:
            n = counts.get((api, "either", kind), 0)
            h = half.get((api, kind), 0)
            flag = " BELOW 5 IN THE PROMPT HALF" if 0 < h < 5 else (" (zero)" if n == 0 else "")
            print(f"  {api} {kind:20s}: {n:3d}  prompt half {h:3d}{flag}")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    run()
