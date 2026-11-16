"""Generate reports/review-prompts.md with one rendered P3 prompt per API and condition."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(ROOT))

from nlipeval.agents.prompts import render_client, render_server

tasks = {}
for api in ["L1", "L2", "L3"]:
    for p in sorted((ROOT / "tasks" / api).glob("*-p01-*.json")):
        tasks[api] = json.loads(p.read_text())
        break

out = []
out.append("# Prompt review: one task per API and condition")
out.append("")
out.append(
    "Generated for Petr\u2019s review before the pilot. "
    "All prompts use P3 (includes per-version notes). "
    "NLIP and NLIP-0 conditions shown for pilot task p01 at the client\u2019s own version."
)
out.append("")

FENCE = "```"

for api, task in tasks.items():
    for condition in ["NLIP", "NLIP-0"]:
        out.append("---")
        out.append("")
        out.append(f"## {api} \u2014 {condition} \u2014 P3 \u2014 task {task['task_id']}")
        out.append("")
        out.append("### Client system prompt")
        out.append("")
        out.append(FENCE)
        out.append(render_client(task, "P3", condition))
        out.append(FENCE)
        out.append("")
        out.append("### Server system prompt")
        out.append("")
        out.append(FENCE)
        out.append(render_server(api, task["server_version"], "P3", condition))
        out.append(FENCE)
        out.append("")

(ROOT / "reports" / "review-prompts.md").write_text("\n".join(out), encoding="utf-8")
print("written")
