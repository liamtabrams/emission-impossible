"""Read-only checks against the REAL bucket and the real EIA/BEA files in it.

Skipped unless you opt in, because it needs GCP credentials in .env and the
collectors to have run at least once:

    RUN_LIVE_TESTS=1 pytest tests/test_live_bucket.py -v -s

It downloads the newest raw files, runs the full clean -> join -> check -> EIA
comparison in memory, and prints the results. It never writes to the bucket.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to run against the real bucket",
)


@pytest.fixture(scope="module")
def live_result():
    import transform

    eia_files, bea_bytes, sources = transform.download_newest_raw_files()
    table, checks, validation = transform.build_checked_table(eia_files, bea_bytes)
    print("\nsources   :", sources)
    print("checks    :", checks)
    print("validation:", validation)
    return table, checks, validation


def test_real_data_passes_every_check(live_result):
    table, checks, _ = live_result
    assert checks["states"] == 51
    assert checks["missing_values"] == 0
    assert checks["duplicates"] == 0
    assert checks["years"][0] == 1997  # BEA's state GDP starts in 1997
    assert len(table) == 51 * (checks["years"][1] - checks["years"][0] + 1)


def test_real_intensity_matches_eia(live_result):
    _, _, validation = live_result
    assert validation["status"] == "passed", validation
    assert 0.95 < validation["median_ratio"] < 1.05


def test_real_numbers_are_plausible(live_result):
    table, _, _ = live_result
    latest = table[table["year"] == table["year"].max()].set_index("state")
    # California has the biggest economy; Texas emits the most CO2
    assert latest["gdp"].idxmax() == "CA"
    assert latest["co2"].idxmax() == "TX"
    # intensity is tonnes per $1M: hundreds for most states, not 0.0003 or 300,000
    assert 20 < latest["intensity"].median() < 2000


def test_processed_file_in_bucket_is_readable():
    import transform

    table = transform.load_processed_table()
    assert len(table) > 0
    assert {"state", "year", "co2", "gdp", "intensity"} <= set(table.columns)
