# Predicting Next-Day PM2.5 at the Albemarle Monitoring Site

DS 4002 Project 2 | EAZ Inc. | Annie Nguyen, Zilan Saadi, and Eli Boyden

This project forecasts the next day's average PM2.5 concentration at EPA AQS site **51-003-0001** in Albemarle County, Virginia. The goal is a **2025 test mean absolute error (MAE) at least 10% lower** than a persistence baseline that predicts tomorrow's pollution will equal today's.

**Current status:** preprocessing, four-way model comparison, selected-model diagnostics, and final model refitting are complete. The selected approach is **Corrected POC - ARIMA(2,1,3), without interpolation**. The final model was fitted on 2021-2024. **2025 has not been forecast or evaluated; the final 10% goal is not yet established.**

## Repository contents

The repository contains raw EPA data, four processed datasets, preprocessing notebooks, Python modeling scripts, validation results, figures, diagnostics, and a saved model for final evaluation. [Data metadata](data/README.md) explains the measurements and [model selection and handoff](output/model_selection.md) documents the selected approach and Eli's next steps.

## 1. Software and platform

- Platform: Windows, VS Code, PowerShell, and Git.
- Preprocessing: Jupyter notebooks using Python, pandas, NumPy, and Python's built-in pathlib and zipfile modules.
- Modeling: statsmodels SARIMAX implementation for ARIMA and seasonal ARIMA, with pandas, NumPy, and SciPy.
- Figures: matplotlib.
- Recorded refit environment: Python **3.14.7**, NumPy **2.5.3**, pandas **3.0.5**, SciPy **1.18.1**, and statsmodels **0.15.0**.
- Exact refit package pins are in [requirements.txt](output/final_model/requirements.txt). These pins cover refitting/loading the saved model; matplotlib and ipykernel are also needed for plots and notebook execution.

## 2. Documentation map

```text
DS4002-project2/
|-- README.md
|-- LICENSE.md
|-- .gitignore
|-- scripts/
|   |-- preprocessing_without_interpolation.ipynb
|   |-- preprocessing_with_interpolation.ipynb
|   |-- model_training.py
|   |-- validation_models.py
|   |-- model_diagnostics.py
|   `-- refit_selected_model.py
|-- data/
|   |-- README.md
|   |-- raw/
|   |   |-- README.md
|   |   `-- daily_88101_2021.zip ... daily_88101_2025.zip
|   `-- processed/
|       |-- albemarle_pm25_poc3_without_interpolation.csv
|       |-- albemarle_pm25_corrected_poc_without_interpolation.csv
|       |-- albemarle_pm25_poc3_forward_filled.csv
|       `-- albemarle_pm25_corrected_poc_forward_filled.csv
`-- output/
    |-- split_summary.csv
    |-- training_lag_correlations.csv
    |-- validation_*.csv / validation_selection.json
    |-- poc_comparison_*.csv
    |-- gap_filling_comparison_*.csv
    |-- model_selection.md
    |-- original_poc3/                 # Original history, no filling
    |-- original_poc3_forward_filled/  # Original history, forward filled
    |-- corrected_forward_filled/     # Corrected history, forward filled
    |-- figures/                      # Training and validation plots
    |-- diagnostics/                  # Selected-model checks
    `-- final_model/
        |-- corrected_poc_arima_2_1_3_without_interpolation.pkl
        |-- fitted_parameters.csv
        |-- refit_history_2021_2024.csv
        |-- refit_metadata.json
        |-- refit_summary.txt
        `-- requirements.txt
