# Final evaluation (2025)

Frozen model: corrected-history ARIMA(2,1,3), no filling. Fitted on 2021-2024; each test date is forecast before its observation updates the state. Parameters and selection settings stay fixed.

- Calendar test dates: 365
- Observed test dates: 362
- Shared scoring dates: 361
- Model MAE: 2.024619 ug/m3
- Persistence MAE: 2.295626 ug/m3
- Improvement: 11.805358%
- At least 10% improvement achieved: True

The baseline uses the previous calendar day's observed value, including December 31, 2024 for January 1. Only dates with an observed target and observed previous day are scored; no filled targets are used. This is retrospective evaluation using EPA-revised historical data, not a live forecasting service.

![2025 predictions](evaluation_plot.png)
