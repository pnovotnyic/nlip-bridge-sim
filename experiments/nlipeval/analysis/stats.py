"""Statistical helpers for NLIP evaluation analysis (stage 07).

Provides Wilson 95% confidence intervals, McNemar exact test,
and paired intent bootstrap resampling.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion.

    Returns (ci_low, ci_high) rounded to 4 decimal places.
    """
    if n <= 0:
        return 0.0, 0.0

    p = k / n
    # Two-sided normal quantile
    z = stats.norm.ppf((1 + confidence) / 2)
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z2 / (4 * n * n)))) / denom

    low = max(0.0, center - half)
    high = min(1.0, center + half)
    return round(low, 4), round(high, 4)


def mcnemar_exact_test(a_only: int, b_only: int) -> float:
    """Perform McNemar's exact two-sided test on discordant pairs.

    Returns the two-sided p-value.
    """
    n_discordant = a_only + b_only
    if n_discordant == 0:
        return 1.0
    # Exact binomial test under H0: p = 0.5
    res = stats.binomtest(a_only, n_discordant, p=0.5, alternative="two-sided")
    return float(res.pvalue)


def paired_intent_bootstrap(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    metric_col: str = "end_to_end",
    intent_col: str = "intent_id",
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Paired bootstrap resampling intents (clusters) for comparing two conditions.

    Because instances belonging to the same intent are correlated across versions,
    we resample intents with replacement and calculate the mean difference.

    Returns a dict with:
      - mean_diff: observed difference in rates (A - B)
      - ci_low, ci_high: 95% bootstrap percentile CI
      - p_value: two-sided bootstrap p-value
    """
    # Merge on task_id / intent
    merged = pd.merge(
        df_a[[intent_col, "task_id", metric_col]],
        df_b[[intent_col, "task_id", metric_col]],
        on=["task_id", intent_col],
        suffixes=("_a", "_b"),
    )
    if merged.empty:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": 1.0, "n_pairs": 0}

    intents = np.unique(merged[intent_col].values)
    n_intents = len(intents)
    if n_intents == 0:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": 1.0, "n_pairs": 0}

    obs_diff = float(merged[f"{metric_col}_a"].astype(float).mean() - merged[f"{metric_col}_b"].astype(float).mean())

    rng = np.random.default_rng(seed)
    boot_diffs = np.empty(n_boot, dtype=float)

    # Group dataframe by intent for fast bootstrap sampling
    grouped = {intent: sub for intent, sub in merged.groupby(intent_col)}

    for i in range(n_boot):
        sample_intents = rng.choice(intents, size=n_intents, replace=True)
        sampled_dfs = [grouped[intent] for intent in sample_intents]
        boot_df = pd.concat(sampled_dfs, ignore_index=True)
        diff = boot_df[f"{metric_col}_a"].astype(float).mean() - boot_df[f"{metric_col}_b"].astype(float).mean()
        boot_diffs[i] = diff

    ci_low = float(np.percentile(boot_diffs, 2.5))
    ci_high = float(np.percentile(boot_diffs, 97.5))

    # Bootstrap p-value under H0: diff = 0
    # Fraction of shifted bootstrap replicates more extreme than observed
    shifted = boot_diffs - obs_diff
    p_val = float(np.mean(np.abs(shifted) >= np.abs(obs_diff)))

    return {
        "mean_diff": round(obs_diff, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "p_value": round(p_val, 4),
        "n_pairs": len(merged),
        "n_intents": n_intents,
    }
