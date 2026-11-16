"""Run the Stage 1 conformance checks on every implementation.

    uv run python -m stage1.harness.run_suite

Writes results/stage1/conformance.csv (check_id, requirement_id, clause, implementation, outcome, evidence) and one
log per run under results/stage1/logs/<implementation>/<check>.log.
"""
from __future__ import annotations

import csv
import sys
import traceback
from pathlib import Path

import yaml

import stage1.tests.checks_def  # noqa: F401  (registers the checks)
from stage1.harness.adapters import RESULTS, ROOT, build_impls
from stage1.harness.checks import CHECKS, NA, Ctx, Fail

REQS = {r["id"]: r for r in yaml.safe_load((ROOT / "stage1" / "requirements.yaml").read_text())["requirements"]}


def run_one(impl, chk) -> tuple[str, str]:
    """Returns (outcome, detail)."""
    if impl.blocked:
        return "blocked", impl.blocked
    impl.trace.clear()
    ctx = Ctx(impl, chk)
    try:
        chk.fn(ctx)
        return "pass", ""
    except Fail as e:
        return "fail", str(e)
    except NA as e:
        return "n/a", str(e)
    except NotImplementedError as e:
        return "fail", f"the implementation has no way to do this: {e}"
    except Exception as e:  # an unexpected error is a failure of the check on this implementation, with the trace
        return "fail", f"unexpected {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"


def run(include: list[str] | None = None, write: bool = True) -> list[dict]:
    impls = build_impls(include)
    rows: list[dict] = []
    try:
        for impl in impls:
            for chk in CHECKS:
                outcome, detail = run_one(impl, chk)
                req = REQS[chk.req]
                log = RESULTS / "logs" / impl.key / f"{chk.id}.log"
                if write:
                    log.parent.mkdir(parents=True, exist_ok=True)
                    log.write_text(
                        f"check {chk.id}: {chk.title}\nrequirement {chk.req} ({req['standard']} clause {req['clause']}, {req['level']})\n"
                        f"quote: {req['quote']}\nimplementation: {impl.label}\noutcome: {outcome}\n"
                        + (f"note: {chk.note}\n" if chk.note else "")
                        + (f"detail: {detail}\n" if detail else "")
                        + "\ntrace:\n"
                        + "\n".join("  " + t for t in impl.trace)
                        + "\n"
                    )
                rows.append(
                    {
                        "check_id": chk.id,
                        "requirement_id": chk.req,
                        "clause": f"{req['standard']} {req['clause']}",
                        "implementation": impl.key,
                        "outcome": outcome,
                        "evidence": str(log.relative_to(ROOT)),
                        "detail": detail.splitlines()[0][:300] if detail else "",
                        "group": chk.group,
                        "kind": chk.kind,
                        "reading": chk.reading,
                        "title": chk.title,
                    }
                )
    finally:
        for i in impls:
            i.close()
    if write:
        RESULTS.mkdir(parents=True, exist_ok=True)
        with open(RESULTS / "conformance.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["check_id", "requirement_id", "clause", "implementation", "outcome", "evidence"], extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        with open(RESULTS / "conformance_detail.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["check_id", "requirement_id", "clause", "group", "kind", "reading", "title", "implementation", "outcome", "detail", "evidence"])
            w.writeheader()
            w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = run(sys.argv[1:] or None)
    from collections import Counter

    for impl in dict.fromkeys(r["implementation"] for r in rows):
        print(impl, dict(Counter(r["outcome"] for r in rows if r["implementation"] == impl)))
    for r in rows:
        if r["outcome"] == "fail":
            print(f"  FAIL {r['implementation']:12} {r['check_id']} {r['requirement_id']}: {r['detail'][:150]}")
