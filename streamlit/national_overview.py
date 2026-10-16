import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from load_data import load_data, state_change, us_by_year, us_change

# AI use: the streamlit layout and plotly charts were written with help
# from Claude - Opus 5.5. for sections where AI was used is commented
# with '#AI assisted:" and the prompt i used.

# colors for the four groups in the scatter plot
group_colors = {
    "Cut emissions outright": "#2E7D32",
    "Emissions grew, but slower than the economy": "#C9A227",
    "Emissions grew as fast as the economy": "#C62828",
    "Economy shrank": "#616161",
}

data = load_data()
years = sorted(data["year"].unique().tolist())

st.title("Emission Impossible: US economic growth and carbon emissions")
st.caption("Energy related CO2 emissions and real (inflation-adjusted) GDP "
           "for the 50 states and DC.")

#AI assisted:  'Using streamlit, add start and end year dropdowns where end
# year list only shows years after the start year and 3 KPI style tiles
# to show % change in GPD, CO2 and carbon intensity'.

# year pickers. the end year list only shows years after the start year.
col1, col2 = st.columns(2)
with col1:
    start_year = st.selectbox("Start year", years[:-1], index=0)
with col2:
    end_years = [year for year in years if year > start_year]
    end_year = st.selectbox("End year", end_years, index=len(end_years) - 1)

# whole country: three numbers
us = us_change(data, start_year, end_year)
tile1, tile2, tile3 = st.columns(3)
tile1.metric("GDP", f"{us['gdp']:+.1f}%",
             help="Change in GDP, all states added up", border=True)
tile2.metric("CO2 emissions", f"{us['co2']:+.1f}%",
             help="Change in energy related CO2, all states added up",
             border=True)
tile3.metric("Carbon intensity", f"{us['intensity']:+.1f}%",
             help="Change in CO2 per dollar of GDP", border=True)

change = state_change(data, start_year, end_year)

# chart 1: map of % change by state

# AI assisted: 'Create US state map using plotly that shows
# the % change in CO2 or carbon intensity between the two years,
# with a button to switch between them. Blue for decrease, red for
# increase.'

st.subheader(f"Change by state, {start_year} -> {end_year}")
map_choice = st.radio("Show", ["CO2 emissions", "Carbon intensity"],
                      horizontal=True, label_visibility="collapsed")
if map_choice == "CO2 emissions":
    map_column = "percent_co2"
else:
    map_column = "percent_intensity"
st.caption("Blue = decreased, red = increased.")

# same limit on both sides so 0 is always the middle gray color
limit = change[map_column].abs().max()
map_fig = px.choropleth(change,
                        locations="state",
                        locationmode="USA-states",
                        scope="usa",
                        color=map_column,
                        color_continuous_scale=["#3987e5", "#dddddd",
                                                "#e66767"],
                        range_color=(-limit, limit),
                        hover_name="state",
                        hover_data={"state": False, map_column: ":+.1f"},
                        labels={map_column: "% change"})
map_fig.update_layout(geo_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=0, r=0, t=10, b=0),
                      height=520)
st.plotly_chart(map_fig)

# one line under the map with the counts, so it stays true for any years
cleaner = (change["percent_intensity"] < 0).sum()
went_up = (change["percent_co2"] > 0).sum()
st.caption(f"{cleaner} of {len(change)} states lowered their carbon intensity. "
           f"{went_up} of {len(change)} increased their total CO2 emissions.")

# chart 2: national trend, all three numbers start at 100

# AI assisted: 'Create a line chart of US total GDP, CO2 and
# carbon intensity indexed to start year = 100, with a dashed line
# and whole years on the x axis.'

st.subheader(f"National trend, {start_year} -> {end_year}")
st.caption(f"All states combined, indexed to {start_year} = 100, so GDP and "
           f"CO2 share one axis. Carbon intensity is CO2 divided by GDP.")

us_years = us_by_year(data, start_year, end_year)
line_fig = go.Figure()
line_fig.add_hline(y=100, line=dict(color="#888888", dash="dash", width=1))
line_fig.add_trace(go.Scatter(x=us_years["year"], y=us_years["gdp_index"],
                              name="GDP",
                              line=dict(color="#c98500", width=2.5)))
line_fig.add_trace(go.Scatter(x=us_years["year"], y=us_years["co2_index"],
                              name="CO2 emissions",
                              line=dict(color="#e66767", width=2.5)))
line_fig.add_trace(go.Scatter(x=us_years["year"],
                              y=us_years["intensity_index"],
                              name="Carbon intensity",
                              line=dict(color="#898781", width=2.5,
                                        dash="dot")))
# whole years on the x axis: every year for short windows, every 5 otherwise
if end_year - start_year <= 12:
    year_step = 1
else:
    year_step = 5
line_fig.update_layout(xaxis=dict(tickformat="d", dtick=year_step),
                       yaxis_title=f"Index ({start_year} = 100)",
                       legend=dict(orientation="h", y=1.1, x=0),
                       margin=dict(l=0, r=0, t=30, b=0),
                       height=420)
st.plotly_chart(line_fig)


# chart 3: % change in economy vs % change in emissions, by group

# AI assisted: 'create a scatter plot of % change in GDP vs %
# change in CO2 for each state, color by group, and a dashed line
# where both changed equally'

st.subheader(f"Economic growth vs emissions change, {start_year} -> {end_year}")
st.caption("Each point is a state. Points below the dashed line grew their "
           "emissions more slowly than their economy.")

scatter_fig = go.Figure()
for group, color in group_colors.items():
    rows = change[change["group"] == group]
    if len(rows) == 0:
        continue
    scatter_fig.add_trace(go.Scatter(
        x=rows["percent_gdp"], y=rows["percent_co2"], mode="markers", name=group,
        text=rows["state"], marker=dict(color=color, size=9),
        hovertemplate="<b>%{text}</b><br>GDP %{x:+.1f}%"
                      "<br>CO2 %{y:+.1f}%<extra></extra>"))


# dashed line where emissions grew exactly as fast as the economy
low = min(change["percent_gdp"].min(), change["percent_co2"].min())
high = max(change["percent_gdp"].max(), change["percent_co2"].max())
scatter_fig.add_shape(type="line", x0=low, y0=low, x1=high, y1=high,
                      line=dict(dash="dash", color="gray"))
scatter_fig.update_layout(xaxis_title="% change in GDP",
                          yaxis_title="% change in CO2 emissions",
                          legend=dict(title="Group"),
                          margin=dict(l=0, r=0, t=10, b=0),
                          height=480)
st.plotly_chart(scatter_fig)

counts = change["group"].value_counts()
cut = counts.get("Cut emissions outright", 0)
slowed = counts.get("Emissions grew, but slower than the economy", 0)
as_fast = counts.get("Emissions grew as fast as the economy", 0)
summary = (f"{cut} states cut emissions outright and {slowed} grew emissions "
           f"more slowly than their economy")
if as_fast > 0:
    summary += f". {as_fast} grew emissions as fast as their economy"
st.caption(summary + ".")
