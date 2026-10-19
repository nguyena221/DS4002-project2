"""Check the selected corrected-data model without using 2025.

Run after model_training.py: python3 scripts/model_diagnostics.py
Reads the saved selection/predictions, refits on 2021-2023 only, and writes
diagnostics under output/diagnostics/. No settings are searched or changed.
Requires pandas, numpy, matplotlib, statsmodels (and its scipy dependency).
"""

import ast
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.graphics.gofplots import qqplot


root = Path(__file__).resolve().parents[1]
output = root / "output"
destination = output / "diagnostics"
destination.mkdir(parents=True, exist_ok=True)
selection = json.loads((output / "validation_selection.json").read_text())
chosen = selection["best_candidate"]
if chosen is None:
    raise ValueError("No selected candidate. Run model_training.py first.")

# Only training observations enter the fit. Nothing from 2025 enters diagnostics.
data = pd.read_csv(
    root / "data/processed/albemarle_pm25_corrected_poc_without_interpolation.csv",
    parse_dates=["Date"], index_col="Date",
).sort_index().asfreq("D")
training = data.loc["2021":"2023", "PM2.5"]
validation = data.loc["2024", "PM2.5"]
predictions = pd.read_csv(output / "validation_predictions.csv",
                          parse_dates=["Date"], index_col="Date")
if not predictions.index.equals(validation.index):
    raise ValueError("Saved prediction dates do not match 2024.")
if not np.allclose(predictions["actual"], validation, equal_nan=True):
    raise ValueError("Saved targets differ from the current dataset; rerun model selection.")

print(f"Checking {chosen['model']} on corrected data...", flush=True)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fitted = SARIMAX(
        training, order=ast.literal_eval(chosen["order"]),
        seasonal_order=ast.literal_eval(chosen["seasonal_order"]),
        trend=chosen["trend"], enforce_stationarity=True,
        enforce_invertibility=True, simple_differencing=False,
    ).fit(disp=False, maxiter=200)

if not fitted.mle_retvals.get("converged", False):
    raise RuntimeError("Selected model did not converge on refit; inspect before proceeding.")
fresh_predictions = fitted.extend(validation).get_prediction().predicted_mean
if not np.allclose(fresh_predictions, predictions[chosen["model"]],
                   rtol=1e-6, atol=1e-7, equal_nan=True):
    raise ValueError("Refitted forecasts differ from saved results; investigate reproducibility.")

# Retain the calendar even where errors cannot be computed.
# Positive error means underprediction: actual pollution exceeded the forecast.
errors = pd.DataFrame(index=validation.index)
errors["actual"] = validation
errors["prediction"] = fresh_predictions
errors["baseline"] = predictions["persistence_baseline"]
errors["error_actual_minus_prediction"] = errors["actual"] - errors["prediction"]
errors["absolute_error"] = errors["error_actual_minus_prediction"].abs()
errors["baseline_absolute_error"] = (errors["actual"] - errors["baseline"]).abs()
scored = errors["actual"].notna() & errors["baseline"].notna()
errors["scored"] = scored
errors.to_csv(destination / "validation_errors.csv", index_label="Date")
common = errors.loc[scored]
mae = float(common["absolute_error"].mean())
if not np.isclose(mae, chosen["validation_mae"], rtol=1e-6):
    raise ValueError("Diagnostic scoring does not reproduce the selection MAE.")

# Do not compress missing dates before computing correlations.
lag_rows = []
for lag in range(1, 31):
    pairs = pd.concat([
        errors["error_actual_minus_prediction"].rename("today"),
        errors["error_actual_minus_prediction"].shift(lag).rename("earlier"),
    ], axis=1).dropna()
    lag_rows.append({"days_earlier": lag,
                     "error_correlation": pairs["today"].corr(pairs["earlier"]),
                     "observed_pairs": len(pairs)})
lags = pd.DataFrame(lag_rows)
lags.to_csv(destination / "validation_error_lag_correlations.csv", index=False)

