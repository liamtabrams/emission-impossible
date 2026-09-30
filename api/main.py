# FastAPI routes
from fastapi import FastAPI
from collectors import eia

app = FastAPI()

@app.post("/ingest/eia")
def ingest_eia():
    return eia.collect()
