import datetime

import requests
from fastapi import HTTPException

from storage import upload_to_gcs
from user_definition import *

# GCS folder where all EIA CO2 files are stored under.
file_name_prefix = "raw/eia_co2"

# three EIA "ranked by state" CO2 workbooks.
eia_co2_files = {
    "co2_total": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_total.xlsx",
    "co2_source": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_source.xlsx",
    "co2_sector": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_sector.xlsx",
}

def collect():
    """Download each EIA CO2 workbook and save it to GCS one folder per month."""
    month = datetime.date.today().strftime("%Y-%m")
    stored = []

    for name, url in eia_co2_files.items():
        try:
            # download the workbook through API call to EIA
            response = requests.get(url, timeout=60)
            response.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=502,
                detail=f"Could not download {name} from EIA: {e}",
            )
        original_file_name = url.split("/")[-1]
        file_name = f"{file_name_prefix}/{month}/{original_file_name}"
        upload_to_gcs(service_account_key, project_id, bucket_name,
                      file_name, response.content)
        stored.append(file_name)

    return {"month": month, "files_stored": stored}
