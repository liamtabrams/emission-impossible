import streamlit as st


overview_page = st.Page(
    "national_overview.py", title="National overview", icon=":material/map:")

# add the second page (one state at a time) to this list once it's ready
pg = st.navigation([overview_page])
st.set_page_config(page_title="Emission Impossible",
                   page_icon=":material/eco:",
                   layout="wide")
pg.run()
