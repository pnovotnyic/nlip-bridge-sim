"""NLIP evaluation aggregate analysis and statistics package (stage 07)."""

from nlipeval.analysis.aggregates import (
    compute_ak,
    compute_all_aggregates,
    compute_basic_function,
    compute_breaking,
    compute_breaking_by_instance,
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

__all__ = [
    "wilson_ci",
    "mcnemar_exact_test",
    "paired_intent_bootstrap",
    "load_data",
    "compute_basic_function",
    "compute_interaction_gain",
    "compute_progression",
    "compute_progression_pooled",
    "compute_interaction_gap",
    "compute_breaking",
    "compute_breaking_by_instance",
    "compute_by_change_kind",
    "compute_prompts",
    "compute_ak",
    "compute_by_kind_interaction",
    "compute_needed",
    "compute_effects",
    "compute_cost",
    "compute_headline_claims",
    "compute_all_aggregates",
    "plot_fig1_basic_function",
    "plot_fig2_progression",
    "plot_fig5_ak",
]
