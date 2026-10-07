# FastAPI routes
import logging

import transform
from collectors import bea, eia
from fastapi import FastAPI

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)

for logger_name in ["collectors", "transform"]:
    logging.getLogger(logger_name).addHandler(handler)
    logging.getLogger(logger_name).setLevel(logging.INFO)

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
    """Clean the newest raw EIA CO2 workbooks and BEA GDP file, join them by state
    and year, add carbon intensity, and save processed/co2_gdp_by_state_year.csv."""
    return transform.create_processed_csv()
