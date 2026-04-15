import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(page_title="Ecobici Mexico City App", layout="wide")

# -------------------------------------------------
# Load live GBFS data
# -------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    gbfs_url = "https://gbfs.mex.lyftbikes.com/gbfs/gbfs.json"
    website_data = requests.get(gbfs_url).json()
    feeds = website_data["data"]["en"]["feeds"]

    station_info_url = next(feed["url"] for feed in feeds if feed["name"] == "station_information")
    station_status_url = next(feed["url"] for feed in feeds if feed["name"] == "station_status")

    data1 = requests.get(station_info_url).json()
    df1 = pd.DataFrame(data1["data"]["stations"])

    data2 = requests.get(station_status_url).json()
    df2 = pd.DataFrame(data2["data"]["stations"])

    df1 = df1[["station_id", "lat", "lon", "capacity", "name"]]
    df2 = df2[
        [
            "station_id",
            "num_bikes_available",
            "num_bikes_disabled",
            "num_docks_available",
            "num_docks_disabled",
            "is_installed",
            "is_renting",
            "is_returning",
            "last_reported",
        ]
    ]

    df = pd.merge(df1, df2, on="station_id")
    df["station_id"] = df["station_id"].astype(str)

    df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce").fillna(0)
    df["num_bikes_available"] = pd.to_numeric(df["num_bikes_available"], errors="coerce").fillna(0)
    df["num_docks_available"] = pd.to_numeric(df["num_docks_available"], errors="coerce").fillna(0)
    df["num_bikes_disabled"] = pd.to_numeric(df["num_bikes_disabled"], errors="coerce").fillna(0)
    df["num_docks_disabled"] = pd.to_numeric(df["num_docks_disabled"], errors="coerce").fillna(0)

    df["bike_ratio"] = df["num_bikes_available"] / df["capacity"].replace(0, pd.NA)
    df["dock_ratio"] = df["num_docks_available"] / df["capacity"].replace(0, pd.NA)

    return df

df = load_data()

# -------------------------------------------------
# Sidebar filters
# -------------------------------------------------
st.sidebar.header("Filters")

mode = st.sidebar.selectbox(
    "Select Mode",
    ["Find Bikes", "Find Docks", "Find High Capacity"]
)

min_bikes = st.sidebar.slider(
    "Minimum Bikes Available",
    min_value=int(df["num_bikes_available"].min()),
    max_value=int(df["num_bikes_available"].max()),
    value=0
)

min_docks = st.sidebar.slider(
    "Minimum Docks Available",
    min_value=int(df["num_docks_available"].min()),
    max_value=int(df["num_docks_available"].max()),
    value=0
)

min_capacity = st.sidebar.slider(
    "Minimum Capacity",
    min_value=int(df["capacity"].min()),
    max_value=int(df["capacity"].max()),
    value=0
)

show_cluster = st.sidebar.checkbox("Use Marker Clustering", value=True)

if st.sidebar.button("Reset Filters"):
    st.rerun()

# -------------------------------------------------
# Filter data
# -------------------------------------------------
filtered_df = df[
    (df["num_bikes_available"] >= min_bikes) &
    (df["num_docks_available"] >= min_docks) &
    (df["capacity"] >= min_capacity)
].copy()

selector_labels = (
    filtered_df["station_id"].astype(str)
    + " | "
    + filtered_df["name"].astype(str)
    + " | Bikes: "
    + filtered_df["num_bikes_available"].astype(int).astype(str)
    + " | Docks: "
    + filtered_df["num_docks_available"].astype(int).astype(str)
)

label_to_station = dict(zip(selector_labels, filtered_df["station_id"]))

# -------------------------------------------------
# Marker color logic
# -------------------------------------------------
def get_marker_color(row, mode_choice):
    if mode_choice == "Find Bikes":
        value = row["num_bikes_available"]
        if value >= 10:
            return "green"
        elif value >= 5:
            return "orange"
        return "red"

    if mode_choice == "Find Docks":
        value = row["num_docks_available"]
        if value >= 10:
            return "green"
        elif value >= 5:
            return "orange"
        return "red"

    value = row["capacity"]
    if value >= 40:
        return "green"
    elif value >= 20:
        return "orange"
    return "red"

