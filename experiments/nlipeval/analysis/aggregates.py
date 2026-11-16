"""Aggregate generation functions for stages 09, 10, and 11 (stage 07).

Reads sessions and scores, logs exclusions (infrastructure errors),
computes rates and Wilson 95% confidence intervals, and exports standard CSV files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nlipeval.analysis.stats import mcnemar_exact_test, paired_intent_bootstrap, wilson_ci

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
RESULTS_DIR = ROOT / "results"

CHANGE_KINDS = ["renamed", "restructured", "unit_format", "newly_required", "changed_meaning", "removed"]


# --------------------------------------------------------------------------- data loading & merging

def load_data(run_dirs: list[Path | str] | Path | str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Load sessions.jsonl and scores.jsonl from run directories, merge with task metadata.

    Returns (df_clean, exclusion_counts).
    Exclusions: sessions where infra_error is True (termination == 'error_harness').
    """
    if isinstance(run_dirs, (str, Path)):
        run_dirs = [run_dirs]

    session_rows = []
    score_rows = []

    for rd in run_dirs:
        rd = Path(rd)
        sess_file = rd / "sessions.jsonl"
        score_file = rd / "scores.jsonl"

        if sess_file.is_file():
            with open(sess_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        session_rows.append(json.loads(line))

        if score_file.is_file():
            with open(score_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        score_rows.append(json.loads(line))

    if not session_rows:
        return pd.DataFrame(), {"total": 0, "included": 0, "excluded_infra": 0}

    df_sess = pd.DataFrame(session_rows)
    df_score = pd.DataFrame(score_rows)

    if not df_score.empty and "session_id" in df_score.columns:
        df = pd.merge(df_sess, df_score, on="session_id", suffixes=("", "_score"))
    else:
        df = df_sess

    # Merge task metadata if missing
    task_index_file = TASKS_DIR / "INDEX.csv"
    if task_index_file.is_file():
        idx_df = pd.read_csv(task_index_file)
        # Identify columns in idx_df not yet present in df
        cols_to_add = [c for c in idx_df.columns if c not in df.columns]
        if cols_to_add:
            df = pd.merge(df, idx_df[["task_id"] + cols_to_add], on="task_id", how="left")

    total_sessions = len(df)
    infra_mask = df.get("infra_error", False) == True
    n_excluded = int(infra_mask.sum())
    df_clean = df[~infra_mask].copy()
    n_included = len(df_clean)

    exclusions = {
        "total": total_sessions,
        "included": n_included,
        "excluded_infra": n_excluded,
    }

    # Ensure change_tags are lists
    for col in ("change_tags_request", "change_tags_response"):
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(
                lambda v: v if isinstance(v, list) else (v.split("|") if isinstance(v, str) and v else [])
            )

    return df_clean, exclusions


# --------------------------------------------------------------------------- Stage 2 aggregates (Stage 09)

def compute_basic_function(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage2/basic_function.csv.

    Columns: rung, api, condition, n, successes, rate, ci_low, ci_high, request_rate, response_rate, harmful_rate, mean_k
    """
    # Filter matching versions (versions_behind == 0, non-pilot)
    sub = df[(df.get("versions_behind", 0) == 0) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    group_cols = ["client_rung", "api", "condition"]
    available_groups = [c for c in group_cols if c in sub.columns]

    if not sub.empty and available_groups:
        for keys, g in sub.groupby(available_groups):
            if not isinstance(keys, tuple):
                keys = (keys,)
            key_dict = dict(zip(available_groups, keys))
            rung = key_dict.get("client_rung", "unknown")
            api = key_dict.get("api", "unknown")
            cond = key_dict.get("condition", "unknown")

            n = len(g)
            successes = int(g["end_to_end"].sum())
            rate = round(successes / n, 4) if n > 0 else 0.0
            ci_low, ci_high = wilson_ci(successes, n)

            req_succ = int(g["request_correct"].sum())
            req_rate = round(req_succ / n, 4) if n > 0 else 0.0

            resp_succ = int(g["response_correct"].sum())
            resp_rate = round(resp_succ / n, 4) if n > 0 else 0.0

            harm_count = int(g["harmful"].sum())
            harm_rate = round(harm_count / n, 4) if n > 0 else 0.0

            mean_k = round(float(g["k_used"].mean()), 2) if "k_used" in g.columns else 0.0

            rows.append({
                "rung": rung,
                "api": api,
                "condition": cond,
                "n": n,
                "successes": successes,
                "rate": rate,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "request_rate": req_rate,
                "response_rate": resp_rate,
                "harmful_rate": harm_rate,
                "mean_k": mean_k,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_interaction_gain(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage2/interaction_gain.csv.

    Columns: rung, api, nlip_rate, nlip0_rate, gain_points, pairs, nlip_only, nlip0_only, mcnemar_p
    """
    sub = df[(df.get("versions_behind", 0) == 0) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    if not sub.empty:
        rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else []
        apis = sorted(sub["api"].unique()) if "api" in sub.columns else []

        for rung in rungs:
            for api in apis:
                sub_pair = sub[(sub["client_rung"] == rung) & (sub["api"] == api)]
                df_nlip = sub_pair[sub_pair["condition"] == "NLIP"]
                df_nlip0 = sub_pair[sub_pair["condition"] == "NLIP-0"]

                merged = pd.merge(
                    df_nlip[["task_id", "end_to_end"]],
                    df_nlip0[["task_id", "end_to_end"]],
                    on="task_id",
                    suffixes=("_nlip", "_nlip0"),
                )
                pairs = len(merged)
                if pairs == 0:
                    continue

                nlip_succ = int(merged["end_to_end_nlip"].sum())
                nlip0_succ = int(merged["end_to_end_nlip0"].sum())
                nlip_rate = round(nlip_succ / pairs, 4)
                nlip0_rate = round(nlip0_succ / pairs, 4)
                gain_pts = round((nlip_rate - nlip0_rate) * 100, 2)

                nlip_only = int(((merged["end_to_end_nlip"] == True) & (merged["end_to_end_nlip0"] == False)).sum())
                nlip0_only = int(((merged["end_to_end_nlip"] == False) & (merged["end_to_end_nlip0"] == True)).sum())
                p_val = round(mcnemar_exact_test(nlip_only, nlip0_only), 4)

                rows.append({
                    "rung": rung,
                    "api": api,
                    "nlip_rate": nlip_rate,
                    "nlip0_rate": nlip0_rate,
                    "gain_points": gain_pts,
                    "pairs": pairs,
                    "nlip_only": nlip_only,
                    "nlip0_only": nlip0_only,
                    "mcnemar_p": p_val,
                })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


# --------------------------------------------------------------------------- Stage 3 aggregates (Stage 10)

def compute_progression(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/progression.csv.

    Columns: rung, api, client_version, versions_behind, breaking_crossed, breaking_crossed_ops,
             prompt, condition, n, successes, rate, ci_low, ci_high, request_rate, response_rate, harmful_rate, mean_k
    """
    sub = df[df.get("pilot", False) == False].copy()
    rows = []
    group_cols = [
        "client_rung", "api", "client_version", "versions_behind",
        "breaking_crossed", "breaking_crossed_ops", "prompt", "condition",
    ]
    available_groups = [c for c in group_cols if c in sub.columns]

    if not sub.empty and available_groups:
        for keys, g in sub.groupby(available_groups):
            if not isinstance(keys, tuple):
                keys = (keys,)
            kd = dict(zip(available_groups, keys))

            n = len(g)
            successes = int(g["end_to_end"].sum())
            rate = round(successes / n, 4) if n > 0 else 0.0
            ci_low, ci_high = wilson_ci(successes, n)

            req_rate = round(int(g["request_correct"].sum()) / n, 4) if n > 0 else 0.0
            resp_rate = round(int(g["response_correct"].sum()) / n, 4) if n > 0 else 0.0
            harm_rate = round(int(g["harmful"].sum()) / n, 4) if n > 0 else 0.0
            mean_k = round(float(g["k_used"].mean()), 2) if "k_used" in g.columns else 0.0

            rows.append({
                "rung": kd.get("client_rung", "unknown"),
                "api": kd.get("api", "unknown"),
                "client_version": kd.get("client_version", "unknown"),
                "versions_behind": kd.get("versions_behind", 0),
                "breaking_crossed": kd.get("breaking_crossed", 0),
                "breaking_crossed_ops": kd.get("breaking_crossed_ops", 0),
                "prompt": kd.get("prompt", "unknown"),
                "condition": kd.get("condition", "unknown"),
                "n": n,
                "successes": successes,
                "rate": rate,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "request_rate": req_rate,
                "response_rate": resp_rate,
                "harmful_rate": harm_rate,
                "mean_k": mean_k,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_progression_pooled(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/progression_pooled.csv.

    Columns: rung, prompt, condition, n, successes, rate, ci_low, ci_high, request_rate, response_rate, harmful_rate, mean_k
    Pooled per rung, prompt, condition. For P1/P3 pooled over prompt_half only.
    """
    sub = df[df.get("pilot", False) == False].copy()
    rows = []

    if not sub.empty:
        rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]
        prompts = sorted(sub["prompt"].unique()) if "prompt" in sub.columns else ["P2"]
        conditions = sorted(sub["condition"].unique()) if "condition" in sub.columns else ["NLIP"]

        for rung in rungs:
            for prompt in prompts:
                for cond in conditions:
                    g = sub[(sub.get("client_rung") == rung) & (sub.get("prompt") == prompt) & (sub.get("condition") == cond)]
                    if prompt in ("P1", "P3") and "prompt_half" in g.columns:
                        g = g[g["prompt_half"] == True]

                    n = len(g)
                    if n == 0:
                        continue
                    successes = int(g["end_to_end"].sum())
                    rate = round(successes / n, 4)
                    ci_low, ci_high = wilson_ci(successes, n)
                    req_rate = round(int(g["request_correct"].sum()) / n, 4)
                    resp_rate = round(int(g["response_correct"].sum()) / n, 4)
                    harm_rate = round(int(g["harmful"].sum()) / n, 4)
                    mean_k = round(float(g["k_used"].mean()), 2) if "k_used" in g.columns else 0.0

                    rows.append({
                        "rung": rung,
                        "prompt": prompt,
                        "condition": cond,
                        "n": n,
                        "successes": successes,
                        "rate": rate,
                        "ci_low": ci_low,
                        "ci_high": ci_high,
                        "request_rate": req_rate,
                        "response_rate": resp_rate,
                        "harmful_rate": harm_rate,
                        "mean_k": mean_k,
                    })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_interaction_gap(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/interaction_gap.csv (Figure 2b).

    Columns: rung, api, client_version, versions_behind, nlip_rate, nlip0_rate, gap_points, pairs, mcnemar_p
    P2, paired on task_id, all 330 Stage 3 instances (versions_behind >= 1).
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    if not sub.empty:
        group_cols = ["client_rung", "api", "client_version", "versions_behind"]
        avail = [c for c in group_cols if c in sub.columns]
        for keys, g in sub.groupby(avail):
            if not isinstance(keys, tuple):
                keys = (keys,)
            kd = dict(zip(avail, keys))

            df_nlip = g[g["condition"] == "NLIP"]
            df_nlip0 = g[g["condition"] == "NLIP-0"]

            merged = pd.merge(
                df_nlip[["task_id", "end_to_end"]],
                df_nlip0[["task_id", "end_to_end"]],
                on="task_id",
                suffixes=("_nlip", "_nlip0"),
            )
            pairs = len(merged)
            if pairs == 0:
                continue

            nlip_succ = int(merged["end_to_end_nlip"].sum())
            nlip0_succ = int(merged["end_to_end_nlip0"].sum())
            nlip_rate = round(nlip_succ / pairs, 4)
            nlip0_rate = round(nlip0_succ / pairs, 4)
            gap_pts = round((nlip_rate - nlip0_rate) * 100, 2)

            nlip_only = int(((merged["end_to_end_nlip"] == True) & (merged["end_to_end_nlip0"] == False)).sum())
            nlip0_only = int(((merged["end_to_end_nlip"] == False) & (merged["end_to_end_nlip0"] == True)).sum())
            p_val = round(mcnemar_exact_test(nlip_only, nlip0_only), 4)

            rows.append({
                "rung": kd.get("client_rung", "unknown"),
                "api": kd.get("api", "unknown"),
                "client_version": kd.get("client_version", "unknown"),
                "versions_behind": kd.get("versions_behind", 0),
                "nlip_rate": nlip_rate,
                "nlip0_rate": nlip0_rate,
                "gap_points": gap_pts,
                "pairs": pairs,
                "mcnemar_p": p_val,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def _catalogue_version_value() -> dict[tuple[str, str], int]:
    """`catalogue_breaking_crossed` per (api, client_version) from results/specs/catalogue_breaking_crossed.csv."""
    p = RESULTS_DIR / "specs" / "catalogue_breaking_crossed.csv"
    if not p.is_file():
        return {}
    t = pd.read_csv(p)
    return {(r.api, r.client_version): int(r.catalogue_breaking_crossed) for r in t.itertuples()}


def compute_breaking(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/breaking.csv (Figure 3).

    One row per (rung, api, client_version, condition). `catalogue_breaking_crossed` is the version's value
    from results/specs/catalogue_breaking_crossed.csv; `catalogue_breaking_crossed_mean` is the mean of the
    instances' own values (07b D1), which differ from instance to instance.

    Columns: rung, api, client_version, breaking_crossed, breaking_crossed_ops,
             catalogue_breaking_crossed, catalogue_breaking_crossed_mean, condition, rate, ci_low, ci_high
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    version_value = _catalogue_version_value()
    rows = []
    group_cols = ["client_rung", "api", "client_version", "breaking_crossed", "breaking_crossed_ops", "condition"]
    avail = [c for c in group_cols if c in sub.columns]

    if not sub.empty and avail:
        for keys, g in sub.groupby(avail):
            if not isinstance(keys, tuple):
                keys = (keys,)
            kd = dict(zip(avail, keys))

            n = len(g)
            successes = int(g["end_to_end"].sum())
            rate = round(successes / n, 4) if n > 0 else 0.0
            ci_low, ci_high = wilson_ci(successes, n)
            inst = g["catalogue_breaking_crossed"] if "catalogue_breaking_crossed" in g.columns else None
            mean_inst = round(float(inst.mean()), 3) if inst is not None else None
            cell = version_value.get((kd.get("api"), kd.get("client_version")),
                                     int(inst.max()) if inst is not None else 0)

            rows.append({
                "rung": kd.get("client_rung", "unknown"),
                "api": kd.get("api", "unknown"),
                "client_version": kd.get("client_version", "unknown"),
                "breaking_crossed": kd.get("breaking_crossed", 0),
                "breaking_crossed_ops": kd.get("breaking_crossed_ops", 0),
                "catalogue_breaking_crossed": cell,
                "catalogue_breaking_crossed_mean": mean_inst,
                "condition": kd.get("condition", "unknown"),
                "rate": rate,
                "ci_low": ci_low,
                "ci_high": ci_high,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


INSTANCE_BINS = [("0", 0, 0), ("1-2", 1, 2), ("3-5", 3, 5), ("6-10", 6, 10), ("11+", 11, 10**9)]


def compute_breaking_by_instance(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/breaking_by_instance.csv (07b D1).

    Success by each instance's own catalogue count, in the bins 0, 1-2, 3-5, 6-10 and 11+, pooled over
    APIs and versions, for P2 and each condition and rung. Stage 3 instances only (versions_behind >= 1).

    Columns: rung, condition, bin, n, successes, rate, ci_low, ci_high
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    if not sub.empty and "catalogue_breaking_crossed" in sub.columns:
        for (rung, cond), g in sub.groupby(["client_rung", "condition"]):
            for label, lo, hi in INSTANCE_BINS:
                gb = g[(g["catalogue_breaking_crossed"] >= lo) & (g["catalogue_breaking_crossed"] <= hi)]
                n = len(gb)
                succ = int(gb["end_to_end"].sum())
                ci_low, ci_high = wilson_ci(succ, n) if n else (None, None)
                rows.append({"rung": rung, "condition": cond, "bin": label, "n": n, "successes": succ,
                             "rate": round(succ / n, 4) if n else None, "ci_low": ci_low, "ci_high": ci_high})

    res = pd.DataFrame(rows, columns=["rung", "condition", "bin", "n", "successes", "rate", "ci_low", "ci_high"])
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_by_change_kind(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/by_change_kind.csv (Figure 4).

    Columns: change_kind, direction, rung, condition, n_tagged, rate, ci_low, ci_high
    Direction request: request_correct over instances tagged in change_tags_request.
    Direction response: response_correct over instances tagged in change_tags_response.
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]
    conditions = sorted(sub["condition"].unique()) if "condition" in sub.columns else ["NLIP"]

    for kind in CHANGE_KINDS:
        for rung in rungs:
            for cond in conditions:
                sub_cell = sub[(sub.get("client_rung") == rung) & (sub.get("condition") == cond)]

                # Request direction
                req_tagged = sub_cell[sub_cell["change_tags_request"].apply(lambda tags: kind in tags if isinstance(tags, list) else False)]
                n_req = len(req_tagged)
                if n_req > 0:
                    req_succ = int(req_tagged["request_correct"].sum())
                    r_rate = round(req_succ / n_req, 4)
                    ci_l, ci_h = wilson_ci(req_succ, n_req)
                    rows.append({
                        "change_kind": kind,
                        "direction": "request",
                        "rung": rung,
                        "condition": cond,
                        "n_tagged": n_req,
                        "rate": r_rate,
                        "ci_low": ci_l,
                        "ci_high": ci_h,
                    })

                # Response direction
                resp_tagged = sub_cell[sub_cell["change_tags_response"].apply(lambda tags: kind in tags if isinstance(tags, list) else False)]
                n_resp = len(resp_tagged)
                if n_resp > 0:
                    resp_succ = int(resp_tagged["response_correct"].sum())
                    r_rate = round(resp_succ / n_resp, 4)
                    ci_l, ci_h = wilson_ci(resp_succ, n_resp)
                    rows.append({
                        "change_kind": kind,
                        "direction": "response",
                        "rung": rung,
                        "condition": cond,
                        "n_tagged": n_resp,
                        "rate": r_rate,
                        "ci_low": ci_l,
                        "ci_high": ci_h,
                    })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_prompts(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/stage3/prompts.csv (Figure 6).

    Columns: rung, prompt, n, rate, ci_low, ci_high, pairs_vs_p2, only_this, only_p2, mcnemar_p
    All three prompts on prompt_half only, paired by task_id vs P2.
    """
    sub = df[(df.get("prompt_half", False) == True) & (df.get("pilot", False) == False)].copy()
    if "condition" in sub.columns:
        sub = sub[sub["condition"] == "NLIP"]

    rows = []
    rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]
    prompts = ["P1", "P2", "P3"]

    for rung in rungs:
        sub_rung = sub[sub.get("client_rung") == rung]
        df_p2 = sub_rung[sub_rung.get("prompt") == "P2"]

        for prompt in prompts:
            df_p = sub_rung[sub_rung.get("prompt") == prompt]
            n = len(df_p)
            if n == 0:
                continue

            successes = int(df_p["end_to_end"].sum())
            rate = round(successes / n, 4)
            ci_low, ci_high = wilson_ci(successes, n)

            # Pair vs P2
            merged = pd.merge(
                df_p[["task_id", "end_to_end"]],
                df_p2[["task_id", "end_to_end"]],
                on="task_id",
                suffixes=("_this", "_p2"),
            )
            pairs = len(merged)
            only_this = int(((merged["end_to_end_this"] == True) & (merged["end_to_end_p2"] == False)).sum())
            only_p2 = int(((merged["end_to_end_this"] == False) & (merged["end_to_end_p2"] == True)).sum())
            p_val = round(mcnemar_exact_test(only_this, only_p2), 4)

            rows.append({
                "rung": rung,
                "prompt": prompt,
                "n": n,
                "rate": rate,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "pairs_vs_p2": pairs,
                "only_this": only_this,
                "only_p2": only_p2,
                "mcnemar_p": p_val,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


# --------------------------------------------------------------------------- Stage 11 aggregates (Interaction)

def compute_ak(df: pd.DataFrame, out_path: Path | str | None = None, is_stage2: bool = False) -> pd.DataFrame:
    """Compute results/interaction/ak.csv (Figure 5) or stage2_ak.csv.

    Columns: rung, k, n, successes, rate, ci_low, ci_high
    For k = 0..5: share of NLIP sessions end-to-end correct with <= k interactions.
    Row k = 'nlip0': NLIP-0 rate on same instances.
    """
    if is_stage2:
        sub = df[(df.get("versions_behind", 0) == 0) & (df.get("pilot", False) == False)].copy()
    else:
        sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()

    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]

    for rung in rungs:
        sub_rung = sub[sub.get("client_rung") == rung]
        nlip = sub_rung[sub_rung.get("condition") == "NLIP"]
        nlip0 = sub_rung[sub_rung.get("condition") == "NLIP-0"]
        n_nlip = len(nlip)

        for k in range(6):
            if n_nlip == 0:
                continue
            # Successes with k_used <= k
            succ_k = int(((nlip["end_to_end"] == True) & (nlip["k_used"] <= k)).sum())
            rate_k = round(succ_k / n_nlip, 4)
            ci_l, ci_h = wilson_ci(succ_k, n_nlip)
            rows.append({
                "rung": rung,
                "k": str(k),
                "n": n_nlip,
                "successes": succ_k,
                "rate": rate_k,
                "ci_low": ci_l,
                "ci_high": ci_h,
            })

        # NLIP-0 row
        n_nlip0 = len(nlip0)
        if n_nlip0 > 0:
            succ_nlip0 = int(nlip0["end_to_end"].sum())
            rate_0 = round(succ_nlip0 / n_nlip0, 4)
            ci_l, ci_h = wilson_ci(succ_nlip0, n_nlip0)
            rows.append({
                "rung": rung,
                "k": "nlip0",
                "n": n_nlip0,
                "successes": succ_nlip0,
                "rate": rate_0,
                "ci_low": ci_l,
                "ci_high": ci_h,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_by_kind_interaction(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/interaction/by_kind.csv (Figure 5b).

    Columns: change_kind, rung, n_tagged, nlip_rate, nlip0_rate, gain_points, pairs, mcnemar_p
    For each rung and rung='all', end-to-end success and union of request & response tags.
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    rungs = list(sorted(sub["client_rung"].unique())) if "client_rung" in sub.columns else []
    rungs_with_all = rungs + (["all"] if len(rungs) > 1 else [])

    for kind in CHANGE_KINDS:
        for rung in rungs_with_all:
            sub_r = sub if rung == "all" else sub[sub.get("client_rung") == rung]
            # Union of request and response tags
            tagged = sub_r[sub_r.apply(
                lambda row: (kind in (row.get("change_tags_request") or [])) or (kind in (row.get("change_tags_response") or [])),
                axis=1,
            )]

            df_nlip = tagged[tagged["condition"] == "NLIP"]
            df_nlip0 = tagged[tagged["condition"] == "NLIP-0"]

            merged = pd.merge(
                df_nlip[["task_id", "end_to_end"]],
                df_nlip0[["task_id", "end_to_end"]],
                on="task_id",
                suffixes=("_nlip", "_nlip0"),
            )
            pairs = len(merged)
            if pairs == 0:
                continue

            nlip_succ = int(merged["end_to_end_nlip"].sum())
            nlip0_succ = int(merged["end_to_end_nlip0"].sum())
            nlip_rate = round(nlip_succ / pairs, 4)
            nlip0_rate = round(nlip0_succ / pairs, 4)
            gain_pts = round((nlip_rate - nlip0_rate) * 100, 2)

            nlip_only = int(((merged["end_to_end_nlip"] == True) & (merged["end_to_end_nlip0"] == False)).sum())
            nlip0_only = int(((merged["end_to_end_nlip"] == False) & (merged["end_to_end_nlip0"] == True)).sum())
            p_val = round(mcnemar_exact_test(nlip_only, nlip0_only), 4)

            rows.append({
                "change_kind": kind,
                "rung": rung,
                "n_tagged": pairs,
                "nlip_rate": nlip_rate,
                "nlip0_rate": nlip0_rate,
                "gain_points": gain_pts,
                "pairs": pairs,
                "mcnemar_p": p_val,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_needed(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/interaction/needed.csv (Figure 5c).

    Columns: rung, bucket, n, share
    Buckets for NLIP sessions: done_0_interactions, done_1_interaction, done_2_interactions,
                               done_3_to_5_interactions, not_done
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False) & (df.get("condition") == "NLIP")].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]

    for rung in rungs:
        sub_r = sub[sub.get("client_rung") == rung]
        n_total = len(sub_r)
        if n_total == 0:
            continue

        b0 = int(((sub_r["end_to_end"] == True) & (sub_r["k_used"] == 0)).sum())
        b1 = int(((sub_r["end_to_end"] == True) & (sub_r["k_used"] == 1)).sum())
        b2 = int(((sub_r["end_to_end"] == True) & (sub_r["k_used"] == 2)).sum())
        b35 = int(((sub_r["end_to_end"] == True) & (sub_r["k_used"] >= 3) & (sub_r["k_used"] <= 5)).sum())
        b_not = int((sub_r["end_to_end"] == False).sum())

        buckets = [
            ("done_0_interactions", b0),
            ("done_1_interaction", b1),
            ("done_2_interactions", b2),
            ("done_3_to_5_interactions", b35),
            ("not_done", b_not),
        ]
        for name, count in buckets:
            share = round(count / n_total, 4)
            rows.append({
                "rung": rung,
                "bucket": name,
                "n": count,
                "share": share,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def _has_missing_info(v: Any) -> bool:
    """`missing_info` is a list in sessions merged from task files, or a '|'-joined string from INDEX.csv."""
    if isinstance(v, (list, tuple, np.ndarray)):
        return len(v) > 0
    return isinstance(v, str) and v.strip() not in ("", "[]", "nan")


def compute_effects(df: pd.DataFrame, out_path: Path | str | None = None, is_stage2: bool = False) -> pd.DataFrame:
    """Compute results/interaction/effects.csv (Table 3) or stage2_effects.csv.

    Columns: rung, questions_per_task, unneeded_share, caught_share, harmful_nlip, harmful_nlip0, n_nlip, n_nlip0,
             n_missing_info_tasks, asked_when_needed_share

    `n_missing_info_tasks` is the number of NLIP sessions on tasks with a non-empty `missing_info`;
    `asked_when_needed_share` is the share of those sessions in which the server asked for at least one
    missing field (`questions_needed` > 0). Both are 07b D2.
    """
    if is_stage2:
        sub = df[(df.get("versions_behind", 0) == 0) & (df.get("pilot", False) == False)].copy()
    else:
        sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()

    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]

    for rung in rungs:
        sub_r = sub[sub.get("client_rung") == rung]
        nlip = sub_r[sub_r.get("condition") == "NLIP"]
        nlip0 = sub_r[sub_r.get("condition") == "NLIP-0"]

        n_nlip = len(nlip)
        n_nlip0 = len(nlip0)
        if n_nlip == 0:
            continue

        q_needed = int(nlip.get("questions_needed", pd.Series([0])).sum())
        q_unneeded = int(nlip.get("questions_unneeded", pd.Series([0])).sum())
        tot_q = q_needed + q_unneeded

        q_per_task = round(tot_q / n_nlip, 2)
        unneeded_share = round(q_unneeded / tot_q, 4) if tot_q > 0 else 0.0

        wrong_caught = int(nlip.get("wrong_plans_caught", pd.Series([0])).sum())
        # caught_share: wrong plans caught per task or over wrong plans
        caught_share = round(wrong_caught / n_nlip, 4)

        harm_nlip = round(int(nlip["harmful"].sum()) / n_nlip, 4) if n_nlip > 0 else 0.0
        harm_nlip0 = round(int(nlip0["harmful"].sum()) / n_nlip0, 4) if n_nlip0 > 0 else 0.0

        if "missing_info" in nlip.columns:
            has_missing = nlip["missing_info"].apply(_has_missing_info)
            needed_sessions = nlip[has_missing]
        else:
            needed_sessions = nlip.iloc[0:0]
        n_missing = len(needed_sessions)
        asked_when_needed = (round(int((needed_sessions["questions_needed"] > 0).sum()) / n_missing, 4)
                             if n_missing else None)

        rows.append({
            "rung": rung,
            "questions_per_task": q_per_task,
            "unneeded_share": unneeded_share,
            "caught_share": caught_share,
            "harmful_nlip": harm_nlip,
            "harmful_nlip0": harm_nlip0,
            "n_nlip": n_nlip,
            "n_nlip0": n_nlip0,
            "n_missing_info_tasks": n_missing,
            "asked_when_needed_share": asked_when_needed,
        })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_cost(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/interaction/cost.csv (§6.5).

    Columns: rung, condition, calls_per_task, tokens_in_per_task, tokens_out_per_task,
             reasoning_tokens_per_task, seconds_per_task, success_rate, tokens_per_correct, seconds_per_correct
    """
    sub = df[(df.get("versions_behind", 0) >= 1) & (df.get("pilot", False) == False)].copy()
    if "prompt" in sub.columns:
        sub = sub[sub["prompt"] == "P2"]

    rows = []
    rungs = sorted(sub["client_rung"].unique()) if "client_rung" in sub.columns else ["unknown"]
    conditions = ["NLIP", "NLIP-0"]

    for rung in rungs:
        for cond in conditions:
            g = sub[(sub.get("client_rung") == rung) & (sub.get("condition") == cond)]
            n = len(g)
            if n == 0:
                continue

            successes = int(g["end_to_end"].sum())
            succ_rate = round(successes / n, 4)

            # Calls
            calls_c = g.get("calls_client", pd.Series([0])).fillna(0).astype(float)
            calls_s = g.get("calls_server", pd.Series([0])).fillna(0).astype(float)
            tot_calls = calls_c + calls_s
            calls_per_task = round(float(tot_calls.mean()), 2)

            # Tokens
            def _extract_tok(row: Any, key: str) -> float:
                tok = row.get("tokens") if isinstance(row, dict) else None
                if isinstance(tok, dict):
                    v = tok.get(key)
                    return float(v) if v is not None else 0.0
                return 0.0

            tok_in = g.apply(lambda r: _extract_tok(r, "client_in") + _extract_tok(r, "server_in"), axis=1)
            tok_out = g.apply(lambda r: _extract_tok(r, "client_out") + _extract_tok(r, "server_out"), axis=1)
            tok_reason = g.apply(lambda r: _extract_tok(r, "reasoning"), axis=1)

            t_in_mean = round(float(tok_in.mean()), 1)
            t_out_mean = round(float(tok_out.mean()), 1)
            t_reason_mean = round(float(tok_reason.mean()), 1)

            wall_sec = g.get("wall_seconds", pd.Series([0])).fillna(0).astype(float)
            sec_per_task = round(float(wall_sec.mean()), 2)

            tot_tok_sum = float((tok_in + tok_out).sum())
            tot_sec_sum = float(wall_sec.sum())

            tok_per_correct = round(tot_tok_sum / successes, 1) if successes > 0 else 0.0
            sec_per_correct = round(tot_sec_sum / successes, 2) if successes > 0 else 0.0

            rows.append({
                "rung": rung,
                "condition": cond,
                "calls_per_task": calls_per_task,
                "tokens_in_per_task": t_in_mean,
                "tokens_out_per_task": t_out_mean,
                "reasoning_tokens_per_task": t_reason_mean,
                "seconds_per_task": sec_per_task,
                "success_rate": succ_rate,
                "tokens_per_correct": tok_per_correct,
                "seconds_per_correct": sec_per_correct,
            })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


# --------------------------------------------------------------------------- Headline claims (Stage 11 §7)

HEADLINE_CLAIMS_SPEC = [
    (1, "R4 baseline matches single-turn spec execution on Stage 2", "basic_function rate (R4 NLIP)", "results/stage2/basic_function.csv"),
    (2, "NLIP outperforms NLIP-0 across all version gaps", "interaction_gap gap_points > 0", "results/stage3/interaction_gap.csv"),
    (3, "Harmful call rate is lower under NLIP than NLIP-0", "effects harmful_nlip vs harmful_nlip0", "results/interaction/effects.csv"),
    (4, "Interactive adaptation success degrades gracefully with schema distance", "progression rate vs versions_behind", "results/stage3/progression.csv"),
    (5, "Wrong plans are caught by client clarification/corrections", "effects caught_share > 0", "results/interaction/effects.csv"),
    (6, "Token cost of interaction is offset by higher success rate", "cost tokens_per_correct NLIP vs NLIP-0", "results/interaction/cost.csv"),
    (7, "Renamed and restructured changes benefit most from interaction", "by_kind gain_points across change kinds", "results/interaction/by_kind.csv"),
    (8, "P2 prompt achieves best balance of token efficiency and accuracy", "prompts rate and mcnemar_p vs P1/P3", "results/stage3/prompts.csv"),
]


def compute_headline_claims(df: pd.DataFrame, out_path: Path | str | None = None) -> pd.DataFrame:
    """Compute results/headline_claims.csv.

    Columns: claim_no, claim_text, measure, measured_value, ci, direction_as_claimed, files
    """
    rows = []
    # If df is empty or preliminary, populate claims table with measured values or placeholders
    for c_no, c_txt, measure, rel_file in HEADLINE_CLAIMS_SPEC:
        measured_val = "N/A"
        ci_str = "N/A"
        direction = "unclear"

        if not df.empty:
            if c_no == 1:
                sub = df[(df.get("client_rung") == "R4") & (df.get("condition") == "NLIP") & (df.get("versions_behind", 0) == 0)]
                if not sub.empty:
                    s = int(sub["end_to_end"].sum())
                    n = len(sub)
                    r = s / n
                    l, h = wilson_ci(s, n)
                    measured_val = f"{r*100:.1f}% ({s}/{n})"
                    ci_str = f"[{l*100:.1f}%, {h*100:.1f}%]"
                    direction = "yes" if r >= 0.95 else "no"

            elif c_no == 2:
                # NLIP vs NLIP-0 across stage 3
                nlip = df[(df.get("condition") == "NLIP") & (df.get("versions_behind", 0) >= 1)]
                nlip0 = df[(df.get("condition") == "NLIP-0") & (df.get("versions_behind", 0) >= 1)]
                if not nlip.empty and not nlip0.empty:
                    r1 = nlip["end_to_end"].mean()
                    r0 = nlip0["end_to_end"].mean()
                    diff = (r1 - r0) * 100
                    measured_val = f"+{diff:.1f} pts"
                    direction = "yes" if diff > 0 else "no"

            elif c_no == 3:
                nlip = df[(df.get("condition") == "NLIP") & (df.get("versions_behind", 0) >= 1)]
                nlip0 = df[(df.get("condition") == "NLIP-0") & (df.get("versions_behind", 0) >= 1)]
                if not nlip.empty and not nlip0.empty:
                    h1 = nlip["harmful"].mean() * 100
                    h0 = nlip0["harmful"].mean() * 100
                    measured_val = f"NLIP: {h1:.1f}% vs NLIP-0: {h0:.1f}%"
                    direction = "yes" if h1 <= h0 else "no"

        rows.append({
            "claim_no": c_no,
            "claim_text": c_txt,
            "measure": measure,
            "measured_value": measured_val,
            "ci": ci_str,
            "direction_as_claimed": direction,
            "files": rel_file,
        })

    res = pd.DataFrame(rows)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(out_p, index=False)
    return res


def compute_all_aggregates(run_dirs: list[Path | str] | Path | str, base_results_dir: Path | str = RESULTS_DIR) -> dict[str, Any]:
    """Compute and write all aggregate tables across stages 09, 10, and 11."""
    df, exclusions = load_data(run_dirs)
    res_dir = Path(base_results_dir)

    outputs = {}
    outputs["basic_function"] = compute_basic_function(df, res_dir / "stage2" / "basic_function.csv")
    outputs["interaction_gain"] = compute_interaction_gain(df, res_dir / "stage2" / "interaction_gain.csv")
    outputs["progression"] = compute_progression(df, res_dir / "stage3" / "progression.csv")
    outputs["progression_pooled"] = compute_progression_pooled(df, res_dir / "stage3" / "progression_pooled.csv")
    outputs["interaction_gap"] = compute_interaction_gap(df, res_dir / "stage3" / "interaction_gap.csv")
    outputs["breaking"] = compute_breaking(df, res_dir / "stage3" / "breaking.csv")
    outputs["breaking_by_instance"] = compute_breaking_by_instance(df, res_dir / "stage3" / "breaking_by_instance.csv")
    outputs["by_change_kind"] = compute_by_change_kind(df, res_dir / "stage3" / "by_change_kind.csv")
    outputs["prompts"] = compute_prompts(df, res_dir / "stage3" / "prompts.csv")
    outputs["ak"] = compute_ak(df, res_dir / "interaction" / "ak.csv")
    outputs["by_kind"] = compute_by_kind_interaction(df, res_dir / "interaction" / "by_kind.csv")
    outputs["needed"] = compute_needed(df, res_dir / "interaction" / "needed.csv")
    outputs["effects"] = compute_effects(df, res_dir / "interaction" / "effects.csv")
    outputs["cost"] = compute_cost(df, res_dir / "interaction" / "cost.csv")
    outputs["stage2_ak"] = compute_ak(df, res_dir / "interaction" / "stage2_ak.csv", is_stage2=True)
    outputs["stage2_effects"] = compute_effects(df, res_dir / "interaction" / "stage2_effects.csv", is_stage2=True)
    outputs["headline_claims"] = compute_headline_claims(df, res_dir / "headline_claims.csv")

    return {
        "exclusions": exclusions,
        "tables": {k: len(v) for k, v in outputs.items()},
    }
