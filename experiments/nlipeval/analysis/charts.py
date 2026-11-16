"""Quick-look charts using matplotlib for preliminary evaluation analysis (stage 07).

Produces plain line and bar charts titled "Preliminary".
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_fig1_basic_function(df_basic: pd.DataFrame, out_path: Path | str | None = None) -> None:
    """Plot Figure 1: basic function success rate by rung and API."""
    if df_basic.empty:
        return

    plt.figure(figsize=(8, 5))
    rungs = sorted(df_basic["rung"].unique())
    apis = sorted(df_basic["api"].unique())

    # Filter to NLIP condition
    sub = df_basic[df_basic["condition"] == "NLIP"]
    if sub.empty:
        sub = df_basic

    for api in apis:
        sub_api = sub[sub["api"] == api]
        rates = [sub_api[sub_api["rung"] == r]["rate"].mean() if not sub_api[sub_api["rung"] == r].empty else 0.0 for r in rungs]
        plt.plot(rungs, [r * 100 for r in rates], marker="o", label=f"API {api}")

    plt.title("Preliminary: Figure 1 - Basic Function Success Rate (Stage 2)")
    plt.xlabel("Model Rung")
    plt.ylabel("End-to-End Success (%)")
    plt.ylim(-5, 105)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()

    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_p, dpi=150)
    plt.close()


def plot_fig2_progression(df_prog: pd.DataFrame, out_path: Path | str | None = None) -> None:
    """Plot Figure 2: schema progression (success vs versions behind)."""
    if df_prog.empty:
        return

    plt.figure(figsize=(8, 5))
    sub = df_prog[(df_prog.get("prompt") == "P2") & (df_prog.get("condition") == "NLIP")]
    if sub.empty:
        sub = df_prog

    rungs = sorted(sub["rung"].unique())
    for rung in rungs:
        sub_r = sub[sub["rung"] == rung].sort_values("versions_behind")
        if not sub_r.empty:
            grouped = sub_r.groupby("versions_behind")["rate"].mean()
            plt.plot(grouped.index, grouped.values * 100, marker="o", label=f"Rung {rung}")

    plt.title("Preliminary: Figure 2 - Success vs Versions Behind (Stage 3)")
    plt.xlabel("Versions Behind Server")
    plt.ylabel("End-to-End Success (%)")
    plt.ylim(-5, 105)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()

    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_p, dpi=150)
    plt.close()


def plot_fig5_ak(df_ak: pd.DataFrame, out_path: Path | str | None = None) -> None:
    """Plot Figure 5: A(k) cumulative interaction success curve."""
    if df_ak.empty:
        return

    plt.figure(figsize=(8, 5))
    rungs = sorted(df_ak["rung"].unique())

    for rung in rungs:
        sub_r = df_ak[(df_ak["rung"] == rung) & (df_ak["k"] != "nlip0")].copy()
        if not sub_r.empty:
            sub_r["k_int"] = sub_r["k"].astype(int)
            sub_r = sub_r.sort_values("k_int")
            plt.plot(sub_r["k_int"], sub_r["rate"] * 100, marker="s", label=f"Rung {rung}")

    plt.title("Preliminary: Figure 5 - Cumulative Success A(k)")
    plt.xlabel("Maximum Interactions Allowed (k)")
    plt.ylabel("Cumulative Success (%)")
    plt.ylim(-5, 105)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()

    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_p, dpi=150)
    plt.close()
