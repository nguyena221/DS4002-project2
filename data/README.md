# Dataset metadata (in progress)

## Data summary

EPA daily PM2.5 summaries for 2021-2025 will be filtered to Albemarle site 51-003-0001, parameter 88101, POC 23/method 736 before August 1, 2023 and POC 3/method 636 from that date onward, and Sample Duration `1 HOUR`. These rows summarize hourly readings by day. The planned coverage threshold is at least 18 hourly observations per daily average.

We are starting without interpolation. Missing measurements will remain blank, with calendar dates preserved. The original POC-3-only export was verified and preserved as `processed/albemarle_pm25_poc3_without_interpolation.csv`. The revised notebook needs rerunning to replace `processed/albemarle_pm25_corrected_poc_without_interpolation.csv` with the adjusted series. Independent checking of the raw files predicts 1,826 calendar dates, 1,759 usable measurements, 67 missing days, 892 changed older values, and no changed newer values or missing dates.

## Provenance

Zilan prepared the preprocessing notebook. The input is five annual EPA AirData PM2.5 daily-summary archives, listed in `raw/README.md`. Download dates and checksums are pending.

## License

The project plan describes EPA source data as public-domain U.S. government data. Record verified source terms here when obtaining the files. The repository MIT license covers team-authored work and does not relicense third-party materials.

## Ethical statement

These are ambient pollution measurements, not personal records. Predictions are for an academic project, not official public-health guidance. Report missing periods, uncertainty, and measurement-method changes honestly. Do not treat estimated values as actual observations when evaluating predictions.

## Planned processed-data dictionary

Confirm these fields against the freshly exported CSV before finalizing this dictionary.

| Column | Meaning | Units / interpretation |
| --- | --- | --- |
| Date | Local calendar date | YYYY-MM-DD; one row per day |
| PM2.5 | EPA daily Arithmetic Mean | Micrograms per cubic meter; blank when no usable measurement |
| Observation_Count | Hourly readings contributing to the daily summary | Count |
| Observation_Percent | Percentage of expected observations obtained | Percent |
| Event_Type | EPA event-handling category | Text; a blank alone does not mean the pollution value is missing |
| Method_Code | EPA measurement method identifier | Categorical code |
| Method_Name | Description of measurement method | Text |

Initial-data field documentation and final analyzed-data details remain to be completed.

## Explanatory plots

At least two are required by MI3 and have not yet been generated. Proposed plots: observed PM2.5 over time with gaps visible, and the distribution of observed PM2.5. Save finished plots in `output/figures/` and embed them here.

## References

[1] U.S. Environmental Protection Agency, "AirData Download Files." [Online]. Available: https://aqs.epa.gov/aqsweb/airdata/download_files.html. Record download dates when the source files are obtained.

## Measurement-selection revision

The original plan selected POC 3 throughout. EPA documentation identifies method 236 as unaligned, method 736 as retrospectively corrected, and method 636 as alignment enabled during collection. The revised selection uses existing method-736 records under POC 23 before 2023-08-01 and method-636 records under POC 3 afterward. No correction formula or interpolation is calculated by this notebook.

The corrected records have different Event Type metadata: 903 method-736 records are labeled None and one Included before coverage filtering. The revised filter does not reject None records or interpret their changed labels as proof that a pollution event disappeared. The only repeated selected date remains 2024-03-21; the Included record is retained over the Excluded alternative. EPA's supplemental explanation states that original unaligned records were retained and marked NAAQS Excluded; regulatory exclusion should not be confused with proof of a wildfire. Site-specific event-flag equivalence has not been independently established.

The revised dataset uses retrospectively revised historical data. Forecast validation must still avoid future pollution observations, but it is not a reconstruction of exactly which data revisions were available in real time in 2021-2023. Retrospective and collection-time alignment are related methods, not a guarantee of identical processing in all conditions.

[2] U.S. Environmental Protection Agency, "Quick Reference Guide to T640/T640X Data," May 13, 2024. https://www.epa.gov/system/files/documents/2024-05/quick-reference_t640-data_final_05-13-2024.pdf

[3] U.S. Environmental Protection Agency, "Supplemental Information on the EPA's Update of PM2.5 Data from T640/T640X PM Mass Monitors," May 13, 2024. https://www.epa.gov/system/files/documents/2024-05/2_supplemental-info_t640-data-update_final-05-13-2024.pdf

## Forward-fill preprocessing notebook

`scripts/preprocessing_with_interpolation.ipynb` now uses forward filling, not linear interpolation. It reads raw ZIPs in chunks, builds original POC-3 and corrected observed series with the established quality/duplicate rules, and verifies those series against the no-fill exports before filling. It exports `albemarle_pm25_poc3_forward_filled.csv` and `albemarle_pm25_corrected_poc_forward_filled.csv`. Each retains `PM2.5_Original`, adds `Was_Filled` and `Fill_Source_Date`, and supplies forward-filled model inputs in `PM2.5`. Measurement metadata is not fabricated for filled days. Source dates must precede filled dates. Leading gaps stay missing; the expected result for each dataset is 61 filled values and six leading blanks. Those are expectations pending a notebook run, not generated results.

The forward-fill experiment repeats the last observation even across long gaps; it cannot recover unseen pollution spikes. It is an optional comparison, separate from the current no-fill model-training workflow. The training script has not yet been connected to these new exports. When added, validation targets and baseline values must come from `PM2.5_Original`, with the same eligible observed dates, and 2025 must remain reserved for final evaluation.