# Per-month results expose periods where good overall MAE can hide large errors.
monthly = common.groupby(common.index.month).agg(
    scored_days=("absolute_error", "size"),
    model_mae=("absolute_error", "mean"),
    baseline_mae=("baseline_absolute_error", "mean"),
    mean_error=("error_actual_minus_prediction", "mean"),
)
monthly.index.name = "month"
monthly.to_csv(destination / "validation_monthly_errors.csv")
common.nlargest(10, "absolute_error").to_csv(
    destination / "validation_largest_errors.csv", index_label="Date"
)

# Training innovations: ignore startup/diffuse periods and unobserved days.
innovations = pd.Series(
    fitted.filter_results.standardized_forecasts_error[0], index=training.index
)
burn = max(int(fitted.loglikelihood_burn),
           int(getattr(fitted.filter_results, "nobs_diffuse", 0)))
innovations.iloc[:burn] = np.nan
innovations.loc[training.isna()] = np.nan
innovations = innovations.replace([np.inf, -np.inf], np.nan)

fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
axes[0, 0].plot(errors.index, errors["error_actual_minus_prediction"], linewidth=0.8)
axes[0, 0].axhline(0, color="black", linewidth=0.8)
axes[0, 0].set_title("2024 forecast errors (positive = predicted too low)")
axes[0, 0].set_ylabel("Actual minus predicted (ug/m3)")
axes[0, 1].hist(common["error_actual_minus_prediction"], bins=30, edgecolor="white")
axes[0, 1].set_title("2024 errors on common scoring dates")
axes[0, 1].set_xlabel("Actual minus predicted (ug/m3)")
axes[1, 0].bar(lags["days_earlier"], lags["error_correlation"])
axes[1, 0].axhline(0, color="black", linewidth=0.8)
axes[1, 0].set_ylim(-1, 1)
axes[1, 0].set_title("2024 error correlations (calendar gaps preserved)")
axes[1, 0].set_xlabel("Days earlier; exploratory, no significance bands")
qqplot(innovations.dropna().to_numpy(), line="45", ax=axes[1, 1])
axes[1, 1].set_title("Training standardized errors versus normal distribution")
fig.savefig(destination / "selected_model_diagnostics.png", dpi=160)
plt.close(fig)

def minimum_root_magnitude(roots):
    return float(np.min(np.abs(roots))) if len(roots) else None

report = {
    "model": chosen["model"], "dataset": "corrected, no interpolation",
    "converged": bool(fitted.mle_retvals.get("converged", False)),
    "warnings": list(dict.fromkeys(str(w.message) for w in caught)),
    "minimum_ar_root_magnitude": minimum_root_magnitude(fitted.arroots),
    "minimum_ma_root_magnitude": minimum_root_magnitude(fitted.maroots),
    "validation_scored_days": int(scored.sum()), "validation_mae": mae,
    "validation_mean_error": float(common["error_actual_minus_prediction"].mean()),
    "validation_rmse": float(np.sqrt(np.mean(common["error_actual_minus_prediction"] ** 2))),
    "negative_validation_forecasts": int((fresh_predictions < 0).sum()),
    "training_innovations_used": int(innovations.notna().sum()),
    "test_evaluated": False,
    "notes": [
        "Starting-parameter warnings concern initialization; convergence is checked separately.",
        "AR/MA root magnitudes near one can indicate sensitivity; differencing is separate.",
        "Error-lag correlations are exploratory, not formal significance tests.",
        "QQ departures flag non-normal errors; they do not alone invalidate point forecasts.",
        "No automatic pass/fail decision or new tuning is based on these diagnostics.",
    ],
}
(destination / "diagnostic_summary.json").write_text(json.dumps(report, indent=2))
(destination / "training_model_summary.txt").write_text(str(fitted.summary()))
print(json.dumps(report, indent=2))
print("\nMonthly validation errors:")
print(monthly.to_string(float_format=lambda value: f"{value:.4f}"))
print(f"\nSaved diagnostics in {destination}")
print("No model settings changed. No 2025 evaluation performed.")