```

The corrected/no-fill validation experiment saves its results directly under `output/`; the other three experiments use the named subfolders. `validation_models.py` is a helper imported by `model_training.py`, not a separate execution step.

## 3. Instructions for reproducing results

Run terminal commands below from the **repository root**. Use the same Python environment for VS Code notebooks and terminal scripts. If your Python command is `python` rather than `python3`, substitute it consistently.

### Install dependencies

```powershell
python3 -m pip install -r output/final_model/requirements.txt
python3 -m pip install matplotlib ipykernel
```

The saved metadata records the environment used for the completed refit. Another Python/platform combination may require compatible package versions and may produce small numerical differences.

### Prepare and verify the datasets

All five raw ZIPs and four processed CSVs are included. To reproduce model results from those included CSVs, proceed to model comparison below. To rerun preprocessing:

1. Open `scripts/preprocessing_without_interpolation.ipynb`, select the Python kernel, restart it, and run all cells. It reads ZIPs from `data/raw/` and regenerates **the corrected no-fill CSV**. It uses the included original POC-3 no-fill CSV as a comparison reference.
2. The original POC-3 no-fill export was independently reconstructed from the raw files using the original selection rules. The current no-fill notebook regenerates only the corrected version. To recreate the original using a temporary copy of that notebook, replace `data = site_data.loc[older_corrected | newer_aligned].copy()` with `data = site_data.loc[site_data["POC"] == 3].copy()` and change only `output_filename` to `albemarle_pm25_poc3_without_interpolation.csv`. Retain the site, hourly-summary, coverage, event-priority, duplicate, and complete-calendar processing. Do not overwrite the corrected export with this temporary run.
3. Open `scripts/preprocessing_with_interpolation.ipynb`, restart its kernel, and run all cells. Despite its filename, it uses **forward filling**, not linear interpolation. It reconstructs both observed histories, verifies them against the no-fill references, and writes the two forward-filled CSVs.
4. Each no-fill CSV has **1,826 calendar dates, 1,759 measured days, and 67 missing values**. Each forward-filled CSV has **61 filled values and six leading blanks**. Original observations and fill indicators are retained in the filled exports. Existing no-fill CSVs are not overwritten by the forward-fill notebook.

### Run training and validation comparisons

```powershell
python3 scripts/model_training.py
```

This script:

1. Separates **2021-2023 training**, **2024 validation**, and **2025 test** periods. Only availability counts are reported for the test period.
2. Saves training-only exploratory plots and calendar-preserving lag correlations.
3. Tests **32 ARIMA candidates** with p/q from 0 to 3 and d from 0 to 1, plus **six exploratory weekly SARIMA candidates**, for each of the four datasets: **152 candidate fits total**.
4. Uses a constant for nonseasonal d=0 and no drift for d=1. Weekly candidates combine nonseasonal orders (1,0,0) or (1,0,1) with seasonal orders (1,0,0,7), (0,0,1,7), or (1,0,1,7).
5. Fits parameters on 2021-2023 and keeps them fixed while generating one-day-ahead 2024 predictions. Previous validation observations update the model state; the current/future target is not used for its own prediction.
6. Scores every approach on the **same 349 dates** with real target and previous-day measurements. Filled values are model inputs only, never scoring targets or baseline answers. Failed/nonconverged fits are logged and excluded; forecasts are not clipped.

Inspect `output/gap_filling_comparison_best_by_family.csv` for the compact comparison or `output/gap_filling_comparison_all_models.csv` for every candidate. Each run overwrites generated comparison outputs. It does not evaluate 2025.

### Check the selected model and reproduce the final refit

```powershell
python3 scripts/model_diagnostics.py
python3 scripts/refit_selected_model.py
```

Diagnostics reproduce the corrected/no-fill model's 2024 predictions and save warnings, monthly errors, largest misses, and plots under `output/diagnostics/`. The refit script checks the frozen selection and fits the same settings using **2021-2024**, leaving missing observations blank. It saves the trained model and supporting files under `output/final_model/`.

The completed refit converged **without warnings**, using **1,461 calendar days, 1,397 measured values, and 64 missing values**. The saved model was loaded successfully and verified to end on December 31, 2024. Neither script evaluates 2025.

## Data preparation decisions

- Keep Albemarle site 51-003-0001, PM2.5 parameter 88101, and `1 HOUR` daily summaries of hourly readings.
- Require at least 18 hourly observations per daily average.
- Prefer event-included over event-excluded alternatives and keep one record per date. Preserve the full calendar.
- **Original POC 3:** POC 3 throughout, including unaligned method 236 in older dates and aligned method 636 afterward.
- **Corrected POC:** POC 23/method 736 before August 1, 2023; POC 3/method 636 from that date onward. EPA identifies 736 as retrospectively corrected historical data and 636 as alignment enabled at collection [1], [2]. The correction choice is based on measurement documentation, not only validation scores.
- **Forward filling:** carry the last observed value forward; leave leading gaps missing. This does not use future readings, but repeats values across long gaps and cannot recover unobserved spikes. The original measurements are retained separately.

These are documented refinements to MI2's POC-3-only selection and proposed gap handling. The revised historical series supports retrospective forecast evaluation; it is not an exact recreation of which revisions were available in real time in 2021-2023.

## Validation results and selected approach

All values below are **2024 validation MAE**, in micrograms per cubic meter. Lower is better. The shared persistence-baseline MAE is **2.274375**.

| Dataset | Gap handling | Best ARIMA MAE | Best weekly SARIMA MAE |
| --- | --- | ---: | ---: |
| Corrected POC | Leave missing | **2.054515** | 2.067389 |
| Original POC 3 | Leave missing | 2.054891 | 2.128212 |
| Corrected POC | Forward fill | 2.058953 | 2.065437 |
| Original POC 3 | Forward fill | 2.060431 | 2.122653 |

**Selected: Corrected POC - ARIMA(2,1,3), without interpolation**, with **9.67% lower validation MAE** than persistence. The original/no-fill ARIMA result was almost tied; the correction did not establish a substantial forecasting improvement. Forward filling did not improve the best overall score. Seasonal conclusions apply only to the weekly candidates tested.

Diagnostics reproduced predictions and found near-zero overall signed validation error, but large misses during sudden changes, non-normal training errors, and an MA component near its invertibility boundary remain limitations. Near-zero signed error does not mean small individual errors. See [selection and diagnostic notes](output/model_selection.md).

## Remaining stage: 2025 evaluation

Eli's evaluation uses the saved final model and the **corrected no-fill CSV**, with settings fixed. Forecast each day before incorporating its measurement; missing observations remain missing. Compare against the observed previous calendar day on identical eligible dates, including December 31, 2024 as the baseline input for January 1, 2025. Report MAE, date count, percentage improvement, and prediction plots. Do not retune settings in response to test results.

Full handoff instructions are in [output/model_selection.md](output/model_selection.md). **The 2025 test has not been evaluated. The validation improvement does not establish the final 10% test target.**

## References

[1] U.S. Environmental Protection Agency, "U.S. EPA Quick Reference Guide to T640/T640X Data," May 13, 2024. [Online]. Available: https://www.epa.gov/system/files/documents/2024-05/quick-reference_t640-data_final_05-13-2024.pdf

[2] U.S. Environmental Protection Agency, "Supplemental Information on the EPA's Update of PM2.5 Data from T640/T640X PM Mass Monitors," May 13, 2024. [Online]. Available: https://www.epa.gov/system/files/documents/2024-05/2_supplemental-info_t640-data-update_final-05-13-2024.pdf

[3] U.S. Environmental Protection Agency, "AirData Download Files." [Online]. Available: https://aqs.epa.gov/aqsweb/airdata/download_files.html

[4] statsmodels developers, "SARIMAXResults.extend." [Online]. Available: https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.extend.html
