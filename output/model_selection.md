# Selected model and evaluation handoff

Selected approach: **Corrected POC - ARIMA(2,1,3), without interpolation**.

The corrected series uses POC 23/method 736 before August 1, 2023 and POC 3/method 636 afterward. Missing observations remain blank on a daily calendar. This is retrospective analysis with EPA-revised measurements, not an exact recreation of data availability in 2021-2023.

## Selection evidence (2024 validation only)

All experiments used 2021-2023 parameter fitting and fixed-parameter, one-day-ahead validation on the same 349 dates with observed targets and observed previous-day baseline readings. The common persistence-baseline MAE was 2.274375 ug/m3.

| Data | Missing-data approach | Best ARIMA MAE | Best weekly SARIMA MAE |
| --- | --- | ---: | ---: |
| Corrected POC | Leave missing | 2.054515 | 2.067389 |
| Original POC 3 | Leave missing | 2.054891 | 2.128212 |
| Corrected POC | Forward fill | 2.058953 | 2.065437 |
| Original POC 3 | Forward fill | 2.060431 | 2.122653 |

The selected model had the lowest validation MAE and 9.666857% less error than persistence. Differences among the best ARIMA approaches were small; this is not evidence of a substantial or statistically established improvement from the data correction. Corrected measurements also have a measurement-quality rationale independent of forecast scores. Weekly SARIMA conclusions apply only to the six seasonal candidates tested.

Initial selected-model diagnostics reproduced validation predictions. Convergence succeeded; a starting-MA-parameter warning occurred. Overall validation signed error was near zero, but extreme misses and non-normal training errors remain limitations. The MA root magnitude near one merits sensitivity awareness. No automatic diagnostic pass/fail rule was applied. See `diagnostics/` for full evidence.

## Refit (Annie's training stage)

Run `python3 refit_selected_model.py` from `scripts/` (or `python3 scripts/refit_selected_model.py` from the repository root). It keeps settings fixed and refits on 2021-2024. Successful execution saves the model, fit metadata, parameters, package versions, and a 2021-2024 history snapshot in `output/final_model/`. Check its convergence and warnings before handoff. The committed refit artifacts are present; the script recreates them.

## Final evaluation protocol (implemented in scripts/evaluation.py)

1. Use the saved model and matching environment recorded in `final_model/refit_metadata.json`. Only load the project's own trusted model pickle. Load with `statsmodels.tsa.statespace.sarimax.SARIMAXResults.load(model_path)`; the saved state ends on December 31, 2024.
2. Use observed 2025 values from `data/processed/albemarle_pm25_corrected_poc_without_interpolation.csv`. Preserve all calendar dates and missing observations. Do not switch to a filled dataset.
3. Forecast the next date **before** incorporating that date's observation. Then extend the model state with the actual observation (or NaN), keeping fitted parameters fixed. Do not refit or retune during the test year.
4. Calculate persistence using the previous calendar day's actual measurement, including December 31, 2024 for January 1, 2025. Score both approaches only where actual measurements exist for the target day and previous day; do not bridge missing dates or score against estimated answers.
5. Report scored date count, each MAE, and `100 * (baseline_MAE - model_MAE) / baseline_MAE`. Save daily predictions and plots in output. The goal is at least 10% lower **2025 test** MAE; the 9.67% validation result does not establish that goal.
6. Keep this selection fixed after observing 2025 results. Report whether the target is met without further test-driven tuning.

No 2025 prediction or evaluation is performed by the refit script. This document does not send a message to Eli or submit the project.

## Completed refit status

The refit has now completed successfully: 1,461 calendar days spanning January 1, 2021 through December 31, 2024; 1,397 measured and 64 missing values. Optimization converged without warnings. Artifacts listed above are present in `output/final_model/`. The refit itself produces no 2025 forecasts; the subsequent evaluation script produces the test results below. The model pickle was subsequently loaded successfully and its sample end date and checksum verified.


## Completed final evaluation

`python scripts/evaluation.py` implements the protocol above. On 361 eligible 2025 dates, model MAE is 2.024618808009112 ug/m3 and persistence MAE is 2.2956256315789476 ug/m3. Improvement is **11.805357974829517%**, meeting the 10% target. There are 362 observed test days; March 11-13 lack measurements and March 14 lacks an observed previous-day baseline. The selected model/settings remain fixed. See [metrics](final_evaluation/evaluation_metrics.json), [predictions](final_evaluation/evaluation_predictions.csv), and [plot](final_evaluation/evaluation_plot.png).

Preprocessing now has a shared command-line entry point, `scripts/preprocess_data.py`, that regenerates all four CSVs directly without notebook edits. Literal Event Type None is preserved; pollution values, selected dates, and model-selection rules are unchanged. Source checksums and missingness are recorded in `data/processed/preprocessing_audit.json`.
