"""Fit fixed candidate models and compare one-day-ahead validation forecasts.

Called by model_training.py. Training uses 2021-2023; selection uses 2024.
No test data is accepted by this function. Requires numpy, pandas, statsmodels.
"""

from itertools import product
import json
import platform
import time
import warnings

import numpy as np
import pandas as pd
import statsmodels
from statsmodels.tsa.statespace.sarimax import SARIMAX


def compare_models(train, validation, output_dir, model_inputs=None):
    """Save convergence logs, predictions, and validation rankings.

    Parameters are fitted once per candidate. Extending the fitted filter through
    validation produces one-step predictions using previous observations only:
    it does not refit parameters or smooth using future validation observations.
    Default inputs preserve missing observations. Optional model_inputs must
    match causal forward filling of the original series. Scoring targets and
    baseline always use the original unfilled train/validation arguments.
    """
    if train.index.max() >= validation.index.min():
        raise ValueError("Training must end before validation begins.")
    if not train.index.equals(pd.date_range(train.index.min(), train.index.max())):
        raise ValueError("Training must preserve every calendar day.")
    expected_validation = pd.date_range(
        train.index.max() + pd.Timedelta(days=1), validation.index.max()
    )
    if not validation.index.equals(expected_validation):
        raise ValueError("Validation must immediately follow training, with daily dates.")

    actual = validation.astype(float)
    # Shift the full calendar before slicing, including Dec 31 as Jan 1's baseline.
    baseline = pd.concat([train, actual]).shift(1).loc[actual.index]
    eligible = actual.notna() & baseline.notna()
    if not eligible.any():
        raise ValueError("No dates with both observed target and baseline.")
    baseline_mae = float((actual[eligible] - baseline[eligible]).abs().mean())
    predictions = pd.DataFrame({
        "actual": actual, "persistence_baseline": baseline, "scored": eligible
    })

    if model_inputs is None:
        fit_values, updates = train, actual
        strategy = "leave_missing"
    else:
        observed = pd.concat([train, actual])
        if not model_inputs.index.equals(observed.index):
            raise ValueError("Filled inputs must cover training and validation only.")
        if not np.allclose(model_inputs, observed.ffill(), equal_nan=True):
            raise ValueError("Filled CSV does not match causal forward filling.")
        fit_values = model_inputs.loc[train.index]
        updates = model_inputs.loc[actual.index]
        strategy = "forward_fill"
    print(f"Model inputs: {strategy}; targets and baseline remain observed.", flush=True)

    # MI2 nonseasonal search: p and q 0-3, d 0-1 (32 candidates).
    # Use a constant for d=0; no drift for d=1. Keep this rule fixed for selection.
    candidates = [((p, d, q), (0, 0, 0, 0))
                  for p, d, q in product(range(4), range(2), range(4))]
    # Small exploratory weekly comparison, not a claim that seasonality exists.
    candidates += [(order, seasonal)
                   for order in [(1, 0, 0), (1, 0, 1)]
                   for seasonal in [(1, 0, 0, 7), (0, 0, 1, 7), (1, 0, 1, 7)]]

    rankings = [{
        "model": "persistence_baseline", "order": "", "seasonal_order": "",
        "trend": "", "validation_mae": baseline_mae,
        "improvement_percent": 0.0, "scored_days": int(eligible.sum()),
    }]
    fit_log = []
    print(f"\nBaseline MAE: {baseline_mae:.4f}; scored dates: {eligible.sum()}", flush=True)
    print(f"Comparing {len(candidates)} candidates; progress prints after each fit.", flush=True)

    for number, (order, seasonal_order) in enumerate(candidates, 1):
        family = "SARIMA" if seasonal_order[-1] else "ARIMA"
        label = f"{family}{order}" + (f"x{seasonal_order}" if seasonal_order[-1] else "")
        trend = "c" if order[1] == 0 else "n"
        record = {"model": label, "order": str(order),
                  "seasonal_order": str(seasonal_order), "trend": trend}
        start = time.monotonic()
        captured = []
        print(f"[{number}/{len(candidates)}] Fitting {label}...", flush=True)
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                model = SARIMAX(
                    fit_values, order=order, seasonal_order=seasonal_order, trend=trend,
                    enforce_stationarity=True, enforce_invertibility=True,
                    simple_differencing=False,
                )
                fitted = model.fit(disp=False, maxiter=200)
                if not fitted.mle_retvals.get("converged", False):
                    record["status"] = "excluded_nonconverged"
                elif not np.isfinite(np.asarray(fitted.params)).all():
                    record["status"] = "excluded_nonfinite_parameters"
                else:
                    # Default predicted information set is one-step-ahead filtering,
                    # not fitted/smoothed estimates using the current/future target.
                    extended = fitted.extend(updates)
                    forecast = extended.get_prediction().predicted_mean
                    if not forecast.index.equals(actual.index):
                        raise ValueError("Forecast dates do not match validation dates.")
                    if not np.isfinite(forecast.to_numpy()).all():
                        raise ValueError("Nonfinite validation forecasts.")

                    # Verify the first extension prediction is truly out of sample.
                    first_forecast = float(fitted.forecast(1).iloc[0])
                    if not np.isclose(forecast.iloc[0], first_forecast):
                        raise ValueError("First one-step forecast failed timing check.")
                    mae = float((actual[eligible] - forecast[eligible]).abs().mean())
                    improvement = (100 * (baseline_mae - mae) / baseline_mae
                                   if baseline_mae > 0 else np.nan)
                    rankings.append({**{k: record[k] for k in
                                           ("model", "order", "seasonal_order", "trend")},
                                     "validation_mae": mae,
                                     "improvement_percent": improvement,
                                     "scored_days": int(eligible.sum())})
                    predictions[label] = forecast
                    record["status"] = "ok"
                    record["validation_mae"] = mae
            record["warnings"] = " | ".join(dict.fromkeys(str(w.message) for w in captured))
        except Exception as error:
            record["status"] = "excluded_error"
            record["error"] = f"{type(error).__name__}: {error}"
            record["warnings"] = " | ".join(dict.fromkeys(str(w.message) for w in captured))
        record["elapsed_seconds"] = round(time.monotonic() - start, 2)
        fit_log.append(record)
        # Save incremental progress so interrupted runs still have a diagnostic log.
        pd.DataFrame(fit_log).to_csv(output_dir / "validation_fit_log.csv", index=False)
        print(f"  {record['status']} ({record['elapsed_seconds']:.1f}s)"
              + (f" MAE={record['validation_mae']:.4f}" if "validation_mae" in record else ""),
              flush=True)

    ranking = pd.DataFrame(rankings).sort_values("validation_mae", kind="stable")
    ranking.to_csv(output_dir / "validation_model_comparison.csv", index=False)
    predictions.to_csv(output_dir / "validation_predictions.csv", index_label="Date")
    successful = ranking.loc[ranking["model"] != "persistence_baseline"]
    selection = {
        "missing_strategy": strategy,
        "training_period": "2021-2023", "validation_period": "2024",
        "scored_days": int(eligible.sum()), "baseline_mae": baseline_mae,
        "best_overall": ranking.iloc[0]["model"],
        "best_candidate": successful.iloc[0].to_dict() if not successful.empty else None,
        "test_evaluated": False, "parameters_refitted_during_validation": False,
        "forecast_clipping": "none", "python_version": platform.python_version(),
        "statsmodels_version": statsmodels.__version__,
        "pandas_version": pd.__version__, "numpy_version": np.__version__,
    }
    with open(output_dir / "validation_selection.json", "w", encoding="utf-8") as file:
        json.dump(selection, file, indent=2)

    print("\nValidation ranking (lower MAE is better):")
    print(ranking.head(10).to_string(index=False))
    if successful.empty:
        raise RuntimeError("No candidates passed. Inspect output/validation_fit_log.csv.")
    print(f"\nBest candidate: {successful.iloc[0]['model']}")
    print(f"Best overall, including baseline: {ranking.iloc[0]['model']}")
    print("2025 has not been forecast, scored, or used to choose settings.")
    return ranking, predictions


