"""Markdown tables for reports/stage-03-conformance.md, computed from results/stage1/*.csv.

    uv run python -m stage1.harness.tables
"""
import csv
from collections import Counter, defaultdict

from stage1.harness.adapters import RESULTS

GROUPS = {"G1": "5 Field names and values in any case", "G2": "5.1–5.2 Required and optional fields", "G3": "5.3 Formats and subformats",
          "G4": "6.1 Initial request answered with NLIP", "G5": "6.2 Token submessages returned unchanged", "G6": "6.2.1–6.2.2 Reserved token prefixes",
          "G7": "6.3 Control message answered with control", "G8": "6.4 Out-of-band transfer", "G9": "7 and ECMA-431 Transport and HTTP binding"}
COLS = [("nlip_sdk", "`nlip_sdk`"), ("nlip_server", "`nlip_server` (minimal app)"), ("nlip_server_echo", "`nlip_server` (own echo app)"), ("ts_client", "TypeScript client"), ("ours", "Our implementation")]
# stage 03b (S2): the headline uses the minimal application; the echo application is a footnote column
HEAD_COLS = [("nlip_sdk", "`nlip_sdk`"), ("nlip_server", "`nlip_server` (minimal app)"), ("ts_client", "TypeScript client"), ("ours", "Our implementation"),
             ("nlip_server_echo", "`nlip_server` with the library's own example application¹")]

# Which open reading of the standard (A1-A7, see reports/review-readings-A1-A7.md) each flagged check depends on.
# C49 rests on the typing in Annex A (informative), which is not one of A1-A7.
READINGS = {"C15": "reading A2", "C16": "reading A7", "C17": "reading A7", "C35": "reading A1", "C36": "reading A1",
            "C49": "Annex A typing (informative)"}


def cell(rows):
    ap = [r for r in rows if r["outcome"] != "n/a"]
    return "n/a" if not ap else f"{sum(r['outcome'] == 'pass' for r in ap)}/{len(ap)}"


def main():
    rows = list(csv.DictReader(open(RESULTS / "conformance_detail.csv")))
    firm = [r for r in rows if not r["reading"]]  # checks that depend on no open reading and not on the application
    out = ["| Clause group | Checks | " + " | ".join(c[1] for c in HEAD_COLS) + " |", "| --- | ---: | " + " | ".join("---" for _ in HEAD_COLS) + " |"]
    for g, name in GROUPS.items():
        n = len({r["check_id"] for r in firm if r["group"] == g})
        out.append(f"| {name} | {n or '—'} | " + " | ".join(cell([r for r in firm if r["group"] == g and r["implementation"] == k]) for k, _ in HEAD_COLS) + " |")
    n = len({r["check_id"] for r in firm})
    out.append(f"| **Total** | {n} | " + " | ".join("**" + cell([r for r in firm if r["implementation"] == k]) + "**" for k, _ in HEAD_COLS) + " |")
    print("TABLE 1\n" + "\n".join(out))
    # the flagged checks, shown separately
    flagged = sorted({r["check_id"] for r in rows if r["reading"]}, key=lambda c: (next(r["group"] for r in rows if r["check_id"] == c), c))
    out = ["| Check | Depends on | " + " | ".join(c[1] for c in HEAD_COLS) + " | What it checks |", "| --- | --- | " + " | ".join("---" for _ in HEAD_COLS) + " | --- |"]
    sym = {"pass": "pass", "fail": "**fail**", "n/a": "n/a", "blocked": "blocked"}
    for cid in flagged:
        by_impl = {r["implementation"]: r for r in rows if r["check_id"] == cid}
        o = by_impl["ours"]
        dep = " + ".join(x for x in (READINGS.get(cid), "application behaviour" if o["reading"] == "application" else None) if x)
        out.append(f"| {cid} | {dep} | " + " | ".join(sym[by_impl[k]["outcome"]] for k, _ in HEAD_COLS) + f" | {o['title']} |")
    print("\nTABLE 1A\n" + "\n".join(out))
    out = ["| | " + " | ".join(c[1] for c in HEAD_COLS) + " |", "| --- | " + " | ".join("---" for _ in HEAD_COLS) + " |"]
    for lab, sel in (("Flagged checks only (passed / applicable)", [r for r in rows if r["reading"]]), ("All 49 checks (passed / applicable)", rows)):
        out.append(f"| {lab} | " + " | ".join(cell([r for r in sel if r["implementation"] == k]) for k, _ in HEAD_COLS) + " |")
    print("\nTABLE 1B\n" + "\n".join(out))
    out = ["| Implementation | pass | fail | n/a | blocked |", "| --- | ---: | ---: | ---: | ---: |"]
    for k, lab in COLS:
        c = Counter(r["outcome"] for r in rows if r["implementation"] == k)
        out.append(f"| {lab} | {c['pass']} | {c['fail']} | {c['n/a']} | {c['blocked']} |")
    print("\nOUTCOMES\n" + "\n".join(out))
    # per-check matrix
    by = defaultdict(dict)
    for r in rows:
        by[r["check_id"]][r["implementation"]] = r
    out = ["| Check | Requirement | Reading | " + " | ".join(c[1] for c in COLS) + " | What it checks |", "| --- | --- | --- | " + " | ".join("---" for _ in COLS) + " | --- |"]
    for cid, d in sorted(by.items(), key=lambda kv: (kv[1]["ours"]["group"], kv[0])):
        o = d["ours"]
        out.append(f"| {cid} | `{o['requirement_id']}` | {o['reading'] or ''} | " + " | ".join(sym[d[k]["outcome"]] for k, _ in COLS) + f" | {o['title']} |")
    print("\nMATRIX\n" + "\n".join(out))
    irows = list(csv.DictReader(open(RESULTS / "interop.csv")))
    drows = list(csv.DictReader(open(RESULTS / "interop_detail.csv")))
    cl = ["nlip_sdk", "ts_client", "ours"]
    names = {"nlip_sdk": "`nlip_sdk` client", "ts_client": "TypeScript example client", "ours": "Our client", "nlip_server": "`nlip_server` (own echo app)"}
    out = ["| Client ↓ · Server → | `nlip_server` (own echo app) | Our server (echo handler) |", "| --- | --- | --- |"]
    for c in cl:
        cells = []
        for s in ("nlip_server", "ours"):
            r = next(x for x in irows if x["client"] == c and x["server"] == s)
            not_built = sum(d["outcome"] == "not built" for d in drows if d["client"] == c and d["server"] == s)
            cells.append(f"{r['messages_ok']}/{r['messages_total']}" + (f" ({not_built} not built)" if not_built else ""))
        out.append(f"| {names[c]} | " + " | ".join(cells) + " |")
    print("\nTABLE 2\n" + "\n".join(out))
    drows = list(csv.DictReader(open(RESULTS / "interop_detail.csv")))
    out = ["| Message | What | " + " | ".join(f"{c}→{s}" for c in cl for s in ("nlip_server", "ours")) + " |", "| --- | --- | " + " | ".join("---" for _ in range(6)) + " |"]
    for mid in sorted({r["message"] for r in drows}):
        desc = next(r["description"] for r in drows if r["message"] == mid)
        cells = []
        for c in cl:
            for s in ("nlip_server", "ours"):
                r = next(x for x in drows if x["message"] == mid and x["client"] == c and x["server"] == s)
                cells.append({"ok": "ok", "fail": "**fail**", "not built": "not built"}[r["outcome"]])
        out.append(f"| {mid} | {desc} | " + " | ".join(cells) + " |")
    print("\nDETAIL\n" + "\n".join(out))


if __name__ == "__main__":
    main()
