import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import os

from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

# Optional: match Streamlit dark theme
plt.style.use('dark_background')

st.set_page_config(layout="centered", page_title="GOES Fire Viewer")
st.title("🔥 GOES Fire Animation - April 1 Sample")

# -------------------------------
# 🗺️ Southeast USA Map Section
# -------------------------------
st.subheader("🗺️ Southeast USA Region")

# Load US states from naturalearth dataset
us_states = gpd.read_file("https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json")

# Your 12 Southeast states
se_states = [
    "Alabama", "Arkansas", "Florida", "Georgia", "Kentucky",
    "Louisiana", "Mississippi", "North Carolina", "South Carolina",
    "Tennessee", "Virginia", "West Virginia"
]

# Filter to only those
seusa = us_states[us_states['name'].isin(se_states)]

# Plot the SE region
fig, ax = plt.subplots(figsize=(8, 6))
seusa.boundary.plot(ax=ax, color='cyan', linewidth=1)
seusa.plot(ax=ax, color='black', alpha=0.3)
ax.set_title("Southeast USA Focus Area", fontsize=14)
ax.axis('off')
st.pyplot(fig)

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

# Get local timezone
tf = TimezoneFinder()
center_lat = gdf['Lat'].mean()
center_lon = gdf['Lon'].mean()
tz_name = tf.timezone_at(lat=center_lat, lng=center_lon)
gdf['local_time'] = gdf['datetime'].dt.tz_localize('UTC').dt.tz_convert(ZoneInfo(tz_name))

# Button to trigger animation
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

# Show GIF
if os.path.exists("fire_animation.gif"):
    st.image("fire_animation.gif", caption="GOES Fire Progression (Local Time)", use_container_width=True)
