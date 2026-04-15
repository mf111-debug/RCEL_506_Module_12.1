import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium

st.set_page_config(page_title="Ecobici Mexico City App", layout="wide")

# -----------------------------------
# Load data from GBFS (LIVE DATA)
# -----------------------------------
url = 'https://gbfs.mex.lyftbikes.com/gbfs/gbfs.json'
website_data = requests.get(url).json()

urls = website_data['data']['en']['feeds']
url_data = [u['url'] for u in urls if 'station' in u['url']]

# Station info
data1 = requests.get(url_data[0]).json()
df1 = pd.DataFrame(data1['data']['stations'])
df1 = df1[['station_id', 'lat', 'lon', 'capacity']]

# Station status
data2 = requests.get(url_data[1]).json()
df2 = pd.DataFrame(data2['data']['stations'])
df2 = df2[['station_id',
           'num_bikes_available',
           'num_bikes_disabled',
           'num_docks_available',
           'num_docks_disabled']]

# Merge both
df = pd.merge(df1, df2, on='station_id')
df['station_id'] = df['station_id'].astype(str)

# -----------------------------------
# Map function
# -----------------------------------
def bike_share_system_cdmx_plot(station_number):
    m = folium.Map([df['lat'].mean(), df['lon'].mean()],
                   zoom_start=12)

    for n in range(len(df)):
        folium.Marker(
            location=[df['lat'].iloc[n], df['lon'].iloc[n]],
            tooltip=df['station_id'].iloc[n],
            icon=folium.Icon(color="red"),
        ).add_to(m)

    station_to_highlight = df[df['station_id'] == str(station_number)]

    try:
        if not station_to_highlight.empty:
            station_lat = station_to_highlight['lat'].iloc[0]
            station_lon = station_to_highlight['lon'].iloc[0]
            highlight_id = station_to_highlight['station_id'].iloc[0]

            folium.Marker(
                location=[station_lat, station_lon],
                tooltip=highlight_id,
                icon=folium.Icon(icon="cloud"),
            ).add_to(m)
        else:
            raise ValueError(f"Station with ID {station_number} not found.")
    except ValueError as e:
        st.error(e)
    except Exception as e:
        st.error(f"Unexpected error: {e}")

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
    station_options = sorted(df['station_id'].unique())
    selected_station = st.selectbox("Choose a station ID", station_options)

with col2:
    st.subheader("Map")
    my_map = bike_share_system_cdmx_plot(selected_station)
    st_folium(my_map, width=900, height=600)
