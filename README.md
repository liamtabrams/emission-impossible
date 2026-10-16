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

Neither source has the emission and GDP side data. By combining them, we are able to calculate carbon intensity, as defined above, for every state. This allows us to easily see which states decoupled.
The two sources are joined on state and year, and due to the different time windows from the sources, the maximum window we can calculate carbon intensity for is 1997-2024. 


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
Open http://localhost:8000/docs in your browser

**7. Download and join the data**
From the page you just opened, click Try it Out, then execute for the following two buttons (in order)
'POST /ingest/eia' (for EIA data)
'POST /ingest/bea' (for BEA data)
'POST /transform' (cleans and combines data. Other two collectors must be run successfully before this one.)

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
│   │   ├── bea.py
│   │   └── eia.py
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── storage.py
│   ├── transform.py
│   └── user_definition.py
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