# -------------------------------------------------
# Map function
# -------------------------------------------------
def bike_share_system_cdmx_plot(dataframe, station_number=None, mode_choice="Find Bikes", cluster=True):
    if dataframe.empty:
        return folium.Map(location=[19.4326, -99.1332], zoom_start=12)

    m = folium.Map(
        location=[dataframe["lat"].mean(), dataframe["lon"].mean()],
        zoom_start=12
    )

    marker_layer = MarkerCluster().add_to(m) if cluster else m

    for _, row in dataframe.iterrows():
        popup_text = f"""
        <b>Station ID:</b> {row['station_id']}<br>
        <b>Name:</b> {row['name']}<br>
        <b>Bikes Available:</b> {int(row['num_bikes_available'])}<br>
        <b>Docks Available:</b> {int(row['num_docks_available'])}<br>
        <b>Disabled Bikes:</b> {int(row['num_bikes_disabled'])}<br>
        <b>Disabled Docks:</b> {int(row['num_docks_disabled'])}<br>
        <b>Capacity:</b> {int(row['capacity'])}
        """

        folium.Marker(
            location=[row["lat"], row["lon"]],
            tooltip=f"{row['station_id']} | {row['name']}",
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=get_marker_color(row, mode_choice)),
        ).add_to(marker_layer)

    if station_number is not None:
        station_to_highlight = dataframe[dataframe["station_id"] == str(station_number)]

        if not station_to_highlight.empty:
            row = station_to_highlight.iloc[0]
            popup_text = f"""
            <b>Highlighted Station</b><br>
            <b>Station ID:</b> {row['station_id']}<br>
            <b>Name:</b> {row['name']}<br>
            <b>Bikes Available:</b> {int(row['num_bikes_available'])}<br>
            <b>Docks Available:</b> {int(row['num_docks_available'])}<br>
            <b>Capacity:</b> {int(row['capacity'])}
            """

            folium.Marker(
                location=[row["lat"], row["lon"]],
                tooltip=f"Selected: {row['station_id']}",
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color="blue", icon="cloud"),
            ).add_to(m)

    legend_html = """
    <div style="
        position: fixed; 
        bottom: 50px; left: 50px; width: 170px; height: 110px; 
        background-color: white; z-index:9999; font-size:14px;
        border:2px solid grey; padding: 10px;
    ">
    <b>Marker Legend</b><br>
    <i style="background:green; width:10px; height:10px; display:inline-block;"></i> High<br>
    <i style="background:orange; width:10px; height:10px; display:inline-block;"></i> Medium<br>
    <i style="background:red; width:10px; height:10px; display:inline-block;"></i> Low<br>
    <i style="background:blue; width:10px; height:10px; display:inline-block;"></i> Selected
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

# -------------------------------------------------
# Header
# -------------------------------------------------
st.title("Ecobici Mexico City App")
st.caption("Created by Mohammed")

# -------------------------------------------------
# KPI metrics
# -------------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Total Stations", len(df))

with kpi2:
    st.metric("Filtered Stations", len(filtered_df))

with kpi3:
    st.metric("Total Bikes Available", int(filtered_df["num_bikes_available"].sum()) if not filtered_df.empty else 0)

with kpi4:
    st.metric("Total Docks Available", int(filtered_df["num_docks_available"].sum()) if not filtered_df.empty else 0)

# -------------------------------------------------
# Main layout
# -------------------------------------------------
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Station Selector")

    if filtered_df.empty:
        st.warning("No stations match your filters.")
        selected_station = None
    else:
        selected_label = st.selectbox("Choose a station", selector_labels.tolist())
        selected_station = label_to_station[selected_label]

    st.subheader("Summary")
    st.write(f"Mode: **{mode}**")
    st.write(f"Stations shown: **{len(filtered_df)}**")

    if not filtered_df.empty:
        st.write("### Top 10 Stations by Bikes")
        st.dataframe(
            filtered_df[["station_id", "name", "num_bikes_available"]]
            .sort_values("num_bikes_available", ascending=False)
            .head(10),
            use_container_width=True
        )

        st.write("### Top 10 Stations by Docks")
        st.dataframe(
            filtered_df[["station_id", "name", "num_docks_available"]]
            .sort_values("num_docks_available", ascending=False)
            .head(10),
            use_container_width=True
        )

        st.write("### Bottom 10 Stations by Bikes")
        st.dataframe(
            filtered_df[["station_id", "name", "num_bikes_available"]]
            .sort_values("num_bikes_available", ascending=True)
            .head(10),
            use_container_width=True
        )

with col2:
    st.subheader("Map")
    ecobici_map = bike_share_system_cdmx_plot(
        filtered_df,
        station_number=selected_station,
        mode_choice=mode,
        cluster=show_cluster
    )
    st_folium(ecobici_map, width=None, height=650, use_container_width=True)

# -------------------------------------------------
# Charts
# -------------------------------------------------
chart1, chart2 = st.columns(2)

with chart1:
    st.subheader("Bikes Available Distribution")
    if not filtered_df.empty:
        st.bar_chart(
            filtered_df[["station_id", "num_bikes_available"]]
            .sort_values("num_bikes_available", ascending=False)
            .head(20)
            .set_index("station_id")
        )

with chart2:
    st.subheader("Docks Available Distribution")
    if not filtered_df.empty:
        st.bar_chart(
            filtered_df[["station_id", "num_docks_available"]]
            .sort_values("num_docks_available", ascending=False)
            .head(20)
            .set_index("station_id")
        )

# -------------------------------------------------
# Filtered data table
# -------------------------------------------------
st.subheader("Filtered Station Data")

if not filtered_df.empty:
    show_columns = [
        "station_id",
        "name",
        "lat",
        "lon",
        "capacity",
        "num_bikes_available",
        "num_docks_available",
        "num_bikes_disabled",
        "num_docks_disabled",
    ]
    st.dataframe(filtered_df[show_columns], use_container_width=True)

    csv = filtered_df[show_columns].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered Data as CSV",
        data=csv,
        file_name="ecobici_filtered_data.csv",
        mime="text/csv",
    )

# -------------------------------------------------
# Last updated
# -------------------------------------------------
if "last_reported" in df.columns and not df["last_reported"].isna().all():
    latest_report = pd.to_datetime(df["last_reported"].max(), unit="s", errors="coerce")
    if pd.notna(latest_report):
        st.caption(f"Last updated from live feed: {latest_report}")
