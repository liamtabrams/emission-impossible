"""Joining CO2 and GDP, carbon intensity, and the checks that guard the saved table."""

import pandas as pd
import pytest
from fastapi import HTTPException

import transform
from conftest import STATE_NAMES, STATES, make_frames, render


@pytest.fixture(scope="module")
def table(raw_files):
    eia_files, bea_bytes = raw_files
    return transform.build_table(eia_files, bea_bytes)


def expect_check_failure(eia_files, bea_bytes, *phrases):
    table = transform.build_table(eia_files, bea_bytes)
    with pytest.raises(HTTPException) as error:
        transform.check_table(table)
    assert error.value.status_code == 500
    for phrase in phrases:
        assert phrase in error.value.detail, error.value.detail
    return error.value.detail


def test_join_keeps_only_years_both_sources_have(table):
    # EIA has 1960-2024, BEA has 1997-2025 -> 1997-2024, 28 years x 51 states
    assert len(table) == 51 * 28 == 1428
    assert table["year"].min() == 1997 and table["year"].max() == 2024
    assert set(table["state"]) == set(STATES)


def test_columns_are_in_the_documented_order(table):
    assert list(table.columns) == (
        ["state", "year", "co2", "gdp", "intensity"]
        + transform.FUEL_COLUMNS
        + transform.SECTOR_COLUMNS
    )


def test_intensity_is_tonnes_per_million_dollars(table, frames):
    for state, year in [("CA", 1997), ("WY", 2024), ("DC", 2010)]:
        row = table.query("state == @state and year == @year").iloc[0]
        co2 = frames["total"].loc[state, year]  # million tonnes
        gdp = frames["gdp"].loc[state, year]  # million dollars
        assert row["co2"] == pytest.approx(co2)
        assert row["intensity"] == pytest.approx(co2 * 1_000_000 / gdp, rel=1e-6)


def test_fuel_and_sector_columns_line_up_with_their_sheets(table, frames):
    row = table.query("state == 'OH' and year == 2005").iloc[0]
    assert row["co2_coal"] == pytest.approx(frames["fuels"]["Coal"].loc["OH", 2005])
    assert row["co2_electric_power"] == pytest.approx(
        frames["sectors"]["Electric power"].loc["OH", 2005]
    )


def test_good_table_passes_checks(table):
    summary = transform.check_table(table)
    assert summary["states"] == 51
    assert summary["years"] == [1997, 2024]
    assert summary["rows_per_state"] == 28
    assert summary["duplicates"] == 0
    assert summary["missing_values"] == 0
    assert summary["max_fuel_gap"] <= transform.SUM_TOLERANCE
    assert summary["max_sector_gap"] <= transform.SUM_TOLERANCE


def test_missing_state_fails():
    frames = make_frames()
    frames["gdp"] = frames["gdp"].drop(index="WY")  # BEA has no Wyoming
    eia_files, bea_bytes = render(frames)
    expect_check_failure(eia_files, bea_bytes, "missing states: WY")


def test_missing_year_for_one_state_fails():
    eia_files, bea_bytes = render(
        make_frames(), bea_overrides={(STATE_NAMES["AL"], 2005): None}
    )
    expect_check_failure(eia_files, bea_bytes, "1 states are missing years", "AL missing [2005]")


def test_blank_gdp_value_fails():
    eia_files, bea_bytes = render(
        make_frames(), bea_overrides={(STATE_NAMES["AL"], 2005): "(NA)"}
    )
    # BEA's "(NA)" becomes a blank GDP (and a blank intensity)
    expect_check_failure(eia_files, bea_bytes, "missing values", "'gdp': 1")


def test_duplicate_rows_fail(table):
    doubled = pd.concat([table, table.head(1)], ignore_index=True)
    with pytest.raises(HTTPException) as error:
        transform.check_table(doubled)
    assert "1 duplicate" in error.value.detail


def test_zero_gdp_fails(table):
    broken = table.copy()
    broken.loc[0, "gdp"] = 0
    with pytest.raises(HTTPException) as error:
        transform.check_table(broken)
    assert "GDP <= 0" in error.value.detail


def test_fuels_not_adding_up_to_total_fails():
    frames = make_frames()
    frames["fuels"]["Coal"].loc["KY", 2010] += 5.0  # coal sheet misread
    eia_files, bea_bytes = render(frames)
    expect_check_failure(eia_files, bea_bytes, "fuel columns differ", "KY 2010")


def test_sectors_not_adding_up_to_total_fails():
    frames = make_frames()
    frames["sectors"]["Transportation"].loc["NV", 2015] -= 1.0
    eia_files, bea_bytes = render(frames)
    expect_check_failure(eia_files, bea_bytes, "sector columns differ", "NV 2015")


def test_empty_table_fails(table):
    with pytest.raises(HTTPException) as error:
        transform.check_table(table.iloc[0:0])
    assert "empty" in error.value.detail
