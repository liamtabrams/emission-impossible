import datetime
import json
import logging
import time

import requests
from fastapi import HTTPException
from storage import upload_to_gcs
from user_definition import bea_api_key, bucket_name, project_id, service_account_key

logger = logging.getLogger(__name__)

# GCS folder where the raw BEA files are stored (one sub-folder per month).
file_name_prefix = "raw/bea_gdp"

BEA_URL = "https://apps.bea.gov/api/data"

MAX_TRIES = 3  # try the request up to 3 times
WAIT_SECONDS = 5  # wait between tries


def fetch_from_bea():
    """Ask the BEA API for real GDP by state and return the JSON reply.
    Tries up to MAX_TRIES times if the request fails."""
    params = {
        "UserID": bea_api_key,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": "SAGDP9",  # real GDP by state, millions of chained 2017 dollars
        "LineCode": "1",  # all industries combined
        "GeoFips": "STATE",  # every state
        "Year": "ALL",  # every year available
        "ResultFormat": "JSON",
    }
    for attempt in range(1, MAX_TRIES + 1):
        try:
            response = requests.get(BEA_URL, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # log only the error type
            error_type = type(e).__name__
            logger.warning(
                f"BEA request failed (try {attempt} of {MAX_TRIES}): {error_type}"
            )
            if attempt < MAX_TRIES:
                time.sleep(WAIT_SECONDS)

    raise HTTPException(
        status_code=502, detail=f"Could not get data from BEA after {MAX_TRIES} tries"
    )


def collect():
    """Fetch real GDP by state from BEA and save the raw JSON to GCS, one folder per month."""
    if not bea_api_key:
        raise HTTPException(status_code=500, detail="BEA_API_KEY is not set")

    month = datetime.date.today().strftime("%Y-%m")
    logger.info("Requesting real GDP by state from BEA")
    data = fetch_from_bea()

    # BEA reports problems (such as a wrong key) inside the JSON with HTTP status 200,
    # so raise_for_status() doesn't catch them.
    bea_reply = data.get("BEAAPI", {})
    results = bea_reply.get("Results", {})
    error = bea_reply.get("Error") or results.get("Error")
    if error:
        message = error.get("APIErrorDescription", "unknown error")
        raise HTTPException(status_code=502, detail=f"BEA returned an error: {message}")

    rows = results.get("Data", [])
    if not rows:
        raise HTTPException(status_code=502, detail="BEA returned no data rows")

    file_name = (
        f"{file_name_prefix}/downloaded_{month}/real_gdp_by_state_all_years.json"
    )

    data["BEAAPI"].pop("Request", None)

    # Save the reply as it came (minus the key) so the transform step can read it later.
    upload_to_gcs(
        service_account_key, project_id, bucket_name, file_name, json.dumps(data)
    )
    logger.info(f"Saved {len(rows)} BEA rows to {file_name}")

    return {"month": month, "rows": len(rows), "files_stored": [file_name]}
