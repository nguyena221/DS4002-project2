# Original EPA files

All five original ZIPs are included. Do not extract or edit them; preprocessing reads each CSV inside its ZIP. If missing, use the matching direct source:

- [daily_88101_2021.zip](https://aqs.epa.gov/aqsweb/airdata/daily_88101_2021.zip)
- [daily_88101_2022.zip](https://aqs.epa.gov/aqsweb/airdata/daily_88101_2022.zip)
- [daily_88101_2023.zip](https://aqs.epa.gov/aqsweb/airdata/daily_88101_2023.zip)
- [daily_88101_2024.zip](https://aqs.epa.gov/aqsweb/airdata/daily_88101_2024.zip)
- [daily_88101_2025.zip](https://aqs.epa.gov/aqsweb/airdata/daily_88101_2025.zip)

Original download dates were not recorded. Do not substitute filesystem dates. Run `python scripts/preprocess_data.py` from the repository root to rebuild the derived files and `data/processed/preprocessing_audit.json`, which records SHA-256 checksums, source URLs, and row counts. Future EPA downloads may differ from archived inputs; investigate checksum differences before comparing results.

See [dataset metadata](../README.md) for definitions, source terms, and selection.
