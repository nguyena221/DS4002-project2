# Predicting Next-Day PM2.5 at the Albemarle Monitoring Site

DS 4002 Project 2 asks whether past daily PM2.5 measurements at EPA AQS site 51-003-0001 can predict the next day's average concentration. Our target is a 2025 test mean absolute error (MAE) at least 10% below the persistence baseline: tomorrow equals today. Results have not yet been established.

## Repository contents

This repository is being prepared for MI3. We are starting with preprocessing without interpolation: missing measurements will remain blank. The supplied non-interpolated notebook and five raw EPA ZIP files have been added. The notebook still needs a clean verification run before its CSV is accepted. No models have been trained here yet.

## 1. Software and platform

- Preprocessing: Python in VS Code/Jupyter on Windows, using pandas and NumPy, plus built-in zipfile and os modules.
- Repository setup: Windows, PowerShell, and Git.
- Planned modeling: statsmodels; plotting: matplotlib.
- Exact Python and package versions will be recorded after the workflow is run and verified.

## 2. Documentation map

```text
DS4002-project2/
|-- README.md
|-- LICENSE.md
|-- .gitignore
|-- scripts/
|   `-- preprocessing_without_interpolation.ipynb
|-- data/
|   |-- README.md
|   |-- raw/
|   |   `-- README.md
|   `-- processed/
|       `-- .gitkeep
`-- output/
    `-- figures/
        `-- .gitkeep
