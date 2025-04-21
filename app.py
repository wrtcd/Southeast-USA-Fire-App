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

# Use white background style
plt.style.use('default')

st.set_page_config(layout="centered", page_title="GOES Fire Viewer")
st.title("🔥 GOES Fire Animation with Southeast USA Boundary")

# -------------------------------
# 🗺️ Southeast USA Boundary Map
# -------------------------------
st.subheader("🗺️ Click anywhere within Southeast USA")

# Load shapefile for SE USA states
seusa = gpd.read_file("data/seusa.shp")

# Create folium map
m = folium.Map(tiles='cartodbpositron')
m.fit_bounds([[seusa.total_bounds[1], seusa.total_bounds[0]],
              [seusa.total_bounds[3], seusa.total_bounds[2]]])

# Add shapefile boundary overlay
folium.GeoJson(
    seusa,
    name="SE USA States",
    style_function=lambda x: {
        'fillColor': 'none',
        'color': 'blue',
        'weight': 2
    }
).add_to(m)

# Add a center marker with instructions
center_lat = (seusa.total_bounds[1] + seusa.total_bounds[3]) / 2
center_lon = (seusa.total_bounds[0] + seusa.total_bounds[2]) / 2
folium.Marker(
    location=[center_lat, center_lon],
    icon=folium.DivIcon(html="<div style='font-size: 12px; color: gray;'>Click map to select a point</div>")
).add_to(m)

# Render map
map_data = st_folium(m, height=500, width=700)

# If point clicked, display buffer map
lat, lon = None, None
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    m2 = folium.Map(location=[lat, lon], zoom_start=7, tiles='cartodbpositron')
    folium.Circle(location=[lat, lon], radius=50000, color="red", fill=True, fill_opacity=0.2).add_to(m2)
    folium.Marker(location=[lat, lon], popup="Selected Point").add_to(m2)
    st_folium(m2, height=500, width=700)
    st.markdown(f"**Selected Coordinates:** `{lat:.4f}, {lon:.4f}`")

# -------------------------------
# 🔥 Fire Animation Section
# -------------------------------

df = pd.read_csv("firesubset-goes.csv")
df['datetime'] = pd.to_datetime(df['YearDay'].astype(str), format='%Y%j') + \
                 pd.to_timedelta(df['Time'] // 100, unit='h') + \
                 pd.to_timedelta(df['Time'] % 100, unit='m')

gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Lon'], df['Lat']), crs='EPSG:4326')
gdf = gdf.sort_values(by='datetime')

tf = TimezoneFinder()
center_lat_gdf = gdf['Lat'].mean()
center_lon_gdf = gdf['Lon'].mean()
tz_name = tf.timezone_at(lat=center_lat_gdf, lng=center_lon_gdf)
gdf['local_time'] = gdf['datetime'].dt.tz_localize('UTC').dt.tz_convert(ZoneInfo(tz_name))

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
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
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
