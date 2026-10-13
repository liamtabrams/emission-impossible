"""The endpoints end to end, with a fake bucket in place of GCS."""

import io

import pandas as pd
import pytest

import transform
from conftest import STATES, bucket_paths, make_frames, render


@pytest.fixture
def stocked_bucket(fake_bucket, raw_files):
    """A bucket holding this month's raw files plus an older, junk snapshot."""
    eia_files, bea_bytes = raw_files
    fake_bucket.update(bucket_paths({n: b"old" for n in eia_files}, b"old", "2026-09"))
    fake_bucket.update(bucket_paths(eia_files, bea_bytes))
    return fake_bucket


def test_transform_saves_processed_csv(client, stocked_bucket):
    response = client.post("/transform")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["rows"] == 1428
    assert body["states"] == 51
    assert body["years"] == [1997, 2024]
    assert body["file_stored"] == transform.PROCESSED_FILE
    # it used the newest snapshot, not the 2026-09 junk
    assert all("2026-10" in source for source in body["sources"])
    assert body["checks"]["missing_values"] == 0
    assert body["validation"]["status"] == "passed"

    saved = pd.read_csv(io.StringIO(stocked_bucket[transform.PROCESSED_FILE]))
    assert saved.shape == (1428, 13)
    assert list(saved.columns) == body["columns"]
    assert not saved.isna().any().any()


def test_transform_without_raw_files_is_a_404(client, fake_bucket):
    response = client.post("/transform")
    assert response.status_code == 404
    assert "Run the collector first" in response.json()["detail"]


def test_transform_does_not_save_a_table_that_fails_checks(client, fake_bucket):
    frames = make_frames()
    frames["gdp"] = frames["gdp"].drop(index="WY")
    fake_bucket.update(bucket_paths(*render(frames)))

    response = client.post("/transform")
    assert response.status_code == 500
    assert "missing states: WY" in response.json()["detail"]
    assert transform.PROCESSED_FILE not in fake_bucket


def test_data_before_transform_is_a_404(client, fake_bucket):
    response = client.get("/data")
    assert response.status_code == 404
    assert "Run POST /transform first" in response.json()["detail"]


def test_data_returns_every_row(client, stocked_bucket):
    client.post("/transform")
    rows = client.get("/data").json()
    assert len(rows) == 1428
    assert set(rows[0]) == {
        "state", "year", "co2", "gdp", "intensity",
        "co2_coal", "co2_natural_gas", "co2_petroleum",
        "co2_residential", "co2_commercial", "co2_industrial",
        "co2_transportation", "co2_electric_power",
    }
    # loads straight into a DataFrame, which is what the dashboard will do
    assert sorted(pd.DataFrame(rows)["state"].unique()) == STATES


def test_data_filters_by_state_and_years(client, stocked_bucket):
    client.post("/transform")
    rows = client.get("/data", params={"state": "ca", "start_year": 2000, "end_year": 2009}).json()
    assert len(rows) == 10
    assert {row["state"] for row in rows} == {"CA"}
    assert [row["year"] for row in rows] == list(range(2000, 2010))


def test_data_unknown_state_is_a_404(client, stocked_bucket):
    client.post("/transform")
    assert client.get("/data", params={"state": "ZZ"}).status_code == 404
