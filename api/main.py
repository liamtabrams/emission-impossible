# FastAPI routes
import logging

from collectors import bea, eia
from fastapi import FastAPI

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
logging.getLogger("collectors").addHandler(handler)
logging.getLogger("collectors").setLevel(logging.INFO)

app = FastAPI()


@app.post("/ingest/eia")
def ingest_eia():
    return eia.collect()


@app.post("/ingest/bea")
def ingest_bea():
    return bea.collect()
