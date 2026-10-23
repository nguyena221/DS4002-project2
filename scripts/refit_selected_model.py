"""Refit the frozen corrected-POC/no-fill ARIMA(2,1,3) on 2021-2024.

Run from scripts: python3 refit_selected_model.py
Requires numpy, pandas, scipy, and statsmodels. No search, 2025 prediction,
or test evaluation occurs here. Saved results retain the end-of-2024 state.
"""

import hashlib
import json
from pathlib import Path
import platform
import warnings

import numpy as np
import pandas as pd
import scipy
import statsmodels
from statsmodels.tsa.statespace.sarimax import SARIMAX


root = Path(__file__).resolve().parents[1]
output = root / "output"
selection = json.loads((output / "validation_selection.json").read_text())
chosen = selection["best_candidate"]
if (chosen["order"], chosen["seasonal_order"], chosen["trend"]) != (
    "(2, 1, 3)", "(0, 0, 0, 0)", "n"
):
    raise ValueError("Saved selection changed. Review before refitting the frozen model.")
comparison = pd.read_csv(output / "gap_filling_comparison_all_models.csv")
winner = comparison.sort_values("validation_mae", kind="stable").iloc[0]
if not (winner["dataset"] == "corrected"
        and winner["missing_data"] == "no interpolation"
        and winner["model"] == chosen["model"]):
    raise ValueError("Four-way comparison does not support the recorded selection.")

data_file = root / "data/processed/albemarle_pm25_corrected_poc_without_interpolation.csv"
data = pd.read_csv(data_file, parse_dates=["Date"])
# Select the refit years before creating the series; never pass 2025 into a model.
history = data.loc[data["Date"].between("2021-01-01", "2024-12-31"), ["Date", "PM2.5"]]
if history["Date"].duplicated().any():
    raise ValueError("Duplicate dates in refit input.")
history = history.set_index("Date").sort_index()
expected_dates = pd.date_range("2021-01-01", "2024-12-31", freq="D")
if not history.index.equals(expected_dates):
    raise ValueError("Refit input must preserve the full 2021-2024 daily calendar.")
y = history["PM2.5"].asfreq("D")
if np.isinf(y.dropna().to_numpy()).any():
    raise ValueError("Nonfinite observed pollution value in refit input.")

print("Refitting Corrected POC - ARIMA(2,1,3), without interpolation...", flush=True)
print(f"2021-2024: {len(y)} days, {y.notna().sum()} measured, {y.isna().sum()} missing.")
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fitted = SARIMAX(
        y, order=(2, 1, 3), seasonal_order=(0, 0, 0, 0), trend="n",
        enforce_stationarity=True, enforce_invertibility=True,
        simple_differencing=False,
    ).fit(disp=False, maxiter=200)
if not fitted.mle_retvals.get("converged", False):
    raise RuntimeError("Refit did not converge. No final model was saved.")
if not np.isfinite(np.asarray(fitted.params)).all():
    raise RuntimeError("Refit has nonfinite parameters. No final model was saved.")

destination = output / "final_model"
destination.mkdir(parents=True, exist_ok=True)
model_file = destination / "corrected_poc_arima_2_1_3_without_interpolation.pkl"
# Retain observations and final filtered state for fixed-parameter extensions.
fitted.save(model_file)
history_file = destination / "refit_history_2021_2024.csv"
history.to_csv(history_file, index_label="Date")
pd.DataFrame({"parameter": fitted.param_names, "estimate": fitted.params.to_numpy()}).to_csv(
    destination / "fitted_parameters.csv", index=False
)
(destination / "refit_summary.txt").write_text(str(fitted.summary()), encoding="utf-8")
versions = {"numpy": np.__version__, "pandas": pd.__version__,
            "scipy": scipy.__version__, "statsmodels": statsmodels.__version__}
metadata = {
    "model_label": "Corrected POC - ARIMA(2,1,3), without interpolation",
    "order": [2, 1, 3], "seasonal_order": [0, 0, 0, 0], "trend": "n",
    "enforce_stationarity": True, "enforce_invertibility": True,
    "simple_differencing": False, "fit_maxiter": 200,
    "refit_start": "2021-01-01", "refit_end": "2024-12-31",
    "calendar_days": len(y), "observed_days": int(y.notna().sum()),
    "missing_days": int(y.isna().sum()), "converged": True,
    "warnings": list(dict.fromkeys(str(w.message) for w in caught)),
    "selection_validation_mae": float(chosen["validation_mae"]),
    "selection_validation_improvement_percent": float(chosen["improvement_percent"]),
    "selection_validation_scored_days": int(chosen["scored_days"]),
    "python_version": platform.python_version(), "packages": versions,
    "history_sha256": hashlib.sha256(history_file.read_bytes()).hexdigest(),
    "model_sha256": hashlib.sha256(model_file.read_bytes()).hexdigest(),
    "test_evaluated": False, "forecast_clipping": "none",
}
(destination / "refit_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
# Package versions remain in refit_metadata.json; use the root requirements.txt
# to install the complete environment instead of generating a second file.
print("Refit converged. Warnings:", metadata["warnings"])
print("Saved trained model:", model_file)
print("Saved history, parameters, fit summary, metadata, and package versions:", destination)
print("No 2025 forecasts or scores were generated. Model is ready for evaluation handoff.")
