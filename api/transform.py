import io
import json

import pandas as pd
from fastapi import HTTPException
from google.api_core.exceptions import NotFound
from storage import download_from_gcs, list_gcs_files, upload_to_gcs
from user_definition import bucket_name, project_id, service_account_key

EIA_FOLDER = "raw/eia_co2"
EIA_FILES = ["CO2_total.xlsx", "CO2_source.xlsx", "CO2_sector.xlsx"]
BEA_FOLDER = "raw/bea_gdp"
BEA_FILE = "real_gdp_by_state_all_years.json"
PROCESSED_FILE = "processed/co2_gdp_by_state_year.csv"

EIA_SHEETS = [
    ("CO2_total.xlsx", "Total CO2", "co2"),
    ("CO2_source.xlsx", "Coal", "co2_coal"),
    ("CO2_source.xlsx", "Natural gas", "co2_natural_gas"),
    ("CO2_source.xlsx", "Petroleum", "co2_petroleum"),
    ("CO2_sector.xlsx", "Residential", "co2_residential"),
    ("CO2_sector.xlsx", "Commercial", "co2_commercial"),
    ("CO2_sector.xlsx", "Industrial", "co2_industrial"),
    ("CO2_sector.xlsx", "Transportation", "co2_transportation"),
    ("CO2_sector.xlsx", "Electric power", "co2_electric_power"),
]

FUEL_COLUMNS = ["co2_coal", "co2_natural_gas", "co2_petroleum"]

SECTOR_COLUMNS = [
    "co2_residential",
    "co2_commercial",
    "co2_industrial",
    "co2_transportation",
    "co2_electric_power",
]

SUM_TOLERANCE = 0.01  # million metric tons; EIA rounds every value to 3 decimals
EIA_INTENSITY_FILE = "CO2_total.xlsx"
EIA_INTENSITY_SHEET = "CO2 per million dollars"
MAX_MEDIAN_PCT_DIFF = 5.0  # above this it's a units or join mistake, not a GDP revision

STATE_CODES = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}


def find_newest_file(folder, file_name):
    """Return the path of the newest copy of file_name under folder and sort by date so the last one is the newest."""
    paths = list_gcs_files(service_account_key, project_id, bucket_name, folder + "/")
    matches = sorted(path for path in paths if path.endswith("/" + file_name))
    if not matches:
        message = f"No {file_name} found under {folder}/. Run the collector first."
        raise HTTPException(status_code=404, detail=message)
    return matches[-1]


def clean_eia_sheet(workbook_bytes, sheet, column):
    """Clean one EIA sheet into a table with one row per state per year."""
    raw = pd.read_excel(io.BytesIO(workbook_bytes), sheet_name=sheet, header=None)

    first_column = raw[0].astype(str).str.strip()
    header_rows = raw.index[first_column == "State"]
    if len(header_rows) == 0:
        raise HTTPException(
            status_code=500, detail=f"No 'State' header row in EIA sheet '{sheet}'"
        )
    header_row = header_rows[0]
    table = raw.iloc[header_row + 1 :].copy()
    column_names = list(raw.iloc[header_row])
    column_names[0] = "state"
    table.columns = column_names

    table["state"] = table["state"].astype(str).str.strip()
    table = table[table["state"].isin(STATE_CODES.values())]

    year_columns = [name for name in table.columns if str(name)[:4].isdigit()]
    table = table[["state"] + year_columns]

    # Reshape from one column per year to one row per state per year
    long = table.melt(id_vars="state", var_name="year", value_name=column)
    long["year"] = long["year"].astype(float).astype(int)
    long[column] = pd.to_numeric(long[column], errors="coerce")

    raw_row_count = len(raw)
    state_count = table["state"].nunique()
    year_count = len(year_columns)
    row_count = len(long)
    print(
        f"EIA {sheet}: {raw_row_count} raw rows cleaned to {state_count} states x {year_count} years = {row_count} rows",
        flush=True,
    )

    return long


