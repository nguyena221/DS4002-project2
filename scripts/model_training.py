"""Explore training data and compare ARIMA/SARIMA on 2024 validation data.

Run in VS Code with pandas, numpy, matplotlib, and statsmodels installed.
Input: data/processed/albemarle_pm25_corrected_poc_without_interpolation.csv
Outputs: output/split_summary.csv and training-only plots in output/figures/.
Model parameters use 2021-2023 only. Test-year values are not forecast or scored.
"""

import pandas as pd
from pathlib import Path

# Find the project folder.
project_root = Path(__file__).resolve().parents[1]

# Load the corrected data. Missing pollution values remain blank.
data = pd.read_csv(
    project_root / "data" / "processed"
    / "albemarle_pm25_corrected_poc_without_interpolation.csv",
    parse_dates=["Date"]
)

if data["Date"].duplicated().any():
    raise ValueError("Duplicate dates found. Check preprocessing before proceeding.")
data = data.set_index("Date").sort_index().asfreq("D")

print("Rows:", len(data))
print("Missing pollution measurements:", data["PM2.5"].isna().sum())
print(data.head().to_string())

# Split by calendar year, never randomly: future information must stay separate.
# Keep missing observations blank in every split.
train = data.loc["2021-01-01":"2023-12-31"].copy()
validation = data.loc["2024-01-01":"2024-12-31"].copy()
test = data.loc["2025-01-01":"2025-12-31"].copy()

output_dir = project_root / "output"
figures_dir = output_dir / "figures"
figures_dir.mkdir(parents=True, exist_ok=True)

# These counts describe availability, not model performance.
summary = pd.DataFrame([
    {
        "split": name,
        "start": frame.index.min().date(),
        "end": frame.index.max().date(),
        "calendar_days": len(frame),
        "observed_days": int(frame["PM2.5"].notna().sum()),
        "missing_days": int(frame["PM2.5"].isna().sum()),
    }
    for name, frame in [
        ("training", train), ("validation", validation), ("test", test)
    ]
])
summary_file = output_dir / "split_summary.csv"
summary.to_csv(summary_file, index=False)
print("\nYear splits:")
print(summary.to_string(index=False))

# Save figures directly so they are available without an interactive plot window.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

fig, ax = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
ax.plot(train.index, train["PM2.5"], color="#176B87", linewidth=0.8)
ax.set_title("Albemarle daily PM2.5 — training data (2021–2023)")
ax.set_xlabel("Date")
ax.set_ylabel("Daily average PM2.5 (µg/m³)")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.grid(axis="y", alpha=0.25)
# NaN values break the line, so it does not bridge missing days.
ax.text(0, -0.23, "Gaps in the line indicate missing measurements; no interpolation.",
        transform=ax.transAxes, fontsize=9)
timeline_file = figures_dir / "training_pm25_over_time.png"
fig.savefig(timeline_file, dpi=160, bbox_inches="tight")
plt.close(fig)

# Describe only observed training measurements, without filled values.
fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
ax.hist(train["PM2.5"].dropna(), bins=35, color="#176B87", edgecolor="white")
ax.set_title("Distribution of observed training PM2.5 (2021–2023)")
ax.set_xlabel("Daily average PM2.5 (µg/m³)")
ax.set_ylabel("Number of days")
ax.grid(axis="y", alpha=0.25)
distribution_file = figures_dir / "training_pm25_distribution.png"
fig.savefig(distribution_file, dpi=160, bbox_inches="tight")
plt.close(fig)

# Exploratory calendar-lag correlations, using only the training period.
# Shift BEFORE dropping missing pairs: otherwise a gap could make readings
# several days apart look consecutive. This is a pairwise correlation diagnostic,
# not a formal ACF significance test or proof of seasonality.
pollution = train["PM2.5"]
lag_rows = []
for lag in range(1, 31):
    pairs = pd.concat(
        [pollution.rename("today"), pollution.shift(lag).rename("earlier")],
        axis=1,
    ).dropna()
    lag_rows.append({
        "days_earlier": lag,
        "correlation": pairs["today"].corr(pairs["earlier"]),
        "observed_pairs": len(pairs),
    })

lag_summary = pd.DataFrame(lag_rows)
lag_table_file = output_dir / "training_lag_correlations.csv"
lag_summary.to_csv(lag_table_file, index=False)

