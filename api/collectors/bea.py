import datetime
import json

import requests
from fastapi import HTTPException
from storage import upload_to_gcs
from user_definition import bea_api_key, bucket_name, project_id, service_account_key

# GCS folder where the raw BEA files are stored.
file_name_prefix = "raw/bea_gdp"

BEA_URL = "https://apps.bea.gov/api/data"


# For "TableName": "SAGDP9" stores real GDP by state, millions of chained 2017 dollars
def fetch_from_bea():
    """Call the BEA API for real GDP by state and return the JSON reply."""
    params = {
        "UserID": bea_api_key,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": "SAGDP9",
        "LineCode": "1",
        "GeoFips": "STATE",
        "Year": "ALL",
        "ResultFormat": "JSON",
    }
    try:
        response = requests.get(BEA_URL, params=params, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # Show only the error type: the full error message can include the URL with the API key
        raise HTTPException(
            status_code=502,
            detail=f"Could not get data from BEA: {type(e).__name__}. "
            "No new file was saved, so /transform keeps using the last saved BEA file.",
        )


def collect():
    """Fetch real GDP by state from BEA and save the raw JSON to GCS."""
    if not bea_api_key:
        raise HTTPException(status_code=500, detail="BEA_API_KEY is not set")

    month = datetime.date.today().strftime("%Y-%m")
    print("Requesting real GDP by state from BEA..", flush=True)
    data = fetch_from_bea()

    # BEA replies with status 200 even when it fails, so check the JSON for an error or empty data
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
    # Remove the "Request" part, because BEA's response includes our API key
    data["BEAAPI"].pop("Request", None)

    upload_to_gcs(
        service_account_key, project_id, bucket_name, file_name, json.dumps(data)
    )

    print(f"Saved {len(rows)} BEA rows to {file_name}", flush=True)

    return {"month": month, "rows": len(rows), "files_stored": [file_name]}
