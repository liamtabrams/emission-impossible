"""Cleaning each source into one row per state per year."""

import pandas as pd
import pytest
from fastapi import HTTPException

import transform
from conftest import BEA_YEARS, EIA_YEARS, STATES, eia_sheet, eia_workbook


def test_eia_sheet_becomes_one_row_per_state_per_year(raw_files, frames):
    eia_files, _ = raw_files
    co2 = transform.clean_eia_sheet(eia_files["CO2_total.xlsx"], "Total CO2", "co2")

    assert list(co2.columns) == ["state", "year", "co2"]
    assert len(co2) == len(STATES) * len(EIA_YEARS)
    assert not co2.duplicated(["state", "year"]).any()
    # the US total row and the footnote are dropped
    assert set(co2["state"]) == set(STATES)
    # header years arrive as floats (1960.0) and come out as ints
    assert co2["year"].dtype.kind == "i"
    assert co2["year"].min() == 1960 and co2["year"].max() == 2024
    # values land on the right state and year
    value = co2.query("state == 'CA' and year == 2010")["co2"].iloc[0]
    assert value == pytest.approx(frames["total"].loc["CA", 2010])


def test_eia_sheet_without_state_header_is_a_500():
    broken = pd.DataFrame([["Some title"], ["no header here"], ["AK"]])
    workbook = eia_workbook({"Total CO2": broken})
    with pytest.raises(HTTPException) as error:
        transform.clean_eia_sheet(workbook, "Total CO2", "co2")
    assert error.value.status_code == 500
    assert "State" in error.value.detail


def test_eia_sheet_values_that_are_not_numbers_become_blank(frames):
    wide = frames["total"].astype(object).copy()
    wide.loc["AK", 2000] = "(NA)"
    workbook = eia_workbook({"Total CO2": eia_sheet("Total", wide)})
    co2 = transform.clean_eia_sheet(workbook, "Total CO2", "co2")
    assert co2.query("state == 'AK' and year == 2000")["co2"].isna().all()


def test_bea_drops_us_and_regions_and_parses_numbers(raw_files, frames):
    _, bea_bytes = raw_files
    gdp = transform.clean_bea_gdp(bea_bytes)

    assert list(gdp.columns) == ["state", "year", "gdp"]
    assert set(gdp["state"]) == set(STATES)  # "United States", "Far West", ... are gone
    assert len(gdp) == len(STATES) * len(BEA_YEARS)
    # "1,234,567.8" -> 1234567.8
    value = gdp.query("state == 'TX' and year == 2020")["gdp"].iloc[0]
    assert value == pytest.approx(frames["gdp"].loc["TX", 2020], abs=0.05)
