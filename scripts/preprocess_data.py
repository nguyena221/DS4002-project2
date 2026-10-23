"""Rebuild all four daily datasets from the five original EPA ZIP files.

Run first: python scripts/preprocess_data.py (from any working directory).
Requires pandas and numpy. Preserves EPA's literal Event Type 'None'; missing
calendar days remain blank. No model fitting, parameter selection, or scoring.
The original detailed notebooks are preserved separately; this command-line
entry point regenerates all four exports without manual notebook edits.
"""

import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = pd.Timestamp("2023-08-01")
CALENDAR = pd.date_range("2021-01-01", "2025-12-31", freq="D")
RENAME = {
    "Date Local": "Date", "Arithmetic Mean": "PM2.5",
    "Observation Count": "Observation_Count",
    "Observation Percent": "Observation_Percent", "Event Type": "Event_Type",
    "Method Code": "Method_Code", "Method Name": "Method_Name",
}


def read_site():
    """Stream nationwide records and retain only the selected site's summaries."""
    parts, sources = [], []
    for year in range(2021, 2026):
        path = ROOT / "data/raw" / f"daily_88101_{year}.zip"
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path}; see data/raw/README.md")
        total, site_count = 0, 0
        with zipfile.ZipFile(path) as archive:
            members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"Expected one CSV in {path.name}")
            # Empty fields stay empty and the genuine category 'None' stays text.
            for chunk in pd.read_csv(archive.open(members[0]), chunksize=100000,
                                     keep_default_na=False, low_memory=False):
                total += len(chunk)
                site = ((chunk["State Code"] == 51) & (chunk["County Code"] == 3)
                        & (chunk["Site Num"] == 1)
                        & (chunk["Parameter Code"] == 88101))
                site_count += int(site.sum())
                parts.append(chunk.loc[site & (chunk["Sample Duration"] == "1 HOUR")].copy())
        sources.append({
            "file": path.name, "csv": members[0], "nationwide_rows": total,
            "site_rows_all_summary_types": site_count,
            "url": f"https://aqs.epa.gov/aqsweb/airdata/{path.name}",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "original_download_date": "not recorded",
        })
        print(f"Read {path.name}: {total:,} source rows; {site_count:,} site rows", flush=True)
    data = pd.concat(parts, ignore_index=True)
    data["Date Local"] = pd.to_datetime(data["Date Local"], errors="coerce")
    for col in ["Arithmetic Mean", "Observation Count", "Observation Percent", "POC", "Method Code"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    return data, sources


def clean_daily(selected):
    """One real daily average with >=18 readings; retain every calendar date."""
    selected = selected.dropna(subset=["Date Local", "Arithmetic Mean"]).copy()
    selected = selected.loc[selected["Observation Count"] >= 18].copy()
    selected["Event Priority"] = selected["Event Type"].map(
        {"Included": 2, "None": 1, "Excluded": 0}
    ).fillna(1)
    selected = selected.sort_values(
        ["Date Local", "Event Priority"], ascending=[True, False], kind="stable"
    ).drop_duplicates("Date Local", keep="first")
    selected = selected[list(RENAME)].rename(columns=RENAME)
    return selected.set_index("Date").reindex(CALENDAR).rename_axis("Date").reset_index()


def main():
    site, sources = read_site()
    corrected = (
        ((site["Date Local"] < CUTOFF) & (site["POC"] == 23) & (site["Method Code"] == 736))
        | ((site["Date Local"] >= CUTOFF) & (site["POC"] == 3) & (site["Method Code"] == 636))
    )
    observed = {
        "poc3": clean_daily(site.loc[site["POC"] == 3]),
        "corrected_poc": clean_daily(site.loc[corrected]),
    }
    destination = ROOT / "data/processed"
    destination.mkdir(parents=True, exist_ok=True)
    audit = {"sources": sources, "datasets": {}}
    for label, frame in observed.items():
        if frame["Date"].duplicated().any() or len(frame) != 1826:
            raise ValueError("Invalid daily calendar")
        # These are input-data invariants, not conditions chosen from test errors.
        if frame["PM2.5"].isna().sum() != 67:
            raise ValueError("Source data changed: inspect the missing-date count")
        name = f"albemarle_pm25_{label}_without_interpolation.csv"
        previous_path = destination / name
        if previous_path.exists():
            previous = pd.read_csv(previous_path, parse_dates=["Date"])
            if not frame["Date"].equals(previous["Date"]) or not np.allclose(
                frame["PM2.5"], previous["PM2.5"], equal_nan=True
            ):
                raise ValueError(f"Existing pollution series differs: {name}")
        frame.to_csv(previous_path, index=False)
        filled = frame.copy()
        filled["PM2.5_Original"] = filled["PM2.5"]
        filled["PM2.5"] = filled["PM2.5_Original"].ffill()
        filled["Was_Filled"] = filled["PM2.5_Original"].isna() & filled["PM2.5"].notna()
        filled["Fill_Source_Date"] = filled["Date"].where(filled["PM2.5_Original"].notna()).ffill()
        estimated = filled["Was_Filled"]
        if not (filled.loc[estimated, "Fill_Source_Date"] < filled.loc[estimated, "Date"]).all():
            raise ValueError("A filled value used a future source date")
        filled.to_csv(destination / f"albemarle_pm25_{label}_forward_filled.csv", index=False)
        audit["datasets"][label] = {
            "calendar_days": len(frame), "observed_days": int(frame["PM2.5"].notna().sum()),
            "missing_days": int(frame["PM2.5"].isna().sum()),
            "missing_by_year": {str(y): int(g["PM2.5"].isna().sum())
                                for y, g in frame.groupby(frame["Date"].dt.year)},
            "forward_filled_days": int(estimated.sum()),
            "leading_missing_after_fill": int(filled["PM2.5"].isna().sum()),
        }
        print(label, audit["datasets"][label], flush=True)
    (destination / "preprocessing_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("Four datasets regenerated. No forecast results were used or changed.")


if __name__ == "__main__":
    main()
