# Decoupling between two years, calculated from the processed table on request.
# Ported from the prototype's transform.decoupling_table / _classify.
import pandas as pd
from fastapi import HTTPException

CATEGORIES = [
    "Absolute decoupling",  # GDP up, CO2 down
    "Relative decoupling",  # both up, CO2 slower than GDP
    "No decoupling",  # CO2 up as fast as GDP or faster
    "Contraction",  # GDP fell (treated separately)
]


def classify(pct_gdp, pct_co2):
    """Decoupling category from the % change in real GDP and in CO2."""
    if pct_gdp <= 0:
        return "Contraction"
    if pct_co2 < 0:
        return "Absolute decoupling"
    if pct_co2 < pct_gdp:
        return "Relative decoupling"
    return "No decoupling"


def decoupling_table(table, start_year, end_year):
    """One row per state: % change in GDP, CO2, and intensity, plus the category."""
    years = set(table["year"])
    if start_year not in years or end_year not in years:
        raise HTTPException(
            status_code=400,
            detail=f"Years must be between {min(years)} and {max(years)}",
        )
    if end_year <= start_year:
        raise HTTPException(
            status_code=400, detail="end_year must be after start_year"
        )

    columns = ["gdp", "co2", "intensity"]
    start = table[table["year"] == start_year].set_index("state")[columns]
    end = table[table["year"] == end_year].set_index("state")[columns]
    states = sorted(start.index.intersection(end.index))
    change = (end.loc[states] / start.loc[states] - 1) * 100

    out = pd.DataFrame(
        {
            "state": states,
            "pct_gdp": change["gdp"].values,
            "pct_co2": change["co2"].values,
            "pct_intensity": change["intensity"].values,
        }
    )
    out["category"] = [
        classify(g, c) for g, c in zip(out["pct_gdp"], out["pct_co2"])
    ]
    return out
