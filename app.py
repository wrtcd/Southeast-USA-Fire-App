import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import os

from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

from streamlit_folium import st_folium
import folium

# Optional: use white background map styling
plt.style.use('default')

st.set_page_config(layout="centered", page_title="GOES Fire Viewer")
st.title("🔥 GOES Fire Animation - April 1 Sample")

# -------------------------------
# 🗺️ Southeast USA Interactive Map
# -------------------------------
st.subheader("🗺️ Southeast USA Region")

# Coordinates to center the map roughly on Southeast USA
center_lat, center_lon = 33.0, -85.0
m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles='cartodbpositron')

# Draw rectangle over SE USA (for visual reference, optional)
se_bounds = [
    [24.5, -94.5],  # Southwest corner
    [39.0, -75.0]   # Northeast corner
]
folium.Rectangle(bounds=se_bounds, color="blue", fill=False).add_to(m)

# Instruction
folium.Marker(
    location=[center_lat, center_lon],
    icon=folium.DivIcon(html="<div style='font-size: 12px; color: gray;'>Click anywhere on the map</div>")
).add_to(m)

# Render the map
map_data = st_folium(m, height=500, width=700)

lat, lon = None, None
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    # Draw buffer map centered on point
    m2 = folium.Map(location=[lat, lon], zoom_start=7, tiles='cartodbpositron')
    folium.Circle(location=[lat, lon], radius=50000,  # 50 km
                  color="red", fill=True, fill_opacity=0.2).add_to(m2)
    folium.Marker(location=[lat, lon], popup="Selected Point").add_to(m2)
    st_folium(m2, height=500, width=700)

    # Show coordinates
    st.markdown(f"**Selected Coordinates:** `{lat:.4f}, {lon:.4f}`")

# -------------------------------
# 🔥 Fire Animation Section
# -------------------------------

# Load and process data
df = pd.read_csv("firesubset-goes.csv")

# Convert UTC datetime
df['datetime'] = pd.to_datetime(df['YearDay'].astype(str), format='%Y%j') + \
                 pd.to_timedelta(df['Time'] // 100, unit='h') + \
                 pd.to_timedelta(df['Time'] % 100, unit='m')

gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Lon'], df['Lat']), crs='EPSG:4326')
gdf = gdf.sort_values(by='datetime')

# Get local timezone for the dataset center
tf = TimezoneFinder()
center_lat_gdf = gdf['Lat'].mean()
center_lon_gdf = gdf['Lon'].mean()
tz_name = tf.timezone_at(lat=center_lat_gdf, lng=center_lon_gdf)
gdf['local_time'] = gdf['datetime'].dt.tz_localize('UTC').dt.tz_convert(ZoneInfo(tz_name))

# Button to generate animation
if st.button("Generate Fire Animation"):
    os.makedirs("frames", exist_ok=True)
    frames = []
    timestamps = pd.Series(gdf['datetime'].sort_values().unique())

    for i, t in enumerate(timestamps):
        subset = gdf[gdf['datetime'] <= t]

        local_time = pd.to_datetime(t).tz_localize('UTC').tz_convert(ZoneInfo(tz_name))
        time_str = local_time.strftime('%I:%M %p')
        date_str = local_time.strftime('%Y-%m-%d')

        fig, ax = plt.subplots(figsize=(6, 6))
        subset.plot(ax=ax, color='red', markersize=20)
        ax.set_title(f"Date: {date_str} | Local Time: {time_str}", fontsize=12)
        ax.set_xlim(gdf['Lon'].min() - 0.1, gdf['Lon'].max() + 0.1)
        ax.set_ylim(gdf['Lat'].min() - 0.1, gdf['Lat'].max() + 0.1)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True)

        filename = f"frames/frame_{i:03d}.png"
        plt.savefig(filename)
        plt.close()
        frames.append(imageio.imread(filename))

    imageio.mimsave("fire_animation.gif", frames, fps=2)
    st.success("GIF animation generated!")

# Show generated GIF
if os.path.exists("fire_animation.gif"):
    st.image("fire_animation.gif", caption="GOES Fire Progression (Local Time)", use_container_width=True)
