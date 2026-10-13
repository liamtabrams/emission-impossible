import json

import transform
from collectors import bea, eia
from fastapi import FastAPI, HTTPException

app = FastAPI()


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
def get_data(state: str | None = None, start_year: int | None = None, end_year: int | None = None):
    """Rows of the processed table (one per state per year), optionally filtered by state and years."""
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
    # to_json then json.loads gives plain Python numbers that FastAPI can return
    return json.loads(table.to_json(orient="records"))
