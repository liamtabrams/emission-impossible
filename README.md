# Emission Impossible

Which U.S. states have grown their economies while cutting carbon emissions? This project collects state-level CO2 emissions, real GDP, power-generation, and energy-price data, stores it in Google Cloud Storage, and serves it through a FastAPI service and a Streamlit dashboard that shows where and how economic growth has "decoupled" from emissions.

- **Git repo:** https://github.com/liamtabrams/emission-impossible
- **GCP project:** `emission-impossible` (bucket `gs://emission-impossible`, region `us-west1`)
- **Course:** DSAI 692 Data Acquisition, University of San Francisco

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

Over the past few decades, most states' economies have grown. The open question is whether their energy-related CO2 emissions grew with them or fell. A state that grows its real GDP while its emissions stay flat or decline has **decoupled**. We measure this with **carbon intensity**: CO2 emitted per dollar of real (inflation-adjusted) GDP.

No single dataset answers this question. EIA reports emissions but not economic output. BEA reports output but not emissions. Neither alone explains *why* a state's intensity changed. By combining emissions, GDP, power-generation mix, and energy prices by state and year, we can:

1. Classify each state's decoupling status over a chosen time window.
2. Show which fuels (coal, natural gas, petroleum) and which sectors (residential, commercial, industrial, transportation, electric power) drove each state's change.
3. Relate decoupling to shifts in the electricity generation mix (e.g. coal giving way to gas and renewables) and to changes in energy prices.

This is useful to state energy and policy analysts, researchers, and anyone asking how much the U.S. has actually shifted toward cleaner growth. Results are descriptive associations, not causal estimates.

### Decoupling categories

| Category | Real GDP | CO2 emissions |
| --- | --- | --- |
| Absolute decoupling | ↑ | ↓ |
| Relative decoupling | ↑ | ↑, but more slowly than GDP |
| No decoupling | ↑ | ↑ as fast as or faster than GDP |
| Contraction | ↓ | — (treated separately) |

### Planned dashboard views

- **Decoupling map:** states colored by % change in carbon intensity between two selectable years (multi-year averages to smooth noise).
- **State profile:** pick a state and year to see the economy's makeup next to emissions by sector.
- **What fuels changed?** Change in emissions by fuel type (coal, natural gas, petroleum).

---

## Data Sources

