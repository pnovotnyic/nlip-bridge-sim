"""Tests for NLIP evaluation analysis and statistics (stage 07).

Tests:
  1. Wilson 95% confidence intervals
  2. McNemar exact test
  3. Paired intent bootstrap
  4. Aggregate tables generation across stages 09, 10, 11
  5. Infrastructure error exclusions logging
  6. Chart plotting functions
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from nlipeval.analysis.aggregates import (
    compute_ak,
    compute_all_aggregates,
    compute_basic_function,
    compute_breaking,
    compute_by_change_kind,
    compute_by_kind_interaction,
    compute_cost,
    compute_effects,
    compute_headline_claims,
    compute_interaction_gain,
    compute_interaction_gap,
    compute_needed,
    compute_progression,
    compute_progression_pooled,
    compute_prompts,
    load_data,
)
from nlipeval.analysis.charts import (
    plot_fig1_basic_function,
    plot_fig2_progression,
    plot_fig5_ak,
)
from nlipeval.analysis.stats import (
    mcnemar_exact_test,
    paired_intent_bootstrap,
    wilson_ci,
)

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- 1. Wilson intervals

def test_wilson_ci():
    # Zero sample
    assert wilson_ci(0, 0) == (0.0, 0.0)

    # 10 / 10 (100%)
    low, high = wilson_ci(10, 10)
    assert 0.70 < low < 1.0
    assert high == 1.0

    # 0 / 10 (0%)
    low, high = wilson_ci(0, 10)
    assert low == 0.0
    assert 0.0 < high < 0.35

    # 50 / 100 (50%)
    low, high = wilson_ci(50, 100)
    assert 0.40 < low < 0.50
    assert 0.50 < high < 0.60


# --------------------------------------------------------------------------- 2. McNemar exact test

def test_mcnemar_exact():
    # Identical
    assert mcnemar_exact_test(0, 0) == 1.0
    assert mcnemar_exact_test(10, 10) == 1.0

    # Significant asymmetry
    p = mcnemar_exact_test(20, 2)
    assert p < 0.01

    # Small sample
    p2 = mcnemar_exact_test(1, 0)
    assert p2 == 1.0  # 2 * 0.5^1 = 1.0


# --------------------------------------------------------------------------- 3. Paired intent bootstrap

def test_paired_intent_bootstrap():
    df_a = pd.DataFrame([
        {"intent_id": "m01", "task_id": "L1-m01-v1.0.0", "end_to_end": True},
        {"intent_id": "m02", "task_id": "L1-m02-v1.0.0", "end_to_end": True},
        {"intent_id": "m03", "task_id": "L1-m03-v1.0.0", "end_to_end": True},
        {"intent_id": "m04", "task_id": "L1-m04-v1.0.0", "end_to_end": True},
    ])
    df_b = pd.DataFrame([
        {"intent_id": "m01", "task_id": "L1-m01-v1.0.0", "end_to_end": False},
        {"intent_id": "m02", "task_id": "L1-m02-v1.0.0", "end_to_end": False},
        {"intent_id": "m03", "task_id": "L1-m03-v1.0.0", "end_to_end": False},
        {"intent_id": "m04", "task_id": "L1-m04-v1.0.0", "end_to_end": True},
    ])

    res = paired_intent_bootstrap(df_a, df_b, n_boot=200, seed=42)
    assert res["n_pairs"] == 4
    assert res["n_intents"] == 4
    assert res["mean_diff"] == 0.75
    assert res["ci_low"] > 0.0


# --------------------------------------------------------------------------- 4. Aggregate computations

@pytest.fixture
def sample_dataset(tmp_path: Path) -> Path:
    """Create a mock run directory with sessions and scores for testing aggregates."""
    run_dir = tmp_path / "mock_run"
    run_dir.mkdir()

    sessions = []
    scores = []

    tasks = [
        ("L1-m01-v1.0.0", "m01", "L1", "v1.0.0", 0, 0, 0, True, False, ["device"], ["device"]),
        ("L1-m02-v1.0.0", "m02", "L1", "v1.0.0", 0, 0, 0, False, False, ["device"], ["device"]),
        ("L2-m01-v0.1.0", "m01", "L2", "v0.1.0", 4, 8, 8, True, False, ["renamed"], ["unit_format"]),
        ("L3-m01-v0.8.1", "m01", "L3", "v0.8.1", 5, 21, 14, True, False, ["renamed", "newly_required"], ["unit_format"]),
    ]

    sid = 0
    for tid, intent, api, c_ver, v_beh, brk, brk_ops, p_half, pilot, c_req, c_resp in tasks:
        for rung in ["R1", "R4"]:
            for cond in ["NLIP", "NLIP-0"]:
                for prompt in (["P2"] if v_beh == 0 else ["P1", "P2", "P3"]):
                    sid += 1
                    s_id = f"s-{sid}"
                    is_infra = (sid == 1)  # Make 1 session an infra error

                    sess = {
                        "schema_version": "1",
                        "session_id": s_id,
                        "task_id": tid,
                        "intent_id": intent,
                        "api": api,
                        "client_version": c_ver,
                        "server_version": "v1.0.0" if api == "L1" else "v3.0.0" if api == "L2" else "v1.1.0",
                        "versions_behind": v_beh,
                        "breaking_crossed": brk,
                        "breaking_crossed_ops": brk_ops,
                        "catalogue_breaking_crossed": brk,
                        "prompt_half": p_half,
                        "pilot": pilot,
                        "client_rung": rung,
                        "server_rung": rung,
                        "prompt": prompt,
                        "condition": cond,
                        "termination": "error_harness" if is_infra else "final",
                        "n_interactions": 1 if cond == "NLIP" else 0,
                        "calls_client": 2,
                        "calls_server": 2,
                        "wall_seconds": 1.5,
                        "tokens": {"client_in": 100, "client_out": 50, "server_in": 120, "server_out": 60, "reasoning": 0},
                        "change_tags_request": c_req,
                        "change_tags_response": c_resp,
                        "missing_info": ["device.phoneNumber"] if tid == "L3-m01-v0.8.1" else [],
                    }
                    sessions.append(sess)

                    # Score
                    e2e = (rung == "R4" or cond == "NLIP") and not is_infra
                    sc = {
                        "schema_version": "1",
                        "session_id": s_id,
                        "scorer_version": "1.0.0",
                        "infra_error": is_infra,
                        "request_correct": e2e,
                        "request_mismatches": [] if e2e else ["error"],
                        "response_correct": e2e,
                        "response_mismatches": [] if e2e else ["error"],
                        "status_correct": True,
                        "end_to_end": e2e,
                        "harmful": not e2e and not is_infra,
                        "harmful_reason": None if (e2e or is_infra) else "test_harm",
                        "declined": False,
                        "correct_decline": False,
                        "k_used": 1 if cond == "NLIP" else 0,
                        "questions_needed": 1 if (cond == "NLIP" and rung == "R4") else 0,
                        "questions_unneeded": 0,
                        "wrong_plans_caught": 0,
                        "first_plan_correct": True,
                        "plan_correct_by_turn": [True],
                    }
                    scores.append(sc)

    with open(run_dir / "sessions.jsonl", "w", encoding="utf-8") as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")

    with open(run_dir / "scores.jsonl", "w", encoding="utf-8") as f:
        for sc in scores:
            f.write(json.dumps(sc) + "\n")

    return run_dir


def test_aggregates_computation(sample_dataset: Path, tmp_path: Path):
    """Test computation of all stage aggregate CSV files."""
    out_res = tmp_path / "results"
    summary = compute_all_aggregates(sample_dataset, base_results_dir=out_res)

    assert summary["exclusions"]["excluded_infra"] == 1
    assert summary["exclusions"]["included"] == summary["exclusions"]["total"] - 1

    # Check that CSV files were created
    assert (out_res / "stage2" / "basic_function.csv").is_file()
    assert (out_res / "stage2" / "interaction_gain.csv").is_file()
    assert (out_res / "stage3" / "progression.csv").is_file()
    assert (out_res / "stage3" / "progression_pooled.csv").is_file()
    assert (out_res / "stage3" / "interaction_gap.csv").is_file()
    assert (out_res / "stage3" / "breaking.csv").is_file()
    assert (out_res / "stage3" / "breaking_by_instance.csv").is_file()
    assert (out_res / "stage3" / "by_change_kind.csv").is_file()
    assert (out_res / "stage3" / "prompts.csv").is_file()
    assert (out_res / "interaction" / "ak.csv").is_file()
    assert (out_res / "interaction" / "by_kind.csv").is_file()
    assert (out_res / "interaction" / "needed.csv").is_file()
    assert (out_res / "interaction" / "effects.csv").is_file()
    assert (out_res / "interaction" / "cost.csv").is_file()
    assert (out_res / "headline_claims.csv").is_file()

    # Verify column structure of basic_function.csv
    bf_df = pd.read_csv(out_res / "stage2" / "basic_function.csv")
    expected_bf_cols = ["rung", "api", "condition", "n", "successes", "rate", "ci_low", "ci_high", "request_rate", "response_rate", "harmful_rate", "mean_k"]
    assert list(bf_df.columns) == expected_bf_cols


def test_quick_look_charts(sample_dataset: Path, tmp_path: Path):
    """Test generating quick-look charts."""
    df, _ = load_data(sample_dataset)
    df_bf = compute_basic_function(df)
    df_prog = compute_progression(df)
    df_ak = compute_ak(df)

    p1 = tmp_path / "fig1.png"
    p2 = tmp_path / "fig2.png"
    p5 = tmp_path / "fig5.png"

    plot_fig1_basic_function(df_bf, p1)
    plot_fig2_progression(df_prog, p2)
    plot_fig5_ak(df_ak, p5)

    assert p1.is_file()
    assert p2.is_file()
    assert p5.is_file()


# --------------------------------------------------------------------------- 5. Stage 07b D: breaking and effects

def test_breaking_csv_has_cell_value_and_instance_mean(sample_dataset: Path):
    from nlipeval.analysis.aggregates import compute_breaking
    df, _ = load_data(sample_dataset)
    # give the two stage 3 tasks different per-instance counts
    df.loc[df["task_id"] == "L2-m01-v0.1.0", "catalogue_breaking_crossed"] = 6
    b = compute_breaking(df)
    assert {"catalogue_breaking_crossed", "catalogue_breaking_crossed_mean"} <= set(b.columns)
    row = b[(b["api"] == "L2") & (b["client_version"] == "v0.1.0")].iloc[0]
    assert row["catalogue_breaking_crossed"] == 13        # results/specs/catalogue_breaking_crossed.csv
    assert row["catalogue_breaking_crossed_mean"] == 6    # the instances' own values


def test_breaking_by_instance_bins(sample_dataset: Path):
    from nlipeval.analysis.aggregates import compute_breaking_by_instance
    df, _ = load_data(sample_dataset)
    df.loc[df["task_id"] == "L2-m01-v0.1.0", "catalogue_breaking_crossed"] = 6     # bin 6-10
    df.loc[df["task_id"] == "L3-m01-v0.8.1", "catalogue_breaking_crossed"] = 15    # bin 11+
    b = compute_breaking_by_instance(df)
    assert list(b.columns) == ["rung", "condition", "bin", "n", "successes", "rate", "ci_low", "ci_high"]
    assert set(b["bin"]) == {"0", "1-2", "3-5", "6-10", "11+"}
    assert (b[b["bin"].isin(["0", "1-2", "3-5"])]["n"] == 0).all()
    r4 = b[(b["rung"] == "R4") & (b["condition"] == "NLIP")].set_index("bin")
    assert r4.loc["6-10", "n"] == 1 and r4.loc["11+", "n"] == 1
    assert r4.loc["11+", "rate"] == 1.0
    # only P2 sessions, only versions_behind >= 1: n sums to the P2 stage 3 sessions of that rung and condition
    sub = df[(df["versions_behind"] >= 1) & (df["prompt"] == "P2") & (df["client_rung"] == "R4") & (df["condition"] == "NLIP")]
    assert r4["n"].sum() == len(sub)


def test_effects_missing_info_columns(sample_dataset: Path):
    from nlipeval.analysis.aggregates import compute_effects
    df, _ = load_data(sample_dataset)
    e = compute_effects(df).set_index("rung")
    assert {"n_missing_info_tasks", "asked_when_needed_share"} <= set(e.columns)
    # R4 NLIP sessions on the missing-info task (L3 v0.8.1, P2) asked a needed question; R1 sessions did not
    assert e.loc["R4", "n_missing_info_tasks"] == 1 and e.loc["R4", "asked_when_needed_share"] == 1.0
    assert e.loc["R1", "n_missing_info_tasks"] == 1 and e.loc["R1", "asked_when_needed_share"] == 0.0
