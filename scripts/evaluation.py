"""Run the canonical 2025 final evaluation for the frozen selected model.

run with: python scripts/evaluation.py
author: eli boyden
"""

import json
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAXResults

# constants
ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "output/final_model/corrected_poc_arima_2_1_3_without_interpolation.pkl"
DATA_PATH = ROOT / "data/processed/albemarle_pm25_corrected_poc_without_interpolation.csv"
OUTPUT_DIR = ROOT / "output/final_evaluation"

PREDICTIONS_PATH = OUTPUT_DIR / "evaluation_predictions.csv"
METRICS_PATH = OUTPUT_DIR / "evaluation_metrics.json"
PLOT_PATH = OUTPUT_DIR / "evaluation_plot.png"
SUMMARY_PATH = OUTPUT_DIR / "evaluation_summary.md"

TARGET_IMPROVEMENT_PERCENT = 10.0

"""
check that:
the data exists
the data contains Date and PM2.5
the data has no duplicate dates
the data covers the expected date range
the data contains only finite PM2.5 value

return observed series for 2025 including one day from 2024 for baseline comparison
"""
def load_observed_series():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"dataset missing at {DATA_PATH}")

    frame = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    required_columns = {"Date", "PM2.5"}
    missing = required_columns - set(frame.columns)
    if missing:
        raise ValueError(f"dataset missing one of {sorted(missing)}")
    if frame["Date"].duplicated().any():
        raise ValueError("dataset contains duplicate dates")

    series = (
        frame.set_index("Date")["PM2.5"]
        .sort_index()
        .astype(float)
        .asfreq("D")
    )

    expected = pd.date_range("2024-12-31", "2025-12-31", freq="D") # include one extra date from 2024 so that the first day of 2025 has a baseline prediction
    window = series.loc["2024-12-31":"2025-12-31"]
    if not window.index.equals(expected):
        raise ValueError("dataset must include every daily date from 2024-12-31 through 2025-12-31")
    if np.isinf(window.dropna().to_numpy()).any():
        raise ValueError("dataset contains non-finite PM2.5 values")

    return window

"""
given a model and the observed series for 2025, forecast each day in 2025 using the model
returns a series of model predictions for 2025, raise an error if any prediction is non-finite
"""
def forecast_2025(model, observed_2025):
    running = model
    predictions = []

    for date, observation in observed_2025.items():
        next_day = running.get_forecast(1).predicted_mean
        value = float(next_day.iloc[0])
        if not np.isfinite(value):
            raise ValueError(f"non-finite prediction at {date.date()}.")
        predictions.append(value)

        update = pd.Series([observation], index=[date], dtype=float)
        running = running.extend(update)

    return pd.Series(predictions, index=observed_2025.index, name="model_prediction")

