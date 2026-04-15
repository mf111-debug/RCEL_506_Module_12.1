import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium

st.set_page_config(page_title="Ecobici Mexico City App", layout="wide")

# -----------------------------------
# Load data from GBFS safely
# -----------------------------------
gbfs_url = "https://gbfs.mex.lyftbikes.com/gbfs/gbfs.json"

website_data = requests.get(gbfs_url).json()

feeds = website_data["data"]["en"]["feeds"]

station_info_url = next(
    feed["url"] for feed in feeds if feed["name"] == "station_information"
)
station_status_url = next(
    feed["url"] for feed in feeds if feed["name"] == "station_status"
)

# Station information
data1 = requests.get(station_info_url).json()
df1 = pd.DataFrame(data1["data"]["stations"])

# Keep only columns that actually exist
needed_info_cols = ["station_id", "lat", "lon", "capacity"]
missing_info_cols = [col for col in needed_info_cols if col not in df1.columns]

if missing_info_cols:
    st.error(f"Missing columns in station information feed: {missing_info_cols}")
    st.stop()

df1 = df1[needed_info_cols]

# Station status
data2 = requests.get(station_status_url).json()
df2 = pd.DataFrame(data2["data"]["stations"])

needed_status_cols = [
    "station_id",
    "num_bikes_available",
    "num_bikes_disabled",
    "num_docks_available",
    "num_docks_disabled",
]
missing_status_cols = [col for col in needed_status_cols if col not in df2.columns]

if missing_status_cols:
    st.error(f"Missing columns in station status feed: {missing_status_cols}")
    st.stop()

df2 = df2[needed_status_cols]

# Merge
df = pd.merge(df1, df2, on="station_id")
df["station_id"] = df["station_id"].astype(str)

# -----------------------------------
# Map function
# -----------------------------------
def bike_share_system_cdmx_plot(station_number):
    m = folium.Map(
        [df["lat"].mean(), df["lon"].mean()],
        zoom_start=12
    )

    for n in range(len(df)):
        folium.Marker(
            location=[df["lat"].iloc[n], df["lon"].iloc[n]],
            tooltip=df["station_id"].iloc[n],
            icon=folium.Icon(color="red"),
        ).add_to(m)

    station_to_highlight = df[df["station_id"] == str(station_number)]

    if not station_to_highlight.empty:
        station_lat = station_to_highlight["lat"].iloc[0]
        station_lon = station_to_highlight["lon"].iloc[0]
        highlight_id = station_to_highlight["station_id"].iloc[0]

        folium.Marker(
            location=[station_lat, station_lon],
            tooltip=highlight_id,
            icon=folium.Icon(icon="cloud"),
        ).add_to(m)
    else:
        st.error(f"Station with ID {station_number} not found.")

    return m

# -----------------------------------
# First row
# -----------------------------------
st.title("Ecobici Mexico City App")
st.caption("Created by Mohammed")

# -----------------------------------
# Second row
# -----------------------------------
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Select Station")
    station_options = sorted(df["station_id"].unique())
    selected_station = st.selectbox("Choose a station ID", station_options)

with col2:
    st.subheader("Map")
    my_map = bike_share_system_cdmx_plot(selected_station)
    st_folium(my_map, width=900, height=600)
