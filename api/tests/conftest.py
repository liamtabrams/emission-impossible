"""Shared test fixtures: synthetic raw files shaped like the real EIA and BEA data,
and a fake bucket so tests never touch GCS.

The EIA layout mirrors the real workbooks (see the prototype's data_inspection.ipynb):
a 'Contents' sheet first, then on each data sheet a title row, a blank row, a header
row of 'State' followed by years as floats (1960.0 ... 2024.0), one row per state
(two-letter code), a 'US' total row, and footnotes underneath.

The BEA layout mirrors the real SAGDP9 reply: BEAAPI -> Results -> Data, one record
per geography per year, with the US total and 8 BEA regions mixed in, and DataValue
as text with thousands separators.
"""

import io
import json

import numpy as np
import pandas as pd
import pytest
from google.api_core.exceptions import NotFound

import main
import transform

STATES = sorted(transform.STATE_CODES.values())
STATE_NAMES = {code: name for name, code in transform.STATE_CODES.items()}
EIA_YEARS = list(range(1960, 2025))
BEA_YEARS = list(range(1997, 2026))
BEA_NON_STATES = [
    "United States",
    "New England",
    "Mideast",
    "Great Lakes",
    "Plains",
    "Southeast",
    "Southwest",
    "Rocky Mountain",
    "Far West",
]
FUEL_SHEETS = ["Coal", "Natural gas", "Petroleum"]
SECTOR_SHEETS = [
    "Residential",
    "Commercial",
    "Industrial",
    "Transportation",
    "Electric power",
]
MONTH = "2026-10"


def make_frames(seed=0):
    """Synthetic source data as wide tables (rows = states + 'US', columns = years).

    Tests can edit these before rendering them into files.
    """
    rng = np.random.default_rng(seed)
    rows = STATES + ["US"]

    def wide(low, high):
        values = rng.uniform(low, high, (len(rows), len(EIA_YEARS))).round(3)
        return pd.DataFrame(values, index=rows, columns=EIA_YEARS)

    fuels = {name: wide(1, 60) for name in FUEL_SHEETS}
    total = sum(fuels.values()).round(3)

    # split total into five sectors; the last one takes the remainder so they add up
    # (every share is at least 5% so the remainder never goes negative)
    shares = 0.05 + 0.75 * rng.dirichlet(np.ones(len(SECTOR_SHEETS)), size=len(rows))
    sectors = {}
    for i, name in enumerate(SECTOR_SHEETS[:-1]):
        sectors[name] = total.mul(shares[:, i], axis=0).round(3)
    sectors[SECTOR_SHEETS[-1]] = (total - sum(sectors.values())).round(3)

    # real GDP in millions of chained 2017 dollars, growing ~2% a year
    base = rng.uniform(30_000, 3_000_000, len(STATES))
    growth = 1.02 ** np.arange(len(BEA_YEARS))
    gdp = pd.DataFrame(np.outer(base, growth).round(1), index=STATES, columns=BEA_YEARS)

    # EIA's published intensity, made with a slightly different GDP vintage (+/-1%)
    overlap = [y for y in EIA_YEARS if y in BEA_YEARS]
    noise = rng.uniform(0.99, 1.01, (len(STATES), len(overlap)))
    published = (total.loc[STATES, overlap] * 1e6 / gdp[overlap] * noise).round(1)

    return {
        "fuels": fuels,
        "total": total,
        "sectors": sectors,
        "gdp": gdp,
        "published_intensity": published,
    }


def eia_sheet(title, wide):
    """Lay a wide table out the way EIA's sheets look."""
    years = list(wide.columns)
    width = len(years) + 1
    rows = [
        [title] + [None] * (width - 1),
        [None] * width,
        ["State"] + [float(y) for y in years],
    ]
    for state, values in wide.iterrows():
        rows.append([state] + list(values))
    rows.append([None] * width)
    rows.append(["Source: U.S. Energy Information Administration"] + [None] * (width - 1))
    return pd.DataFrame(rows)


