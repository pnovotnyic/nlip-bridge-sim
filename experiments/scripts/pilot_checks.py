"""Stage 08 step 3: pilot checks for a run (R1 only while the RITS API is unavailable).

    uv run python scripts/pilot_checks.py <run_id_or_dir> [more run dirs...]

Reads sessions.jsonl, scores.jsonl, calls.jsonl and wire.jsonl, and writes
results/pilot/checks.csv, results/pilot/outcomes.csv and results/pilot/r1_call_stats.csv.
Prints the same tables. Nothing here changes run data.
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "pilot"
R1_CONTEXT = 65536


def jl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def pct(n: float, d: float) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "0/0"


def quant(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


def main(run_dirs: list[Path]) -> None:
    sessions, scores, calls, wires = [], [], [], []
    for rd in run_dirs:
        sessions += jl(rd / "sessions.jsonl")
        scores += jl(rd / "scores.jsonl")
        calls += jl(rd / "calls.jsonl")
        wires += jl(rd / "wire.jsonl")
    sc = {s["session_id"]: s for s in scores}
    real = [c for c in calls if c["session_id"] != "warmup"]
    warm = [c for c in calls if c["session_id"] == "warmup"]
    n = len(sessions)
    rungs = sorted({s["client_rung"] for s in sessions})
    checks: list[tuple[str, str, str]] = []

    infra = sum(1 for s in sessions if s["termination"] == "error_harness")
    checks.append(("error_harness sessions", pct(infra, n), "target < 2%"))

    for r in rungs:
        rc = [c for c in real if c["rung"] == r]
        fail = [c for c in rc if c.get("parse_ok") is False or c.get("error_type") == "parse_failure"]
        repaired = [c for c in rc if c.get("purpose") == "repair"]
        err_calls = [c for c in rc if c.get("error")]
        checks.append((f"{r} parse failures after repair (calls with error)", pct(len(err_calls), len(rc)),
                       f"target < 5%; repair calls {len(repaired)}, parse_ok=false {len(fail)}"))

    # 08a F15: the criteria of the first-10 check
    checks.append(("sessions ending error_model", pct(sum(1 for s in sessions if s["termination"] == "error_model"), n),
                   "08a F15: stop if more than 1 of the first 10"))
    rep = sum(1 for s in sessions if s.get("n_action_repairs_client", 0) + s.get("n_action_repairs_server", 0))
    checks.append(("sessions needing an action repair", pct(rep, n), "08a F15: stop if more than 3 of the first 10"))
    nofinal = [s["session_id"] for s in sessions if not s.get("client_final") and s["termination"] in ("final", "declined")]
    checks.append(("sessions with no client_final (final or declined)", pct(len(nofinal), n),
                   "08a F15: stop if any of the first 10"))

    bad_wire = [w for w in wires if not w.get("valid_ecma430")]
    checks.append(("wire messages valid under ECMA-430", pct(len(wires) - len(bad_wire), len(wires)), "target 100%"))

    slips = Counter()
    for s in sessions:
        if s["n_protocol_slips"]:
            slips[s["condition"]] += s["n_protocol_slips"]
    for cond in ("NLIP", "NLIP-0"):
        k = sum(1 for s in sessions if s["condition"] == cond)
        checks.append((f"protocol slips, {cond}", pct(sum(1 for s in sessions if s["condition"] == cond and s["n_protocol_slips"]), k),
                       f"{slips[cond]} slips in total; report"))

    for r in rungs:
        rc = [c for c in real if c["rung"] == r and c.get("usage")]
        mp = max((c["usage"]["prompt_tokens"] or 0) for c in rc) if rc else 0
        mpc = max(((c["usage"]["prompt_tokens"] or 0) + (c["usage"]["completion_tokens"] or 0)) for c in rc) if rc else 0
        checks.append((f"{r} largest prompt / prompt+completion (tokens)", f"{mp} / {mpc}",
                       f"context {R1_CONTEXT if r == 'R1' else 'n/a'}; truncation if prompt+completion nears it"))

    # timeouts and transport failures per rung
    for r in rungs:
        rs = [s for s in sessions if s["client_rung"] == r]
        to = sum(1 for s in rs if s["termination"] == "timeout" or s.get("timeout_rerun"))
        conn = sum(1 for c in real if c["rung"] == r and c.get("error_type") in ("timeout", "connection"))
        checks.append((f"{r} session timeouts (incl. re-run) / transport-failed calls", f"{pct(to, len(rs))} / {conn}", "target < 1%"))

    # refused call followed by accepted one (backend rejected, then 2xx)
    for r in rungs:
        for cond in ("NLIP", "NLIP-0"):
            rs = [s for s in sessions if s["client_rung"] == r and s["condition"] == cond]
            rec = 0
            for s in rs:
                st_ = [e["status"] for e in s["executed_calls"]]
                if any(x >= 400 for x in st_) and any(200 <= x < 300 for x in st_):
                    rec += 1
            checks.append((f"{r} {cond} sessions with a refused call then an accepted one", pct(rec, len(rs)), "report"))

    for r in rungs:
        warm_r = [c["latency_ms"] / 1000 for c in warm if c["rung"] == r]
        checks.append((f"{r} schema warm-up calls: max latency (s)", f"{max(warm_r):.1f}" if warm_r else "n/a",
                       f"{len(warm_r)} warm-up calls; stalls = latency far above the run's median"))

    nl = [s for s in sessions if s["condition"] == "NLIP"]
    for r in rungs:
        rs = [s for s in nl if s["client_rung"] == r]
        checks.append((f"{r} NLIP sessions with k >= 1", pct(sum(1 for s in rs if s["n_interactions"] >= 1), len(rs)), "target > 0"))

    # outcomes
    out_rows = []
    keyf = lambda s: (s["client_rung"], s["prompt"], s["condition"])
    groups = defaultdict(list)
    for s in sessions:
        groups[keyf(s)].append(s)
    for (r, p, cond), ss in sorted(groups.items()):
        sco = [sc[s["session_id"]] for s in ss if s["session_id"] in sc]
        t = Counter(s["termination"] for s in ss)
        out_rows.append(dict(
            rung=r, prompt=p, condition=cond, sessions=len(ss), scored=len(sco),
            end_to_end=sum(1 for x in sco if x["end_to_end"]),
            request_correct=sum(1 for x in sco if x["request_correct"]),
            response_correct=sum(1 for x in sco if x["response_correct"]),
            harmful=sum(1 for x in sco if x["harmful"]),
            declined=sum(1 for x in sco if x["declined"]),
            mean_k=round(st.mean(s["n_interactions"] for s in ss), 2),
            final=t["final"], declined_term=t["declined"], max_interactions=t["max_interactions"],
            timeout=t["timeout"], error_model=t["error_model"], error_harness=t["error_harness"],
            mean_wall_s=round(st.mean(s["wall_seconds"] for s in ss), 1)))
    for r in rungs:
        sco = [sc[s["session_id"]] for s in sessions if s["client_rung"] == r and s["session_id"] in sc]
        checks.append((f"{r} pooled end-to-end success", pct(sum(1 for x in sco if x["end_to_end"]), len(sco)), "report (ladder order needs R2-R4)"))

    # per-call stats
    call_rows = []
    for r in rungs:
        for role in ("client", "server"):
            rc = [c for c in real if c["rung"] == r and c["role"] == role and c.get("usage") and not c.get("cached")]
            comp = [c["usage"]["completion_tokens"] or 0 for c in rc]
            pt = [c["usage"]["prompt_tokens"] or 0 for c in rc]
            lat = [c["latency_ms"] / 1000 for c in rc]
            rate = [(c["usage"]["completion_tokens"] or 0) / (c["latency_ms"] / 1000) for c in rc if c["latency_ms"]]
            call_rows.append(dict(rung=r, role=role, calls=len(rc),
                                  out_tokens_median=quant(comp, .5), out_tokens_p90=quant(comp, .9),
                                  prompt_tokens_median=quant(pt, .5), prompt_tokens_max=max(pt) if pt else 0,
                                  latency_s_median=round(quant(lat, .5), 1), latency_s_p90=round(quant(lat, .9), 1),
                                  completion_tok_per_s_median=round(quant(rate, .5), 1)))

    # projection for stages 09-10 (R1): calls * mean latency
    for r in rungs:
        rc = [c for c in real if c["rung"] == r and not c.get("cached")]
        if rc:
            per_call = st.mean(c["latency_ms"] for c in rc) / 1000
            per_sess = st.mean(s["wall_seconds"] for s in sessions if s["client_rung"] == r)
            checks.append((f"{r} mean seconds per call / per session", f"{per_call:.1f} / {per_sess:.1f}",
                           "projection for stages 09-10 uses these (see report)"))

    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("outcomes", out_rows), ("r1_call_stats", call_rows)):
        if rows:
            with open(OUT / f"{name}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    with open(OUT / "checks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["check", "result", "note"])
        w.writerows(checks)

    print("sessions:", n, dict(Counter(s["termination"] for s in sessions)))
    for c in checks:
        print(" | ".join(c))
    for name, rows in (("outcomes", out_rows), ("call stats", call_rows)):
        print("\n" + name)
        for r in rows:
            print(r)


if __name__ == "__main__":
    dirs = []
    for a in sys.argv[1:]:
        p = Path(a)
        dirs.append(p if p.is_dir() else ROOT / "data" / "runs" / a)
    main(dirs)
