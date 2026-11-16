"""Stage 07b (B12): time per rung for stages 08-10, and R5's cost for stage 14.

    uv run python scripts/project_time_cost.py <smoke-run-dir>

Inputs: results/prompts/prompt_sizes.csv (real tokenizers), tasks/INDEX.csv, the smoke run (per-call history
overhead and output tokens, R3), and the latencies of stages 01 and 04b. Writes
results/prompts/time_projection.csv and results/prompts/r5_cost.csv, and prints both.

Call counts: 5 calls per NLIP session (client 3, server 2) plus 2 per interaction (client 1, server 1);
4 per NLIP-0 session (client 2, server 2). Interactions per NLIP session: the share of instances with
`missing_info` (one question each), computed from the instances run in that stage.
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNGS = ["R1", "R2", "R3", "R4"]
SERVER_VERSION = {"L1": "v1.0.0", "L2": "v3.0.0", "L3": "v1.1.0"}
# seconds per call: R1 from stage 04b (client 11.41, server 14.72 -> mean); R2-R4 from stage 01 (4,000-token prompt,
# up to 300 tokens out, median)
LATENCY_S = {"R1": (11.41 + 14.72) / 2, "R2": 5.8, "R3": 1.8, "R4": 28.0}
CONCURRENCY = {"R1": 1, "R2": 8, "R3": 8, "R4": 8}
R5_PRICE = (4.0, 20.0)   # USD per million input / output tokens


def load_sizes() -> dict[tuple, int]:
    out = {}
    for r in csv.DictReader(open(ROOT / "results/prompts/prompt_sizes.csv")):
        for rung in RUNGS:
            if r[rung]:
                out[(r["role"], r["api"], r["version"], r["prompt"], rung)] = int(r[rung])
    return out


def load_index() -> list[dict]:
    return list(csv.DictReader(open(ROOT / "tasks/INDEX.csv")))


def calibrate(run_dir: Path, sizes: dict) -> dict:
    """Per role: mean history overhead (prompt_tokens minus the system prompt) and mean output tokens per call."""
    sess = {}
    for line in open(run_dir / "sessions.jsonl"):
        r = json.loads(line)
        sess[r["session_id"]] = r
    over, out = defaultdict(list), defaultdict(list)
    for line in open(run_dir / "calls.jsonl"):
        c = json.loads(line)
        s = sess.get(c["session_id"])
        if s is None or c["purpose"] == "repair" or not c.get("usage"):
            continue
        role = c["role"]
        version = s["client_version"] if role == "client" else s["server_version"]
        variant = "NLIP-0" if s["condition"] == "NLIP-0" else s["prompt"]
        sysz = sizes.get((role, s["api"], version, variant, "R3"))
        if sysz is None:
            continue
        over[role].append(c["usage"]["prompt_tokens"] - sysz)
        out[role].append(c["usage"]["completion_tokens"])
    return {role: {"overhead": st.mean(over[role]), "out": st.mean(out[role])} for role in over}


def observed_slowdown(run_dir: Path) -> float:
    """Mean call latency in the smoke run (R3), over R3's stage 01 latency: what real prompts and replies cost
    compared with the 4,000-token benchmark."""
    lat = [json.loads(l)["latency_ms"] / 1000 for l in open(run_dir / "calls.jsonl")
           if json.loads(l)["session_id"] != "warmup" and json.loads(l)["purpose"] != "repair"]
    return st.mean(lat) / LATENCY_S["R3"]


def session_calls(cond: str, k: float) -> tuple[float, float]:
    """(client calls, server calls) per session."""
    if cond == "NLIP":
        return 3 + k, 2 + k
    return 2.0, 2.0


def mean_k(rows: list[dict]) -> float:
    return sum(1 for r in rows if r["missing_info"]) / len(rows) if rows else 0.0


def stages(index: list[dict]) -> dict:
    main = [r for r in index if r["pilot"] == "False"]
    pilot_a = [r for r in index if r["pilot"] == "True" and r["pilot_round"] == "A"]
    s2 = [r for r in main if int(r["versions_behind"]) == 0]
    s3 = [r for r in main if int(r["versions_behind"]) >= 1]
    half3 = [r for r in s3 if r["prompt_half"] == "True"]
    l3_pilot = [r for r in pilot_a if r["api"] == "L3"]
    # stage -> list of (rows, prompt, condition, rungs)
    return {
        "08 pilot": [(pilot_a, "P2", "NLIP", RUNGS), (pilot_a, "P2", "NLIP-0", RUNGS),
                     (l3_pilot, "P1", "NLIP", ["R1", "R3"]), (l3_pilot, "P3", "NLIP", ["R1", "R3"])],
        "09 stage 2": [(s2, "P2", "NLIP", RUNGS), (s2, "P2", "NLIP-0", RUNGS)],
        "10 stage 3": [(s3, "P2", "NLIP", RUNGS), (s3, "P2", "NLIP-0", RUNGS),
                       (half3, "P3", "NLIP", RUNGS), (half3, "P1", "NLIP", RUNGS)],
    }


def tokens_for(rows: list[dict], prompt: str, cond: str, rung: str, sizes: dict, cal: dict, k: float):
    """(client calls, server calls, input tokens, output tokens) for these sessions on this rung."""
    variant = "NLIP-0" if cond == "NLIP-0" else prompt
    cc, sc = session_calls(cond, k)
    n_c = n_s = t_in = t_out = 0.0
    for r in rows:
        cs = sizes[("client", r["api"], r["client_version"], variant, rung)]
        ss = sizes[("server", r["api"], SERVER_VERSION[r["api"]], variant, rung)]
        n_c += cc
        n_s += sc
        t_in += cc * (cs + cal["client"]["overhead"]) + sc * (ss + cal["server"]["overhead"])
        t_out += cc * cal["client"]["out"] + sc * cal["server"]["out"]
    return n_c, n_s, t_in, t_out


def main(run_dir: Path) -> None:
    sizes, index = load_sizes(), load_index()
    cal = calibrate(run_dir, sizes)
    slow = observed_slowdown(run_dir)
    print("observed slowdown on R3 (smoke run mean call / stage 01 median):", round(slow, 2))
    print("calibration from the smoke run (R3):", {k: {a: round(b) for a, b in v.items()} for k, v in cal.items()})

    time_rows = []
    for stage, parts in stages(index).items():
        for rung in RUNGS:
            sessions = calls = 0.0
            for rows, prompt, cond, rungs in parts:
                if rung not in rungs:
                    continue
                k = mean_k(rows) if cond == "NLIP" else 0.0
                n_c, n_s, _, _ = tokens_for(rows, prompt, cond, rung, sizes, cal, k)
                sessions += len(rows)
                calls += n_c + n_s
            hours = calls * LATENCY_S[rung] / CONCURRENCY[rung] / 3600
            # R1's latency (stage 04b) was measured with a local decode that dominates the call; the others are
            # scaled by what the smoke run showed on R3
            hours_scaled = hours if rung == "R1" else hours * slow
            time_rows.append(dict(stage=stage, rung=rung, sessions=int(sessions), calls=round(calls),
                                  seconds_per_call=round(LATENCY_S[rung], 2), concurrency=CONCURRENCY[rung],
                                  hours=round(hours, 1), hours_scaled=round(hours_scaled, 1)))
    with open(ROOT / "results/prompts/time_projection.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(time_rows[0]))
        w.writeheader()
        w.writerows(time_rows)
    print("\nstage rung sessions calls s/call conc hours hours_scaled")
    for r in time_rows:
        print(*r.values())
    for rung in RUNGS:
        tot = sum(r["hours"] for r in time_rows if r["rung"] == rung)
        tot_s = sum(r["hours_scaled"] for r in time_rows if r["rung"] == rung)
        print(rung, "total hours", round(tot, 1), "scaled", round(tot_s, 1))

    # R5, stage 14: 90 stage 2 + 330 stage 3 instances, P2, NLIP and NLIP-0 (840 sessions)
    main_rows = [r for r in index if r["pilot"] == "False"]
    k = mean_k(main_rows)
    cost_rows = []
    for rung in RUNGS:   # R5's own tokenizer is not measured; the four rungs bracket it
        t_in = t_out = n = 0.0
        for cond in ("NLIP", "NLIP-0"):
            n_c, n_s, ti, to = tokens_for(main_rows, "P2", cond, rung, sizes, cal, k if cond == "NLIP" else 0.0)
            t_in += ti
            t_out += to
            n += n_c + n_s
        for label, mult in (("output as R3 smoke", 1.0), ("output x2", 2.0)):
            usd = t_in / 1e6 * R5_PRICE[0] + t_out * mult / 1e6 * R5_PRICE[1]
            cost_rows.append(dict(tokenizer=rung, output_case=label, sessions=2 * len(main_rows), calls=round(n),
                                  input_mtok=round(t_in / 1e6, 2), output_mtok=round(t_out * mult / 1e6, 2),
                                  usd=round(usd)))
    with open(ROOT / "results/prompts/r5_cost.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cost_rows[0]))
        w.writeheader()
        w.writerows(cost_rows)
    print("\nR5 cost (stage 14)")
    for r in cost_rows:
        print(*r.values())


if __name__ == "__main__":
    main(Path(sys.argv[1]))