"""
write a plot comparing observed, model, and persistence predictions for 2025
"""
def write_plot(dates, observed, model_prediction, persistence_prediction, eligible):
    fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)

    ax.plot(dates, observed, label="Observed PM2.5", linewidth=1.4)
    ax.plot(dates, model_prediction, label="Model prediction", linewidth=1.2)
    ax.plot(dates, persistence_prediction, label="Persistence baseline", linewidth=1.2)

    scored_dates = dates[eligible.to_numpy()]
    if len(scored_dates):
        ax.scatter(
            scored_dates,
            observed.loc[scored_dates],
            label="Eligible scoring date",
            s=14,
            alpha=0.8,
            zorder=3,
        )

    ax.set_title("2025 final evaluation: observed vs model vs persistence baseline")
    ax.set_xlabel("Date")
    ax.set_ylabel("PM2.5 (ug/m3)")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.savefig(PLOT_PATH, dpi=160)
    plt.close(fig)


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"pickle missing at {MODEL_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Verify this is the frozen team-authored artifact before loading the pickle.
    metadata = json.loads((MODEL_PATH.parent / "refit_metadata.json").read_text(encoding="utf-8"))
    if hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest() != metadata["model_sha256"]:
        raise ValueError("Saved model checksum differs from refit metadata")
    if metadata["refit_end"] != "2024-12-31":
        raise ValueError("Final model must end before the test year")
    model = SARIMAXResults.load(MODEL_PATH)
    if pd.Timestamp(model.model.data.dates[-1]) != pd.Timestamp("2024-12-31"):
        raise ValueError("Loaded model state does not end on December 31, 2024")
    observed_window = load_observed_series()
    observed_2025 = observed_window.loc["2025-01-01":"2025-12-31"]

    persistence_prediction = observed_window.shift(1).loc[observed_2025.index] # shift by one day to get persistence baseline
    model_prediction = forecast_2025(model, observed_2025)

    eligible = observed_2025.notna() & persistence_prediction.notna()
    if not eligible.any():
        raise ValueError("no eligible scoring date values were found")

    abs_error_model = (observed_2025 - model_prediction).abs()
    abs_error_persistence = (observed_2025 - persistence_prediction).abs()

    model_mae = float(abs_error_model.loc[eligible].mean())
    baseline_mae = float(abs_error_persistence.loc[eligible].mean())
    if baseline_mae <= 0:
        raise ValueError("baseline MAE was not positive")
    percent_improvement = float(100.0 * (baseline_mae - model_mae) / baseline_mae)
    target_met = bool(percent_improvement >= TARGET_IMPROVEMENT_PERCENT)

    predictions = pd.DataFrame(
        {
            "date": observed_2025.index.strftime("%Y-%m-%d"),
            "observed_pm25": observed_2025.to_numpy(),
            "model_prediction": model_prediction.to_numpy(),
            "persistence_prediction": persistence_prediction.to_numpy(),
            "is_eligible_for_scoring": eligible.to_numpy(),
            "abs_error_model": abs_error_model.where(eligible).to_numpy(),
            "abs_error_persistence": abs_error_persistence.where(eligible).to_numpy(),
        }
    )
    predictions.to_csv(PREDICTIONS_PATH, index=False)

    metrics = {
        "scored_date_count": int(eligible.sum()),
        "model_mae": model_mae,
        "baseline_mae": baseline_mae,
        "percent_improvement": percent_improvement,
        "target_improvement_percent": TARGET_IMPROVEMENT_PERCENT,
        "target_met": target_met,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    write_plot(
        observed_2025.index,
        observed_2025,
        model_prediction,
        persistence_prediction,
        eligible,
    )

    # Recreate the human-readable result too, rather than leaving a stale report.
    SUMMARY_PATH.write_text(
        "# Final evaluation (2025)\n\n"
        "Frozen model: corrected-history ARIMA(2,1,3), no filling. "
        "Fitted on 2021-2024; each test date is forecast before its observation "
        "updates the state. Parameters and selection settings stay fixed.\n\n"
        f"- Calendar test dates: {len(observed_2025)}\n"
        f"- Observed test dates: {int(observed_2025.notna().sum())}\n"
        f"- Shared scoring dates: {int(eligible.sum())}\n"
        f"- Model MAE: {model_mae:.6f} ug/m3\n"
        f"- Persistence MAE: {baseline_mae:.6f} ug/m3\n"
        f"- Improvement: {percent_improvement:.6f}%\n"
        f"- At least 10% improvement achieved: {target_met}\n\n"
        "The baseline uses the previous calendar day's observed value, including "
        "December 31, 2024 for January 1. Only dates with an observed target and "
        "observed previous day are scored; no filled targets are used. "
        "This is retrospective evaluation using EPA-revised historical data, "
        "not a live forecasting service.\n\n"
        "![2025 predictions](evaluation_plot.png)\n",
        encoding="utf-8",
    )

    print(f"scored date count: {metrics['scored_date_count']}")
    print(f"model MAE: {model_mae:.6f}")
    print(f"baseline MAE: {baseline_mae:.6f}")
    print(f"percent improvement: {percent_improvement:.6f}%")
    print(f"target met: {target_met}")
    print(f"output dir: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
