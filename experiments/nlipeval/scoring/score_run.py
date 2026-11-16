"""CLI for scoring a run: `python -m nlipeval.scoring.score_run <run_id> [--incremental]` (stage 07)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nlipeval.scoring.score import score_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Score an NLIP evaluation run.")
    parser.add_argument("run_id", help="Run directory path or run_id inside data/runs/")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only score sessions that do not already have scores in scores.jsonl",
    )
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        default=None,
        help="Optional path to tasks directory",
    )

    args = parser.parse_args()
    target = Path(args.run_id)
    if not target.is_dir():
        # Check relative to repo data/runs/
        repo_runs = Path("data/runs") / args.run_id
        if repo_runs.is_dir():
            target = repo_runs
        else:
            print(f"Error: Run directory not found: {args.run_id}", file=sys.stderr)
            sys.exit(1)

    print(f"Scoring run at {target} (incremental={args.incremental})...")
    scores = score_run(target, incremental=args.incremental, tasks_dir=args.tasks_dir)
    n_total = len(scores)
    n_e2e = sum(1 for s in scores if s.get("end_to_end"))
    n_harmful = sum(1 for s in scores if s.get("harmful"))
    n_infra = sum(1 for s in scores if s.get("infra_error"))

    print(f"Scored {n_total} sessions:")
    print(f"  End-to-end correct: {n_e2e}/{n_total} ({n_e2e/n_total*100:.1f}%)" if n_total else "  0 sessions")
    print(f"  Harmful calls:      {n_harmful}/{n_total}")
    print(f"  Infrastructure err: {n_infra}/{n_total}")
    print(f"Scores written to {target / 'scores.jsonl'}")


if __name__ == "__main__":
    main()
