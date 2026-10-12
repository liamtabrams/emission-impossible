"""Comparing our intensity to EIA's published 'CO2 per million dollars' sheet."""

import pytest
from fastapi import HTTPException

import transform
from conftest import make_frames, render


def build(frames, **kwargs):
    eia_files, bea_bytes = render(frames, **kwargs)
    table = transform.build_table(eia_files, bea_bytes)
    return table, eia_files["CO2_total.xlsx"]


def test_matches_eia_within_gdp_revisions(raw_files):
    eia_files, bea_bytes = raw_files
    table = transform.build_table(eia_files, bea_bytes)
    result = transform.validate_against_eia(table, eia_files["CO2_total.xlsx"])

    assert result["status"] == "passed"
    assert result["rows_compared"] == 1428
    assert result["median_abs_pct_diff"] < 1.0  # synthetic EIA values are within 1%
    assert result["median_ratio"] == pytest.approx(1.0, abs=0.01)
    assert len(result["worst_rows"]) == 3


def test_gdp_in_wrong_units_fails():
    # Pretend BEA sent billions instead of millions: our intensity is 1000x too big
    frames = make_frames()
    frames["gdp"] = frames["gdp"] / 1000
    table, total_workbook = build(frames)
    with pytest.raises(HTTPException) as error:
        transform.validate_against_eia(table, total_workbook)
    assert error.value.status_code == 500
    assert "median ratio ours/EIA 1000" in error.value.detail


def test_states_mixed_up_in_the_join_fails():
    # Simulate GDP landing on the wrong states: shift GDP rows by one state
    frames = make_frames()
    gdp = frames["gdp"]
    shuffled = gdp.copy()
    shuffled.iloc[:] = gdp.values[list(range(1, len(gdp))) + [0]]
    frames["gdp"] = shuffled
    table, total_workbook = build(frames)
    with pytest.raises(HTTPException) as error:
        transform.validate_against_eia(table, total_workbook)
    assert "doesn't match EIA" in error.value.detail


def test_missing_published_sheet_is_skipped_not_failed():
    table, total_workbook = build(make_frames(), include_published=False)
    result = transform.validate_against_eia(table, total_workbook)
    assert result["status"] == "skipped"
    assert "CO2 per million dollars" in result["reason"]