fig, ax = plt.subplots(figsize=(10, 4.5), constrained_layout=True)
colors = ["#C66B20" if lag % 7 == 0 else "#176B87" for lag in range(1, 31)]
ax.bar(lag_summary["days_earlier"], lag_summary["correlation"], color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylim(-1, 1)
ax.set_xticks([1, 2, 3, 7, 14, 21, 28, 30])
ax.set_xlabel("Days earlier (1 = yesterday; 7 = one week earlier)")
ax.set_ylabel("Correlation with today's pollution")
ax.set_title("Training data: similarity to earlier days (2021-2023)")
ax.grid(axis="y", alpha=0.25)
ax.text(0, -0.23,
        "Orange bars mark weekly intervals. Missing pairs are omitted; dates are preserved.",
        transform=ax.transAxes, fontsize=9)
lag_plot_file = figures_dir / "training_lag_correlations.png"
fig.savefig(lag_plot_file, dpi=160, bbox_inches="tight")
plt.close(fig)

print("\nSelected lag comparisons (training only):")
print(lag_summary.loc[
    lag_summary["days_earlier"].isin([1, 2, 3, 7, 14, 21, 28])
].to_string(index=False, float_format=lambda value: f"{value:.3f}"))
print("These are exploratory correlations, not proof of a repeating cycle.")

print("\nSaved:")
for filename in (summary_file, timeline_file, distribution_file,
                 lag_table_file, lag_plot_file):
    print(filename)
print("\nFinished preparing splits and training plots.", flush=True)

# Keep model fitting in a separate, commented module for readability.
try:
    from validation_models import compare_models
except ModuleNotFoundError as error:
    raise SystemExit(
        f"Missing package: {error.name}. Install dependencies in the same Python "
        "environment with: python3 -m pip install numpy pandas matplotlib statsmodels"
    ) from error

# Load the original POC-3-only history for a controlled comparison.
# Keep 2024 targets identical: the experiments differ in their older training data.
original_file = (
    project_root / "data" / "processed"
    / "albemarle_pm25_poc3_without_interpolation.csv"
)
original_data = pd.read_csv(original_file, parse_dates=["Date"])
if original_data["Date"].duplicated().any():
    raise ValueError("Original POC-3 dataset has duplicate dates.")
original_data = original_data.set_index("Date").sort_index().asfreq("D")
if not original_data.index.equals(data.index):
    raise ValueError("The two datasets must have identical calendar dates.")
if not original_data["PM2.5"].isna().equals(data["PM2.5"].isna()):
    raise ValueError("The two datasets must have identical missing dates.")
original_train = original_data.loc[train.index, "PM2.5"]
original_validation = original_data.loc[validation.index, "PM2.5"]
import numpy as np

if not np.allclose(original_validation, validation["PM2.5"], equal_nan=True):
    raise ValueError("Validation measurements differ; comparison requires the same targets.")
if not np.isclose(original_train.iloc[-1], train["PM2.5"].iloc[-1], equal_nan=True):
    raise ValueError("December 31 values differ, affecting the January 1 baseline.")

print("\nEXPERIMENT 1: corrected history, without interpolation", flush=True)
ranking, validation_predictions = compare_models(
    train["PM2.5"], validation["PM2.5"], output_dir
)

# Show the best candidate against actual validation measurements and baseline.
# Save forecasts for every date, but calculate errors only on the common mask.
best_candidate = ranking.loc[
    ranking["model"] != "persistence_baseline"
].iloc[0]["model"]
fig, ax = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
ax.plot(validation_predictions.index, validation_predictions["actual"],
        label="Observed", color="black", linewidth=0.9)
ax.plot(validation_predictions.index, validation_predictions["persistence_baseline"],
        label="Tomorrow equals today", alpha=0.55, linewidth=0.8)
ax.plot(validation_predictions.index, validation_predictions[best_candidate],
        label=best_candidate, alpha=0.8, linewidth=0.9)
ax.set_title("2024 validation: one-day-ahead predictions")
ax.set_xlabel("Target date")
ax.set_ylabel("Daily average PM2.5 (ug/m3)")
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.25)
fig.savefig(figures_dir / "validation_predictions.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print("Saved validation tables, fit log, selection, and prediction plot in output/.")

# Repeat exactly the same candidate grid and evaluation with the original history.
# Separate folders prevent overwriting the corrected experiment's outputs.
print("\nEXPERIMENT 2: original POC-3 history, without interpolation", flush=True)
original_output_dir = output_dir / "original_poc3"
original_output_dir.mkdir(parents=True, exist_ok=True)
original_ranking, original_predictions = compare_models(
    original_train, original_validation, original_output_dir
)
if not original_predictions["scored"].equals(validation_predictions["scored"]):
    raise ValueError("Scored dates differ between experiments.")

combined = pd.concat([
    ranking.assign(dataset="corrected", missing_data="no interpolation"),
    original_ranking.assign(dataset="original_poc3", missing_data="no interpolation"),
], ignore_index=True)
combined["family"] = combined["model"].map(
    lambda name: "baseline" if name == "persistence_baseline"
    else ("SARIMA" if name.startswith("SARIMA") else "ARIMA")
)
combined_file = output_dir / "poc_comparison_all_models.csv"
combined.sort_values("validation_mae").to_csv(combined_file, index=False)

# Best model in each family, per dataset (not just the winning family).
best_by_family = (
    combined.sort_values("validation_mae", kind="stable")
    .drop_duplicates(["dataset", "family"])
    .sort_values(["dataset", "family"])
)
family_file = output_dir / "poc_comparison_best_by_family.csv"
best_by_family.to_csv(family_file, index=False)
print("\nCOMPARISON: best result in each model family")
print(best_by_family[[
    "dataset", "family", "model", "validation_mae",
    "improvement_percent", "scored_days"
]].to_string(index=False))

original_best = original_ranking.loc[
    original_ranking["model"] != "persistence_baseline"
].iloc[0]["model"]
fig, ax = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
ax.plot(validation_predictions.index, validation_predictions["actual"],
        label="Observed", color="black", linewidth=0.9)
ax.plot(validation_predictions.index, validation_predictions[best_candidate],
        label=f"Corrected: {best_candidate}", alpha=0.8, linewidth=0.9)
ax.plot(original_predictions.index, original_predictions[original_best],
        label=f"Original POC 3: {original_best}", alpha=0.7, linewidth=0.9)
ax.set_title("2024 validation: original versus corrected training history")
ax.set_xlabel("Target date")
ax.set_ylabel("Daily average PM2.5 (ug/m3)")
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.25)
fig.savefig(figures_dir / "poc_comparison_predictions.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print(f"\nComparison tables saved: {combined_file} and {family_file}")
print("Both experiments used the same 2024 targets and candidate settings.")
print("No interpolation was performed. 2025 remains unevaluated.")

# Read the forward-filled exports generated in the separate preprocessing
# notebook. Never use the filled column as a scoring target or baseline.
experiment_rankings = [combined]
for dataset_name, original_frame, filled_name in [
    ("original_poc3", original_data, "albemarle_pm25_poc3_forward_filled.csv"),
    ("corrected", data, "albemarle_pm25_corrected_poc_forward_filled.csv"),
]:
    filled_frame = pd.read_csv(
        project_root / "data" / "processed" / filled_name, parse_dates=["Date"]
    )
    if filled_frame["Date"].duplicated().any():
        raise ValueError(f"Duplicate dates in {filled_name}")
    filled_frame = filled_frame.set_index("Date").sort_index().asfreq("D")
    # Restrict experiment inputs to 2021-2024; do not forecast or score 2025.
    supplied = filled_frame.loc["2021":"2024", "PM2.5"]
    originals = original_frame.loc["2021":"2024", "PM2.5"]
    retained_originals = filled_frame.loc["2021":"2024", "PM2.5_Original"]
    if not supplied.index.equals(originals.index):
        raise ValueError(f"Calendar mismatch in {filled_name}")
    if not np.allclose(retained_originals, originals, equal_nan=True):
        raise ValueError(f"Original observations changed in {filled_name}")
    if not np.allclose(supplied, originals.ffill(), equal_nan=True):
        raise ValueError(f"Inputs are not causal forward fills in {filled_name}")

    print(f"\nFORWARD-FILLED INPUTS: {dataset_name}", flush=True)
    experiment_dir = output_dir / f"{dataset_name}_forward_filled"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    filled_ranking, filled_predictions = compare_models(
        original_frame.loc["2021":"2023", "PM2.5"],
        original_frame.loc["2024", "PM2.5"],
        experiment_dir, model_inputs=supplied,
    )
    if not filled_predictions["scored"].equals(validation_predictions["scored"]):
        raise ValueError("Filled experiment changed eligible scoring dates.")
    if not np.allclose(
        filled_predictions["persistence_baseline"],
        validation_predictions["persistence_baseline"], equal_nan=True
    ):
        raise ValueError("Filled experiment changed the observed baseline.")
    filled_ranking = filled_ranking.assign(
        dataset=dataset_name, missing_data="forward filled"
    )
    filled_ranking["family"] = filled_ranking["model"].map(
        lambda name: "baseline" if name == "persistence_baseline"
        else ("SARIMA" if name.startswith("SARIMA") else "ARIMA")
    )
    experiment_rankings.append(filled_ranking)

all_results = pd.concat(experiment_rankings, ignore_index=True)
all_results.sort_values("validation_mae").to_csv(
    output_dir / "gap_filling_comparison_all_models.csv", index=False
)
best_by_experiment = (
    all_results.sort_values("validation_mae", kind="stable")
    .drop_duplicates(["dataset", "missing_data", "family"])
    .sort_values(["dataset", "missing_data", "family"])
)
best_by_experiment.to_csv(
    output_dir / "gap_filling_comparison_best_by_family.csv", index=False
)
print("\nALL FOUR EXPERIMENTS: best result in each model family")
print(best_by_experiment[[
    "dataset", "missing_data", "family", "model", "validation_mae",
    "improvement_percent", "scored_days"
]].to_string(index=False))
print("All experiments used observed answers, the same baseline, and the same scoring dates.")
print("2025 remains unevaluated. Final refitting has not been performed.")

