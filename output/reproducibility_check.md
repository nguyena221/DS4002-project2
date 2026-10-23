# Reproduction check - October 23, 2026

An isolated Windows environment was created with CPython 3.14.7 and the six
direct dependency pins in the root requirements.txt. All 45 resolved packages
were captured in requirements-lock.txt. The package compatibility check passed.
During the initial cleanup, preprocessing was independently reconstructed with a temporary command-line implementation, then the modeling stages below were executed. That extra preprocessing script was subsequently removed at the team leader's request; the original detailed notebooks and their original CSV exports are restored. The modeling/evaluation rerun and exact result checks below remain valid. The restored notebooks were not re-executed during this restoration. The original verification sequence was:

1. Independent preprocessing reconstruction (removed; use original notebooks for reproduction)
2. scripts/model_training.py
3. scripts/model_diagnostics.py
4. scripts/refit_selected_model.py
5. scripts/evaluation.py

Preprocessing rebuilt all four datasets from the five archived ZIPs. Observed
pollution values and calendars matched the previously committed series. The original notebook-generated exports are retained, including their original handling of Event Type None as a null; PM2.5 values and dates are unchanged. The 67 missing PM2.5 values split as 17/28/6/13/3 across 2021-2025.
Both forward-filled alternatives supplied 61 values and retained six leading
blanks. The five original ZIP files remain included unchanged.

All 152 candidate fits were rerun. The selected model remained corrected-history
ARIMA(2,1,3), with no filling, validation MAE 2.0545148122046104 on 349 shared
dates. The 2021-2024 refit converged without warnings. No settings were changed
using the 2025 results.

Final test results exactly reproduced the previously committed evaluation:

| Metric | Reproduced value |
| --- | ---: |
| Shared scoring dates | 361 |
| Model MAE (ug/m3) | 2.024618808009112 |
| Baseline MAE (ug/m3) | 2.2956256315789476 |
| Improvement (%) | 11.805357974829517 |
| At least 10% improvement | Met |

An independent CSV-based calculation confirmed the MAEs, eligibility mask,
previous-calendar-day baseline (including December 31, 2024), raw-file hashes,
and row totals. Python/notebook code parsed and relative documentation links
resolved. Training/evaluation figures were visually inspected. An initialization
warning in training diagnostics remains documented; the final refit had none.

This verifies reproduction on the recorded Windows environment, not every
operating system or Python version. Original source download dates remain
unrecorded, and no dataset-specific source license was inferred or fabricated.