def clean_bea_gdp(json_bytes):
    """Clean the BEA JSON reply into a table with columns state, year and gdp, one row per state per year."""
    reply = json.loads(json_bytes)
    rows = reply["BEAAPI"]["Results"]["Data"]
    gdp = pd.DataFrame(rows)

    gdp["state"] = gdp["GeoName"].str.strip().map(STATE_CODES)
    gdp = gdp[gdp["state"].notna()].copy()

    gdp["year"] = gdp["TimePeriod"].astype(int)
    gdp["gdp"] = pd.to_numeric(gdp["DataValue"].str.replace(",", ""), errors="coerce")

    raw_row_count = len(rows)
    state_count = gdp["state"].nunique()
    row_count = len(gdp)
    print(
        f"BEA: {raw_row_count} raw rows cleaned to {state_count} states = {row_count} rows",
        flush=True,
    )

    return gdp[["state", "year", "gdp"]]


def build_table(eia_files, bea_bytes):
    """Combine the EIA and BEA data into one table by state and year."""
    sheet_tables = [
        clean_eia_sheet(eia_files[file_name], sheet, column)
        for file_name, sheet, column in EIA_SHEETS
    ]
    table = sheet_tables[0]
    for sheet_table in sheet_tables[1:]:
        table = table.merge(sheet_table, on=["state", "year"], how="left")

    # join with GDP
    gdp = clean_bea_gdp(bea_bytes)
    table = table.merge(gdp, on=["state", "year"], how="inner")

    # co2 is in million tonnes, gdp in millions of dollars
    table["intensity"] = table["co2"] * 1_000_000 / table["gdp"]

    columns = (
        ["state", "year", "co2", "gdp", "intensity"] + FUEL_COLUMNS + SECTOR_COLUMNS
    )
    return table[columns].sort_values(["state", "year"]).reset_index(drop=True)


def fail(message):
    """Print the reason (so it shows in the Cloud Run logs) and stop with a 500 error."""
    print(message, flush=True)
    raise HTTPException(status_code=500, detail=message)


def check_table(table):
    """Stop with a 500 error if the joined table is incomplete or inconsistent, else return a summary."""
    if table.empty:
        fail("Processed table is empty")
    problems = []

    duplicates = int(table.duplicated(["state", "year"]).sum())
    if duplicates:
        problems.append(f"{duplicates} duplicate state-year rows")

    missing_states = sorted(set(STATE_CODES.values()) - set(table["state"]))
    if missing_states:
        problems.append(f"missing states: {', '.join(missing_states)}")

    all_years = set(range(table["year"].min(), table["year"].max() + 1))
    gaps = {}
    for state, years in table.groupby("state")["year"]:
        if set(years) != all_years:
            gaps[state] = sorted(all_years - set(years))
    if gaps:
        examples = "; ".join(f"{state} missing {years[:5]}" for state, years in list(gaps.items())[:5])
        problems.append(f"{len(gaps)} states are missing years ({examples})")

    missing = table.isna().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        problems.append(f"missing values: {missing.to_dict()}")

    if (table["gdp"] <= 0).any():
        problems.append(f"{int((table['gdp'] <= 0).sum())} rows with GDP <= 0")

    # the fuel columns and the sector columns should each add up to total CO2
    largest_gap = {}
    for name, columns in [("fuel", FUEL_COLUMNS), ("sector", SECTOR_COLUMNS)]:
        gap = (table[columns].sum(axis=1) - table["co2"]).abs()
        largest_gap[name] = round(float(gap.max()), 4)
        if gap.max() > SUM_TOLERANCE:
            worst = table.loc[gap.idxmax()]
            problems.append(f"{name} columns differ from total CO2 by up to {gap.max():.3f} "
                            f"million tonnes (worst: {worst['state']} {worst['year']})")

    summary = {
        "states": int(table["state"].nunique()),
        "years": [int(table["year"].min()), int(table["year"].max())],
        "rows_per_state": int(table.groupby("state").size().min()),
        "duplicates": duplicates,
        "missing_values": int(missing.sum()),
        "max_fuel_gap": largest_gap["fuel"],
        "max_sector_gap": largest_gap["sector"],
    }
    print(f"Checks: {summary}", flush=True)
    if problems:
        fail("Processed table failed checks: " + "; ".join(problems))
    return summary