def eia_workbook(sheets):
    """Bytes of an .xlsx with a Contents sheet followed by the given data sheets."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        contents = pd.DataFrame([["U.S. Energy Information Administration"], ["Contents"]])
        contents.to_excel(writer, sheet_name="Contents", header=False, index=False)
        for name, table in sheets.items():
            table.to_excel(writer, sheet_name=name, header=False, index=False)
    return buffer.getvalue()


def bea_reply(gdp, data_value_overrides=None):
    """Bytes of a BEA SAGDP9 JSON reply, including the US total and regions.

    data_value_overrides maps (GeoName, year) to the DataValue text to send instead,
    or to None to leave that record out.
    """
    overrides = data_value_overrides or {}
    records = []
    for year in BEA_YEARS:
        us_total = gdp[year].sum()
        for name in BEA_NON_STATES:
            records.append((name, year, us_total))
        for state in gdp.index:
            records.append((STATE_NAMES[state], year, gdp.loc[state, year]))
    data = []
    for name, year, value in records:
        text = overrides.get((name, year), f"{value:,.1f}")
        if text is None:  # None in the overrides = BEA left this record out
            continue
        data.append(
            {
                "Code": "SAGDP9-1",
                "GeoFips": "00000",
                "GeoName": name,
                "TimePeriod": str(year),
                "CL_UNIT": "Millions of chained 2017 dollars",
                "UNIT_MULT": "6",
                "DataValue": text,
            }
        )
    return json.dumps({"BEAAPI": {"Results": {"Data": data}}}).encode()


def render(frames, include_published=True, bea_overrides=None):
    """Turn frames into the raw files: ({file name: bytes} for EIA, BEA bytes)."""
    total_sheets = {"Total CO2": eia_sheet("Total CO2, million metric tons", frames["total"])}
    if include_published:
        total_sheets["CO2 per million dollars"] = eia_sheet(
            "CO2 per million dollars", frames["published_intensity"]
        )
    eia_files = {
        "CO2_total.xlsx": eia_workbook(total_sheets),
        "CO2_source.xlsx": eia_workbook(
            {name: eia_sheet(name, frames["fuels"][name]) for name in FUEL_SHEETS}
            | {"Total": eia_sheet("Total", frames["total"])}
        ),
        "CO2_sector.xlsx": eia_workbook(
            {name: eia_sheet(name, frames["sectors"][name]) for name in SECTOR_SHEETS}
            | {"Total": eia_sheet("Total", frames["total"])}
        ),
    }
    return eia_files, bea_reply(frames["gdp"], bea_overrides)


def bucket_paths(eia_files, bea_bytes, month=MONTH):
    """Where the collectors would have saved these files."""
    paths = {f"raw/eia_co2/{month}/{name}": data for name, data in eia_files.items()}
    paths[f"raw/bea_gdp/downloaded_{month}/{transform.BEA_FILE}"] = bea_bytes
    return paths


@pytest.fixture(scope="session")
def frames():
    return make_frames()


@pytest.fixture(scope="session")
def raw_files(frames):
    """(eia_files, bea_bytes) built from the default synthetic data."""
    return render(frames)


@pytest.fixture
def fake_bucket(monkeypatch):
    """A dict standing in for the GCS bucket, wired into transform.py."""
    bucket = {}

    def list_files(key, project, bucket_name, prefix):
        return [name for name in bucket if name.startswith(prefix)]

    def download(key, project, bucket_name, name):
        if name not in bucket:
            raise NotFound(f"{name} not found")
        data = bucket[name]
        return data.encode() if isinstance(data, str) else data

    def upload(key, project, bucket_name, name, data):
        bucket[name] = data

    monkeypatch.setattr(transform, "list_gcs_files", list_files)
    monkeypatch.setattr(transform, "download_from_gcs", download)
    monkeypatch.setattr(transform, "upload_to_gcs", upload)
    return bucket


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(main.app)
