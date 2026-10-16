# Emission Impossible

Which U.S. states have grown their economies while cutting carbon emissions? We collect emissions and economic data at the state level, combine them, and show the results in a Streamlit dashboard. 

- **Git repo:** https://github.com/liamtabrams/emission-impossible
- **GCP project:** `emission-impossible-510123` (bucket `gs://emission-impossible`, region `us-west1`)

---

## Team Members

| Name | GitHub ID | Role / Focus |
| --- | --- | --- |
| Liam Abrams | [liamtabrams](https://github.com/liamtabrams) | Transform and join; Dashboard |
| Nadeem Ahmedi | [nahmedi286179](https://github.com/nahmedi286179) | Transform and join; Analysis and final report |
| Darshini Mysore Harishwara | [DarshiniMH](https://github.com/DarshiniMH) | Data source extraction; Dashboard |
| Rini Khaneja | [rinikhaneja](https://github.com/rinikhaneja) | Data source extraction; Transform and join |
| Jung Hoon (John) An | [junghoona](https://github.com/junghoona) | Docker and GCP deployment |

---

## Problem Statement

**Which U.S. states have decoupled economic growth from carbon emissions, and what drove it?**

Most U.S. states' economies grew between 1997 and 2024. We want to know whether their carbon emissions grew as well, or whether they cut emissions. 
Some people argue that cutting emissions means giving up economic growth; we test that idea one state at a time. Since many energy policies are dictated by state, we show which states are getting cleaner and which are falling behind. 

**Key Terms**

-Real GDP (rGDP) - we use to measure the size of a state's economy. Real means adjusted for inflation.

-Carbon Intensity - how much CO2 a state releases for every $1 million of GDP. 

-Decoupling - when a state's economy grows, but emissions do not grow proportionately, or fall. 

-Absolute Decoupling - rGDP goes up CO2 emissions goes down

-Relative Decoupling - GDP goes up, CO2 emissions go up at a slower rate than GDP. 

-No decoupling - GDP goes up, CO2 emissions go up at the same rate or faster than GDP. 


---

## Data Sources

| # | Source | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [U.S. Energy Information Administration (EIA)](https://www.eia.gov/environment/emissions/state/) | Download 3 Excel files | CO2 emissions by state and year (1960–2024) | Once a year | Public (no key required) |
| 2 | [U.S. Bureau of Economic Analysis (BEA)](https://apps.bea.gov/api/data) | API | Real GDP by state and year (1997–2025) | Once a year | Key required |

**We downloaded the following files from the EIA**

-Total CO2: https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_total.xlsx

-CO2 by fuel: https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_source.xlsx

-CO2 by sector: https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_sector.xlsx

**From the BEA we request the following data:**

Table SAGDP9 (rGDP by state), Line Code 1 to get the all-industry totals. rGDP is adjusted to 2017 prices to account for inflation.  

**Integration Goal**

<<<<<<< HEAD
| Field | Type | Description |
| --- | --- | --- |
| `GeoFips` | string | State FIPS code (e.g. `56000` for Wyoming) |
| `GeoName` | string | State name |
| `TimePeriod` | string → int | Year |
| `DataValue` | string → float | Real GDP. Arrives as text with thousands separators, so it's converted to a number |
| `CL_UNIT`, `UNIT_MULT` | string | Unit: millions of chained 2017 dollars |
| `NoteRef` | string | Footnote reference |

### Source 3 detail: EIA monthly electricity generation

Pulled from EIA API v2 route `electricity/electric-power-operational-data`, which EIA describes as monthly and annual electric power operations by state, sector, and energy source.

| Facet / column | Description |
| --- | --- |
| `location` | State |
| `fueltypeid` | Energy source (coal, natural gas, nuclear, wind, solar, etc.) |
| `sectorid` | Generating sector (electric utility, independent power producer, etc.) |
| `period` | Month (`YYYY-MM`). Quarterly and annual frequencies are also available |
| `generation` | Net generation, in thousand MWh |

### Source 4 coverage notes

From an initial pull of the SEDS price series:

| Series | Years | States with data | Gaps |
| --- | --- | --- | --- |
| `CLEID` coal price, electric power sector | 1997–2024 | 47 of 51 | DC, ID, RI, VT never report (no coal-fired generation) |
| `ESRCD` residential electricity price | 1997–2024 | 51 of 51 | None |
| `ESTCD` electricity average price, all sectors | 1997–2024 | 51 of 51 | None |

Prices are in nominal dollars and are deflated before comparison across years (using a BEA price deflator, or by chaining to 2017 dollars to match BEA's real GDP).

### Attribution

Data from the U.S. Energy Information Administration and the U.S. Bureau of Economic Analysis. Neither agency endorses this project.

---

## Integration Goal

**What each source contributes**

- **EIA CO2 tables:** the environmental side. Emissions by state and year, broken down by fuel and by sector.
- **BEA real GDP:** the economic side. Inflation-adjusted output by state and year.
- **EIA monthly generation:** the mechanism. How each state's power mix (coal, gas, nuclear, wind, solar, …) shifted over time, plus a frequently updated source for scheduled collection.
- **EIA energy prices:** a candidate explanation. Whether price changes coincide with cleaner growth.

**What the combination reveals**

Only the joined data can show carbon intensity (CO2 ÷ real GDP) for every state and year. From that we get each state's decoupling category, its trend over time, and the fuels, sectors, and generation-mix changes behind it. Every `POST /transform` run compares our computed intensity against EIA's published "CO2 per million dollars" sheet to validate the join and the units (see step 7). On the October 2026 data, the median difference across all 1,428 state-years was 0.008%; the largest was 5.2% (Delaware 2023), likely from BEA revising recent GDP after EIA built its sheet.

**How the sources are combined**

- **Join key: state + year.** The EIA workbooks use two-letter state abbreviations and BEA uses state names (`GeoName`). A lookup table in `transform.py` maps BEA's names to the two-letter codes, so both sources share one `state` column.
- **Reshaping:** the EIA workbooks are reshaped from one-column-per-year to one row per state per year, and the `Contents` sheets and any non-state rows (e.g. U.S. total) are dropped.
- **Aggregation (planned):** monthly generation is summed to annual totals before joining.
- **Common window:** analyses combining emissions and GDP use **1997–2024**, where both sources overlap.
- **Units:** CO2 (million metric tons) ÷ real GDP (millions of chained 2017 dollars) gives metric tons of CO2 per dollar of real GDP. Because that number is very small, the `intensity` column is in **metric tons per million dollars** (the same scale as EIA's published sheet).
=======
Neither source has the emission and GDP side data. By combining them, we are able to calculate carbon intensity, as defined above, for every state. This allows us to easily see which states decoupled.
The two sources are joined on state and year, and due to the different time windows from the sources, the maximum window we can calculate carbon intensity for is 1997-2024. 
>>>>>>> origin/nahmedi286179-patch-3


**Setup Instructions**

**1. Download the code**
```
git clone https://github.com/liamtabrams/emission-impossible
cd emission-impossible
```
**2. Install Necessary Python Packages through a Virtual Envrionment**
```
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
**3. Get a Google Cloud Key**
From the Google Cloud console, go to IAM & Admin, Service Accounts, Keys and download a key file. 

**4. Get a BEA Key**
Visit https://apps.bea.gov/api/signup/
Register your name and email and they will send you your key. 

**5. Fill in your keys**
```
cp .env_template .env
```
Should fill in with the following:

GCP_Project_ID='emission-impossible-510123'

GCP_Bucket_Name='emission-impossible'

GOOGLE_APPLICATION_CREDENTIALS='Full File path from Step 3'

BEA_API_KEY='Key from Step 4' 

**6. Start the API**
```
cd api
fastapi run main.py
```
**7. Download and join the data**
From the page you just opened, click Try it Out, then execute for the following two buttons (in order)

'POST /ingest/eia' (for EIA data)

<<<<<<< HEAD
Leave this terminal running. Run the `curl` commands in the steps below from a second terminal.

### 6. Call the EIA and BEA ingestion endpoints
=======
'POST /ingest/bea' (for BEA data)
>>>>>>> origin/nahmedi286179-patch-3

'POST /transform' (cleans and combines data. Other two collectors must be run successfully before this one.)


**8. Run the Dashboard**
```
<<<<<<< HEAD

Or from Python:

```python
import requests

resp = requests.post("http://localhost:8000/ingest/eia")
print(resp.status_code, resp.json())
```

A successful call returns `200` with the month and the files written:

```json
{
  "month": "2026-09",
  "files_stored": [
    "raw/eia_co2/2026-09/CO2_total.xlsx",
    "raw/eia_co2/2026-09/CO2_source.xlsx",
    "raw/eia_co2/2026-09/CO2_sector.xlsx"
  ]
}
```

**ii. `POST /ingest/bea`** gets real GDP by state from the BEA API and saves it as JSON under a folder for the current month. It needs `BEA_API_KEY` in `.env`.

Run it the same way from the Swagger UI. A successful call returns `200`:

```json
{"month": "2026-10", "rows": 1740, "files_stored": ["raw/bea_gdp/downloaded_2026-10/real_gdp_by_state_all_years.json"]}
```

### 7. Run the transform

**`POST /transform`** takes the latest EIA and BEA files from the bucket, cleans them, joins them by state and year, adds carbon intensity, and saves the result as `processed/co2_gdp_by_state_year.csv`. It needs no API key or parameters, and each run overwrites the old file.

Run it after the ingestion endpoints, with the server from step 5 still running: in the Swagger UI, open `POST /transform` -> **Try it out** -> **Execute**. Or from a second terminal:

```bash
curl -X POST http://localhost:8000/transform
```

To print only the EIA comparison results:

```bash
curl -s -X POST http://localhost:8000/transform | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['validation'], indent=2))"
```

A successful call returns `200`. The response body appears below **Execute** in the Swagger UI, or in the second terminal with `curl`:

```json
{
  "rows": 1428,
  "states": 51,
  "years": [1997, 2024],
  "columns": ["state", "year", "co2", "gdp", "intensity", "co2_coal", "co2_natural_gas", "co2_petroleum", "co2_residential", "co2_commercial", "co2_industrial", "co2_transportation", "co2_electric_power"],
  "sources": [
    "raw/eia_co2/2026-10/CO2_total.xlsx",
    "raw/eia_co2/2026-10/CO2_source.xlsx",
    "raw/eia_co2/2026-10/CO2_sector.xlsx",
    "raw/bea_gdp/downloaded_2026-10/real_gdp_by_state_all_years.json"
  ],
  "file_stored": "processed/co2_gdp_by_state_year.csv",
  "checks": {"states": 51, "years": [1997, 2024], "rows_per_state": 28, "duplicates": 0, "missing_values": 0, "max_fuel_gap": 0.001, "max_sector_gap": 0.002},
  "validation": {"status": "passed", "rows_compared": 1428, "median_abs_pct_diff": 0.008, "max_abs_pct_diff": 5.172, "median_ratio": 1.0, "worst_rows": [{"state": "DE", "year": 2023, "ours": 140.9, "eia": 148.6, "pct_diff": -5.2}, {"state": "DE", "year": 2022, "ours": 149.1, "eia": 156.8, "pct_diff": -4.9}, {"state": "NE", "year": 2024, "ours": 281.6, "eia": 294.0, "pct_diff": -4.2}]}
}
```

(Values above are from the October 2026 data.)

The first terminal (the one running the server) prints one line for each EIA sheet (9 in total: the last one is shown), one for BEA, then the checks, the EIA comparison, and one when the CSV is saved, followed by status:

```
EIA Electric power: 55 raw rows cleaned to 51 states x 65 years = 3315 rows
BEA: 1740 raw rows cleaned to 51 states = 1479 rows
Checks: {'states': 51, 'years': [1997, 2024], 'rows_per_state': 28, 'duplicates': 0, 'missing_values': 0, ...}
EIA CO2 per million dollars: 55 raw rows cleaned to 51 states x 28 years = 1428 rows
EIA comparison: 1428 state-years, median difference 0.008% (limit 5.0%). Largest differences:
  DE 2023: ours 140.9, EIA 148.6 (-5.2%)
  DE 2022: ours 149.1, EIA 156.8 (-4.9%)
  NE 2024: ours 281.6, EIA 294.0 (-4.2%)
Saved 1428 rows to processed/co2_gdp_by_state_year.csv
INFO   127.0.0.1:58535 - "POST /transform HTTP/1.1" 200
```

If a check fails, the reason is printed there too, so it also shows in the Cloud Run logs.

**Checks.** The CSV is only saved if every check passes. Otherwise the call returns `500` with every problem listed, and the previous `processed/` file is left untouched. The table must have:

- exactly one row per state per year
- all 50 states + DC
- every year from the first to the last for every state, with no gaps
- no missing values and GDP above 0
- fuel columns and sector columns that each add up to `co2` within `SUM_TOLERANCE` (0.01 million tonnes; on the October 2026 data the largest gaps are 0.001 and 0.002, from EIA's 3-decimal rounding)

**EIA comparison.** EIA publishes its own carbon intensity on the "CO2 per million dollars" sheet of `CO2_total.xlsx`. The transform compares ours with it for every state-year both have and reports the median difference and the three largest differences. EIA computed theirs with an older vintage of BEA GDP, so small differences are expected. If the median difference is above 5% (`MAX_MEDIAN_PCT_DIFF`), the call fails, because that points to a unit or join mistake rather than a GDP revision. `median_ratio` near 1.0 means matching units, and about 1000 or 0.001 means a units mistake. If EIA drops or renames that sheet, the comparison is skipped and `validation.status` says `"skipped"` with the reason.

If a raw file is missing, it returns `404`: run the matching ingestion endpoint first.

### 8. Read the processed data

**`GET /data`** reads `processed/co2_gdp_by_state_year.csv` from the bucket and returns it over HTTP, so any client can use the processed data without GCS credentials. (The Streamlit dashboard currently reads the same CSV from the bucket directly.) It returns `404` until `POST /transform` has run once.

It returns the processed rows as a JSON list, one object per state per year with the columns from [Processed Data](#processed-data-output-of-the-transform). Optional filters: `state` (two-letter code, any case), `start_year`, `end_year`.

```bash
curl "http://localhost:8000/data?state=CA&start_year=2010&end_year=2024"
```

```python
import pandas as pd, requests
df = pd.DataFrame(requests.get(f"{API_SERVICE_URL}/data").json())
```

### 9. Verify the files in the bucket

In the GCP console, open **Cloud Storage -> Buckets -> emission-impossible**. The raw files are under **raw -> eia_co2** and **raw -> bea_gdp**, and the processed CSV is under **processed**.

### Running FastAPI in Docker

```bash
cd api && docker build -t emission-impossible-api .
cd .. && docker run -v absolute-path-to-GCP_service_account_key:/tmp/GCP_service_account_key.json --env-file .env -p 8000:8000 emission-impossible-api
```

The server will run at `http://localhost:8000`. Interactive docs (Swagger UI) are at **http://localhost:8000/docs**.

If you authenticate with a service account key, mount it into the container and set `GOOGLE_APPLICATION_CREDENTIALS` to the path inside the container `/tmp/`.

### Run the dashboard

From the repo root:

```bash
cd streamlit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
=======
cd Streamlit
>>>>>>> origin/nahmedi286179-patch-3
streamlit run streamlit_app.py
```
Open http://localhost:8000/docs in your browser



**If it worked, you should see a 'raw' folder and 'processed' folder in your Google Cloud console.**

**How to run the deployment script gcloud_command.sh**
```
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```
Run the script from the root directory 
```
bash gcloud_command.sh
```
Run api Deployment
```
bash gcloud_command.sh api
```

Deploy Schedulers
```
bash gcloud_command.sh api
```

## Repository Structure

```
emission-impossible/
├── api/
│   ├── collectors/
│   │   ├── __init__.py
<<<<<<< HEAD
│   │   ├── bea.py               # calls the BEA API for real GDP by state
│   │   └── eia.py               # downloads the EIA SEDS CO2 workbooks
│   ├── Dockerfile               # container for the FastAPI service
│   ├── main.py                  # FastAPI routes: POST /ingest/eia, /ingest/bea, /transform; GET /data
│   ├── requirements.txt
│   ├── storage.py               # read/write Google Cloud Storage
│   ├── transform.py             # cleaning, reshaping, the state-year join, checks, EIA comparison
│   └── user_definition.py       # configuration loaded from environment variables
=======
│   │   ├── bea.py
│   │   └── eia.py
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── storage.py
│   ├── transform.py
│   └── user_definition.py
>>>>>>> origin/nahmedi286179-patch-3
├── streamlit/
│   ├── Dockerfile
│   ├── load_data.py
│   ├── national_overview.py
│   ├── requirements.txt
│   ├── streamlit_app.py
│   └── user_definition.py
├── .env_template
├── .gitignore
├── gcloud_command.sh
└── README.md
```

---