| # | Source & Link | Method | What it contains | Update frequency | Access requirements | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [EIA State Energy Data System (SEDS) CO2 emissions tables](https://www.eia.gov/environment/emissions/state/) | File (.xlsx downloaded from URL) | Energy-related CO2 by state, 1960–2024, in three workbooks (details below) | Annual (current release June 26, 2026; next June 25, 2027) | None. Public, no key | Implemented (`POST /ingest/eia`) |
| 2 | [BEA Regional API](https://apps.bea.gov/api/data), table `SAGDP9`, `LineCode=1` | API | Real GDP by state and year, 1997–2025, in millions of chained 2017 dollars | Annual, revised yearly (quarterly state GDP also available as `SQGDP`) | Free key (`BEA_API_KEY`), [signup](https://apps.bea.gov/API/signup/). Limits: 100 requests/min, 100 MB/min, 30 errors/min | Implemented (`POST /ingest/bea`) |
| 3 | [EIA API v2, `electricity/electric-power-operational-data`](https://api.eia.gov/v2/electricity/electric-power-operational-data/data/) | API | Net electricity generation by state, fuel type, and sector (thousand MWh) | **Monthly** (posted about 2 months after the fact) | Free key (`EIA_API_KEY`), [signup](https://www.eia.gov/opendata/register.php). Max 5,000 rows per request | Planned (recurring source) |
| 4 | [EIA API v2, SEDS price series](https://www.eia.gov/opendata/) | API | Energy prices by state, 1997–2024: `CLEID` (coal price, electric power sector), `ESRCD` (residential electricity price), `ESTCD` (all-sector electricity price) | Annual | Same `EIA_API_KEY` | Planned |

### Source 1 detail: EIA SEDS CO2 workbooks

The collector downloads three workbooks from EIA and stores them in the bucket unchanged. All emissions values are in **million metric tons of CO2**.

| Workbook (bucket name) | Worksheets |
| --- | --- |
| `CO2_total.xlsx` | Total CO2, Per capita, CO2 per billion Btu (intensity of energy supply), CO2 per million dollars (intensity of economy, i.e. CO2 ÷ real GDP) |
| `CO2_source.xlsx` | Coal, Natural gas, Petroleum, Total |
| `CO2_sector.xlsx` | Residential, Commercial, Industrial, Transportation, Electric power, Total |

### Source 2 detail: BEA real GDP by state

The collector calls the BEA Regional dataset once per run with these parameters:

| Parameter | Value | Meaning |
| --- | --- | --- |
| `method` | `GetData` | Data request (vs. metadata discovery) |
| `datasetname` | `Regional` | The only BEA dataset with state-level GDP |
| `TableName` | `SAGDP9` | Real GDP by state, chained dollars, by industry |
| `LineCode` | `1` | All-industry total |
| `GeoFips` | `STATE` | Every state |
| `Year` | `ALL` | Full available history |

Each row returned is one state-year:

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

Only the joined data can show carbon intensity (CO2 ÷ real GDP) for every state and year. From that we get each state's decoupling category, its trend over time, and the fuels, sectors, and generation-mix changes behind it. Comparing our computed intensity against EIA's published "CO2 per million dollars" sheet validates the join and the units.

**How the sources are combined**

- **Join key: state + year.** BEA identifies states by FIPS code (`GeoFips`) and name (`GeoName`). The EIA workbooks and API use two-letter state abbreviations. A small lookup table maps all of them to one identifier.
- **Reshaping:** the EIA workbooks are reshaped from one-column-per-year to one row per state per year, and the `Contents` sheets and any non-state rows (e.g. U.S. total) are dropped.
- **Aggregation:** monthly generation is summed to annual totals before joining.
- **Common window:** analyses combining emissions and GDP use **1997–2024**, where both sources overlap.
- **Units:** CO2 (million metric tons) ÷ real GDP (millions of chained 2017 dollars) gives metric tons of CO2 per dollar of real GDP. Because that number is very small, we report **metric tons per million dollars** (the same scale as EIA's published sheet) or kilograms per dollar.


## Setup Instructions (Locally)

### Prerequisites

- Python 3.11+
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- Membership in the `emission-impossible` GCP project with write access to the `emission-impossible` bucket
- Free API keys for BEA and EIA (only needed for the API collectors; the EIA CO2 file ingestion needs no key)

### 1. Clone the repository

```bash
git clone https://github.com/liamtabrams/emission-impossible
cd emission-impossible
```

### 2. Create a virtual environment and install dependencies

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Authenticate with Google Cloud

Either sign in with your own account:

```bash
gcloud auth application-default login
gcloud config set project emission-impossible
```

or point to a service account key file using the variable in step 4.

### 4. Configure environment variables

From the repo root, copy the template and fill in your own values. **Never commit `.env`**, which is listed in `.gitignore`.

```bash
cp .env_template .env
```

| Variable | Description | Example |
| --- | --- | --- |
| `GCP_PROJECT_ID` | GCP project ID | `emission-impossible` |
| `GCS_BUCKET_NAME` | Bucket where raw and processed data is stored | `emission-impossible` |
| `GOOGLE_APPLICATION_CREDENTIALS` | *(Optional)* absolute path to a service account JSON key, if not using `gcloud auth` | `/Users/you/keys/emission-impossible.json` |
| `BEA_API_KEY` | BEA Regional API key ([signup](https://apps.bea.gov/API/signup/)) | 36-character UserID |
| `EIA_API_KEY` | EIA Open Data API key ([signup](https://www.eia.gov/opendata/register.php)) | 40-character key |
| `API_SERVICE_URL` | Where the Streamlit app reaches the API | `http://localhost:8000` |

> **TODO:** make these names match exactly what `api/user_definition.py` reads, and keep `.env_template` in sync with this table.

### 5. Start the API server

```bash
cd api
fastapi run main.py
```

The server runs at `http://localhost:8000`. Interactive docs (Swagger UI) are at **http://localhost:8000/docs**.

### 6. Call the ingestion endpoint

**i. `POST /ingest/eia`** downloads the three EIA CO2 workbooks and uploads them to the bucket under a folder for the current month. It takes no parameters.

From the Swagger UI, open `POST /ingest/eia` → **Try it out** → **Execute**. Or from the terminal:

```bash
curl -X POST http://localhost:8000/ingest/eia
```

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

**ii. `POST /ingest/bea`** gets real GDP by state from the BEA API (table `SAGDP9`, all years) and saves it as JSON under a folder for the current month. It needs `BEA_API_KEY` in `.env`, and you call it the same way as above:

```bash
curl -X POST http://localhost:8000/ingest/bea
```

A successful call returns `200`:

```json
{"month": "2026-10", "rows": 1740, "files_stored": ["raw/bea_gdp/downloaded_2026-10/real_gdp_by_state_all_years.json"]}
```

### 7. Verify the files in the bucket

```bash
gcloud storage ls gs://emission-impossible/raw/eia_co2/
gcloud storage ls gs://emission-impossible/raw/bea_gdp/
```

or open **Cloud Storage → Buckets → emission-impossible → raw → eia_co2** 
(or **bea_gdp**) in the GCP console.

### Optional: run the API in Docker

```bash
docker build -t emission-impossible-api ./api
docker run --env-file .env -p 8000:8000 emission-impossible-api
```

If you authenticate with a service account key, mount it into the container and set `GOOGLE_APPLICATION_CREDENTIALS` to the path inside the container.

---

## Storage Layout (GCS)

Each ingestion run writes a dated snapshot, so earlier pulls are kept and EIA's yearly revisions can be compared.

```
gs://emission-impossible/
├── raw/
│   ├── eia_co2/YYYY-MM/              # CO2_total.xlsx, CO2_source.xlsx, CO2_sector.xlsx
│   ├── bea_gdp/downloaded_YYYY-MM/   # real_gdp_by_state_all_years.json     
│   ├── eia_generation/YYYY-MM/       # planned
│   └── eia_prices/YYYY-MM/           # planned
└── processed/                        # planned: cleaned, merged state-year tables
```

---

## Repository Structure

```
emission-impossible/
├── api/
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── bea.py               # calls the BEA API for real GDP by state 
│   │   └── eia.py               # downloads the EIA SEDS CO2 workbooks
│   ├── Dockerfile               # container for the FastAPI service
│   ├── main.py                  # FastAPI, Routes (POST /ingest/eia, POST /ingest/bea)
│   ├── requirements.txt
│   ├── storage.py               # read/write Google Cloud Storage
│   ├── transform.py             # cleaning, reshaping, and the state-year join
│   └── user_definition.py       # configuration loaded from environment variables
├── streamlit/
│   ├── Dockerfile               # container for the dashboard
│   ├── requirements.txt
│   └── streamlit_app.py         # dashboard (Phase 3)
├── .env_template                # documented list of required environment variables
├── .gitignore
├── gcloud_command.sh            # gcloud commands for build and Cloud Run deployment
└── README.md
```

---