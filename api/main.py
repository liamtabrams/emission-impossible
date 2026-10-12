import json

import analysis
import transform
from collectors import bea, eia
from fastapi import FastAPI, HTTPException

app = FastAPI()


def to_records(table):
    """Turn a DataFrame into a list of plain dicts that FastAPI can return as JSON."""
    return json.loads(table.to_json(orient="records"))


@app.post("/ingest/eia")
def ingest_eia():
    return eia.collect()


@app.post("/ingest/bea")
def ingest_bea():
    """Download real GDP by state from the BEA API and save the raw JSON to the bucket."""
    return bea.collect()


@app.post("/transform")
def run_transform():
    """Clean the raw EIA CO2 excel files and BEA GDP json, join them by state, year, add carbon intensity, check the result, and save the processed csv."""
    return transform.create_processed_csv()


@app.get("/data")
def get_data(
    state: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
):
    """Rows of the processed table (one per state per year), optionally filtered."""
    table = transform.load_processed_table()
    if state:
        state = state.upper()
        if state not in set(table["state"]):
            raise HTTPException(status_code=404, detail=f"Unknown state '{state}'")
        table = table[table["state"] == state]
    if start_year is not None:
        table = table[table["year"] >= start_year]
    if end_year is not None:
        table = table[table["year"] <= end_year]
    return to_records(table)


@app.get("/decoupling")
def get_decoupling(start_year: int | None = None, end_year: int | None = None):
    """Each state's % change in GDP, CO2 and carbon intensity between two years, and its
    decoupling category. Defaults to the first and last year available."""
    table = transform.load_processed_table()
    if start_year is None:
        start_year = int(table["year"].min())
    if end_year is None:
        end_year = int(table["year"].max())
    return to_records(analysis.decoupling_table(table, start_year, end_year))
