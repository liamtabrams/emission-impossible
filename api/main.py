import transform
from collectors import bea, eia
from fastapi import FastAPI

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
    """Clean the raw EIA CO2 excel files and BEA GDP json, join them by state, year, add carbon intensity, and save the processed csv."""
    return transform.create_processed_csv()