```

The .gitkeep files preserve empty folders in Git and will be unnecessary once project files are added.

## 3. Instructions for reproducing results

The workflow is pending verification; there are no completed model results to reproduce yet.

1. Use the five annual EPA ZIP files included in `data/raw/`.
2. Open `scripts/preprocessing_without_interpolation.ipynb` in VS Code. Select a Python kernel with pandas, NumPy, and ipykernel installed. Restart the kernel and run every cell from top to bottom. The notebook finds ZIP files in `data/raw/` automatically.
3. Confirm site 51-003-0001, parameter 88101, POC 23/method 736 before August 1, 2023 and POC 3/method 636 afterward, Sample Duration `1 HOUR`, at least 18 hourly observations, and the rule used to resolve repeated dates. Inspect any conflicting records before accepting the daily series.
4. Keep one row for every calendar date and leave missing pollution measurements blank. Verify output counts and review the documented measurement-selection revision in `data/README.md`.
5. The notebook saves `data/processed/albemarle_pm25_corrected_poc_without_interpolation.csv` directly. Verify that export and record tested software versions here.
6. Implement ARIMA and suitable SARIMA candidates using 2021-2023 for training and rolling one-day-ahead predictions during 2024 for selection. Use only information available before each forecast and an implementation that supports missing observations.
7. Refit the selected configuration on 2021-2024 and evaluate on 2025 without further tuning. Compare the model and baseline on identical dates with actual measurements for both today and tomorrow.
8. Save predictions, error summaries, and plots under `output/`. Include at least two explanatory data plots in `data/README.md`. Replace these provisional instructions with exact execution steps once implementation is complete.

## References

The project proposal (MI1), analysis plan (MI2), and instructor's MI3 rubric guide this work. Complete IEEE-style references will be added as source and analysis documentation is verified.






## Running model selection

From the repository root, run:

```powershell
python3 -m pip install numpy pandas matplotlib statsmodels
python3 scripts/model_training.py
```

Use the same interpreter that successfully loaded the data. Dependency versions are recorded in `output/validation_selection.json` after model comparison; a pinned environment is still pending a verified run.

The script searches 32 ARIMA configurations (p/q 0-3, d 0-1) and six exploratory weekly SARIMA configurations. For d=0 it uses a constant; for d=1 it uses no drift. Weekly candidates use nonseasonal orders (1,0,0) or (1,0,1) and seasonal orders (1,0,0,7), (0,0,1,7), or (1,0,1,7). These are fixed in advance, not evidence of an established weekly cycle.

Parameters are fitted using 2021-2023 only. Fixed-parameter one-step filtering through 2024 incorporates previous validation observations without using the current or future target. Missing dates are preserved. All candidates and the persistence baseline are scored on the same dates with observed pollution today and the previous calendar day. Failed/nonconverged candidates are excluded and logged. Predictions are not clipped. The script does not evaluate or forecast 2025, refit the winner on 2021-2024, or claim the test improvement target has been achieved.

Additional outputs: `validation_fit_log.csv`, `validation_model_comparison.csv`, `validation_predictions.csv`, `validation_selection.json`, and `figures/validation_predictions.png`. If the baseline wins, that is reported explicitly. Each run replaces these generated outputs.

Forecasting API reference: https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.extend.html

### Original versus corrected history (without interpolation)

`model_training.py` now runs the same 38 candidates twice: corrected history first (outputs in `output/`), then original POC-3 history (outputs in `output/original_poc3/`). It verifies common calendar/missing dates and identical 2024 target measurements before comparison. Combined results are saved as `output/poc_comparison_all_models.csv`; the best ARIMA, SARIMA, and baseline per dataset are in `output/poc_comparison_best_by_family.csv`. The original and corrected histories are not averaged or combined during training. Both use 2021-2023 training and 2024 validation; 2025 is not evaluated. The exploratory plots earlier in the script describe the corrected training series only.

Follow-up requested: revisit missing-value filling experiments later. They are not implemented in the current comparison. Any future filling experiment must respect forecast timing and score against real, common validation measurements.

### Selected-model diagnostics

After model comparison, run `python3 scripts/model_diagnostics.py` from the repository root (or `python3 model_diagnostics.py` from scripts). It refits the selected corrected-data model on 2021-2023, checks that its 2024 forecasts reproduce the saved predictions, and saves diagnostics in `output/diagnostics/`. Outputs include training model summary, warnings and root magnitudes, calendar-preserving validation error correlations, a four-panel diagnostic figure, monthly MAE, and the ten largest errors. Positive signed error means underprediction. This step neither changes model settings nor evaluates 2025. Review outputs before deciding on any further work or refitting on 2021-2024. Interpolation remains a deferred experiment.

### Preparing forward-filled inputs (optional experiment)

Open `scripts/preprocessing_with_interpolation.ipynb` in VS Code, restart its Python kernel, and run all cells. Despite its filename, the documented method is forward filling. Both original POC-3 and corrected inputs are exported separately under `data/processed/`, with original measurements and fill flags retained. Existing no-fill datasets are not overwritten. See `data/README.md` for filenames, column meanings, limitations, and expected fill counts. This notebook has been adapted but still needs its first verification run. Current `model_training.py` continues to compare only the no-fill datasets until the forward-fill comparison is explicitly added.

### Four-way model comparison using notebook exports

The current training script now reads both forward-filled CSVs from `data/processed/` in addition to the two no-fill CSVs. This supersedes earlier statements that it compares only no-fill data. It verifies the retained original measurements and checks that the filled inputs equal forward filling of the original daily calendar through 2024. All four experiments search the same 38 candidates, using original observed 2024 targets and the original observed persistence baseline on common dates. Filled inputs update the model only after the prediction for their date. Model parameters are fitted on 2021-2023 and remain fixed during validation. No 2025 predictions or scoring are performed.

Run `python3 scripts/model_training.py` from the repository root, or `python3 model_training.py` from scripts. It performs 152 candidate fits and prints ALL FOUR EXPERIMENTS. Additional experiment outputs are in `output/original_poc3_forward_filled/` and `output/corrected_forward_filled/`. Combined rankings are `output/gap_filling_comparison_all_models.csv` and `output/gap_filling_comparison_best_by_family.csv`. The existing diagnostics script still checks the corrected/no-fill winner; review the combined results before deciding which approach to diagnose and refit. This expanded script still needs its first verification run.

### Frozen selection and completed refit

The selected approach is Corrected POC - ARIMA(2,1,3), without interpolation. See `output/model_selection.md` for the four-way validation results, limitations, and Eli's evaluation instructions. Run `python3 scripts/refit_selected_model.py` to reproduce the final training fit. It fixes the selected settings and uses 2021-2024 only. The refit completed successfully with 1,461 calendar days, 1,397 measured days, 64 missing observations, and no fit warnings. Saved artifacts are in `output/final_model/`, including the loadable model, parameter estimates, fit summary, history snapshot, metadata/checksums, and exact package versions. The 2025 test evaluation remains unperformed. No model-selection decisions should be changed in response to the eventual 2025 score.