def validate_against_eia(table, total_workbook_bytes):
    """Compare our intensity with EIA's published intensity, and stop with a 500 error
    if they differ by more than a GDP revision could explain."""
    try:
        published = clean_eia_sheet(total_workbook_bytes, EIA_INTENSITY_SHEET, "eia_intensity")
    except (HTTPException, ValueError) as e:
        reason = getattr(e, "detail", str(e))
        print(f"Skipped the EIA intensity comparison: {reason}", flush=True)
        return {"status": "skipped", "reason": reason}

    published = published[published["eia_intensity"] > 0]
    compared = table[["state", "year", "intensity"]].merge(published, on=["state", "year"])
    if compared.empty:
        fail(f"EIA '{EIA_INTENSITY_SHEET}' sheet shares no state-years with the table")

    # a ratio near 1 means the same units; near 1000 or 0.001 means a units mistake
    compared["ratio"] = compared["intensity"] / compared["eia_intensity"]
    pct_diff = (compared["ratio"] - 1).abs() * 100
    worst = compared.loc[pct_diff.nlargest(3).index, ["state", "year", "intensity", "eia_intensity"]]

    result = {
        "status": "passed",
        "rows_compared": len(compared),
        "median_abs_pct_diff": round(float(pct_diff.median()), 3),
        "max_abs_pct_diff": round(float(pct_diff.max()), 3),
        "median_ratio": round(float(compared["ratio"].median()), 4),
        "worst_rows": worst.round(2).to_dict(orient="records"),
    }
    print(f"EIA comparison: {result['rows_compared']} rows, median difference "
          f"{result['median_abs_pct_diff']}%, max {result['max_abs_pct_diff']}%", flush=True)
    if result["median_abs_pct_diff"] > MAX_MEDIAN_PCT_DIFF:
        fail(f"Intensity doesn't match EIA's published values: median difference "
             f"{result['median_abs_pct_diff']}% (limit {MAX_MEDIAN_PCT_DIFF}%), "
             f"median ratio ours/EIA {result['median_ratio']}")
    return result


def download_newest_raw_files():
    """Return the newest EIA workbooks (by file name), the newest BEA file, and their bucket paths."""
    sources = [find_newest_file(EIA_FOLDER, file_name) for file_name in EIA_FILES]
    sources.append(find_newest_file(BEA_FOLDER, BEA_FILE))
    files = [download_from_gcs(service_account_key, project_id, bucket_name, path) for path in sources]
    return dict(zip(EIA_FILES, files[:-1])), files[-1], sources


def build_checked_table(eia_files, bea_bytes):
    """Clean, join, check and validate. Returns the table and both reports."""
    table = build_table(eia_files, bea_bytes)
    checks = check_table(table)
    validation = validate_against_eia(table, eia_files[EIA_INTENSITY_FILE])
    return table, checks, validation


def create_processed_csv():
    """Download the newest raw files, clean and join them, and save the processed CSV to GCS."""
    eia_files, bea_bytes, sources = download_newest_raw_files()

    # Clean, join and check
    table, checks, validation = build_checked_table(eia_files, bea_bytes)

    # Save the processed table as CSV
    upload_to_gcs(
        service_account_key,
        project_id,
        bucket_name,
        PROCESSED_FILE,
        table.to_csv(index=False),
    )

    row_count = len(table)
    print(f"Saved {row_count} rows to {PROCESSED_FILE}", flush=True)

    return {
        "rows": row_count,
        "states": int(table["state"].nunique()),
        "years": [int(table["year"].min()), int(table["year"].max())],
        "columns": list(table.columns),
        "sources": sources,
        "file_stored": PROCESSED_FILE,
        "checks": checks,
        "validation": validation,
    }


def load_processed_table():
    """Read the processed CSV from the bucket (404 if /transform hasn't been run yet)."""
    try:
        data = download_from_gcs(service_account_key, project_id, bucket_name, PROCESSED_FILE)
    except NotFound:
        raise HTTPException(status_code=404, detail=f"{PROCESSED_FILE} not found. Run POST /transform first.")
    return pd.read_csv(io.BytesIO(data))
