"""Decoupling categories and % changes, on small hand-made tables."""

import pandas as pd
import pytest
from fastapi import HTTPException

from analysis import classify, decoupling_table


@pytest.mark.parametrize(
    "pct_gdp, pct_co2, category",
    [
        (30, -10, "Absolute decoupling"),  # GDP up, CO2 down
        (30, 10, "Relative decoupling"),  # both up, CO2 slower
        (30, 30, "No decoupling"),  # CO2 as fast as GDP
        (30, 45, "No decoupling"),  # CO2 faster
        (-5, -20, "Contraction"),  # GDP fell
        (0, -20, "Contraction"),  # GDP flat counts as contraction
    ],
)
def test_classify(pct_gdp, pct_co2, category):
    assert classify(pct_gdp, pct_co2) == category


def make_table(rows):
    table = pd.DataFrame(rows, columns=["state", "year", "co2", "gdp"])
    table["intensity"] = table["co2"] * 1_000_000 / table["gdp"]
    return table


def test_decoupling_table_numbers_and_categories():
    table = make_table(
        [
            ("AA", 2000, 100, 1000), ("AA", 2010, 80, 1500),   # GDP +50%, CO2 -20%
            ("BB", 2000, 100, 1000), ("BB", 2010, 110, 1500),  # GDP +50%, CO2 +10%
            ("CC", 2000, 100, 1000), ("CC", 2010, 160, 1500),  # GDP +50%, CO2 +60%
            ("DD", 2000, 100, 1000), ("DD", 2010, 90, 900),    # GDP -10%
        ]
    )
    out = decoupling_table(table, 2000, 2010).set_index("state")

    assert out.loc["AA", "pct_gdp"] == pytest.approx(50)
    assert out.loc["AA", "pct_co2"] == pytest.approx(-20)
    # intensity: (80/1500) / (100/1000) - 1 = -46.67%
    assert out.loc["AA", "pct_intensity"] == pytest.approx(-46.6667, abs=1e-3)
    assert out["category"].to_dict() == {
        "AA": "Absolute decoupling",
        "BB": "Relative decoupling",
        "CC": "No decoupling",
        "DD": "Contraction",
    }


def test_decoupling_table_skips_states_missing_a_year():
    table = make_table(
        [("AA", 2000, 100, 1000), ("AA", 2010, 80, 1500), ("BB", 2010, 110, 1500)]
    )
    assert list(decoupling_table(table, 2000, 2010)["state"]) == ["AA"]


@pytest.mark.parametrize("start, end", [(2010, 2000), (2000, 2000), (1990, 2010)])
def test_decoupling_table_rejects_bad_years(start, end):
    table = make_table([("AA", 2000, 100, 1000), ("AA", 2010, 80, 1500)])
    with pytest.raises(HTTPException) as error:
        decoupling_table(table, start, end)
    assert error.value.status_code == 400
