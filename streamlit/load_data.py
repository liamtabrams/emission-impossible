import io

from google.oauth2 import service_account
from google.cloud import storage
import streamlit as st
import pandas as pd

from user_definition import *


def retrieve_data_from_gcs(service_account_key: str,
                           project_id: str,
                           bucket_name: str,
                           file_name: str
                           ) -> pd.DataFrame:
    """
    Download the processed csv file from the bucket and return it as a
    dataframe.
    """
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id,
                            credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    # the file is plain text, so read it as a string and let pandas parse it
    content = blob.download_as_text()
    return pd.read_csv(io.StringIO(content))


# caching so the file is downloaded once and not on every click.
# ttl is one day, so the app picks up the new file after the yearly run.
@st.cache_data(ttl=24 * 60 * 60)
def load_data():
    data = retrieve_data_from_gcs(service_account_key,
                                  project_id,
                                  bucket_name,
                                  file_name)
    data = data.sort_values(by=["state", "year"])
    return data


def find_group(percent_gdp: float, percent_co2: float) -> str:
    """
    Put a state into one of four groups based on how much its economy
    and its emissions changed (both in %).
    """
    if percent_gdp <= 0:
        return "Economy shrank"
    if percent_co2 < 0:
        return "Cut emissions outright"
    if percent_co2 < percent_gdp:
        return "Emissions grew, but slower than the economy"
    return "Emissions grew as fast as the economy"


def state_change(data: pd.DataFrame,
                 start_year: int,
                 end_year: int
                 ) -> pd.DataFrame:
    """
    Compare every state between start_year and end_year.
    returns one row per state with the % change in gdp, co2 and
    intensity (co2 per dollar), and the state's group
    """
    # one row per state for each year, so the two can be lined up by state
    start = data[data["year"] == start_year].set_index("state")
    end = data[data["year"] == end_year].set_index("state")

    change = pd.DataFrame()
    change["percent_gdp"] = (end["gdp"] / start["gdp"] - 1) * 100
    change["percent_co2"] = (end["co2"] / start["co2"] - 1) * 100
    change["percent_intensity"] = (end["intensity"] / start["intensity"] - 1) * 100

    groups = []
    for state in change.index:
        groups.append(find_group(change.loc[state, "percent_gdp"],
                                 change.loc[state, "percent_co2"]))
    change["group"] = groups
    return change.reset_index()


def us_change(data: pd.DataFrame, start_year: int, end_year: int) -> dict:
    """
    Add up all the states and return the % change for the whole country
    in gdp, co2 and co2 per dollar.
    """
    start = data[data["year"] == start_year]
    end = data[data["year"] == end_year]

    gdp_change = (end["gdp"].sum() / start["gdp"].sum() - 1) * 100
    co2_change = (end["co2"].sum() / start["co2"].sum() - 1) * 100

    # co2 per dollar for the whole country is total co2 / total gdp
    start_intensity = start["co2"].sum() / start["gdp"].sum()
    end_intensity = end["co2"].sum() / end["gdp"].sum()
    intensity_change = (end_intensity / start_intensity - 1) * 100

    return {"gdp": gdp_change,
            "co2": co2_change,
            "intensity": intensity_change}


def us_by_year(data: pd.DataFrame,
               start_year: int,
               end_year: int
               ) -> pd.DataFrame:
    """
    Add up all the states for every year between start_year and end_year,
    and rescale gdp, co2 and co2 per dollar so the start year is 100.
    """
    window = data[(data["year"] >= start_year) & (data["year"] <= end_year)]
    us = window.groupby("year")[["gdp", "co2"]].sum().reset_index()
    us["intensity"] = us["co2"] / us["gdp"]

    # divide by the first year's value so all three lines start at 100
    for column in ["gdp", "co2", "intensity"]:
        us[column + "_index"] = us[column] / us[column].iloc[0] * 100
    return us
