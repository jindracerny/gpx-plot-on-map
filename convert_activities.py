import os
import glob
import fitdecode
import gpxpy
import gpxpy.gpx as mod_gpx 
import pandas as pd
import folium
from folium.plugins import HeatMap
from datetime import datetime
import xml.etree.ElementTree as ET
import gzip

# --- CONFIGURATION ---
# 1. SET THE PATH TO YOUR STRAVA ACTIVITIES FOLDER
# IMPORTANT: This should point to the folder containing your .fit and .gpx files.
INPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activities')

# 2. SET THE OUTPUT FILE NAME for the interactive HTML map
OUTPUT_MAP_FILE = "strava_heatmap.html"

# Garmin stores coordinates in semicircles. This constant is used for conversion to degrees.
GARMIN_SEMI_TO_DEG = 180 / (2**31)
# --------------------

def convert_semicircles_to_degrees(semicircles):
    """Converts Garmin semicircle coordinate format to standard degrees."""
    if semicircles is None:
        return None
    return semicircles * GARMIN_SEMI_TO_DEG

def get_fit_points(file_path):
    """Extracts (lat, lon) tuples from a single .FIT file, handling .gz compression."""
    points = []
    try:
        open_func = gzip.open if file_path.endswith('.gz') else open
        with open_func(file_path, 'rb') as f:
            with fitdecode.FitReader(f) as fit_file:
                for frame in fit_file:
                    if isinstance(frame, fitdecode.records.FitDataMessage) and frame.name == 'record':
                        lat_semi = frame.get_value('position_lat', fallback=None)
                        lon_semi = frame.get_value('position_long', fallback=None)
                        
                        if lat_semi is not None and lon_semi is not None:
                            lat_deg = convert_semicircles_to_degrees(lat_semi)
                            lon_deg = convert_semicircles_to_degrees(lon_semi)
                            points.append((lat_deg, lon_deg))
    except Exception as e:
        print(f"  Warning: Could not parse FIT file {os.path.basename(file_path)}. Error: {e}")
        return []
    return points

def get_gpx_points(file_path):
    """Extracts (lat, lon) tuples from a single .GPX file, handling .gz compression."""
    points = []
    try:
        open_func = gzip.open if file_path.endswith('.gz') else open
        with open_func(file_path, 'rt', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        # Extract only latitude and longitude
                        points.append((point.latitude, point.longitude))
    except Exception as e:
        print(f"  Warning: Could not parse GPX file {os.path.basename(file_path)}. Error: {e}")
        return []
        
    return points


def generate_heatmap(input_dir, output_file_name):
    """
    Collects all track points from .fit and .gpx files and generates an HTML heatmap.
    """
    
    # 1. Collect all file paths recursively, including .gz files
    print(f"🔍 Searching for activity files in '{input_dir}' (including subdirectories)...")
    fit_paths = glob.glob(os.path.join(input_dir, '**', '*.fit'), recursive=True) + \
                glob.glob(os.path.join(input_dir, '**', '*.fit.gz'), recursive=True)
    gpx_paths = glob.glob(os.path.join(input_dir, '**', '*.gpx'), recursive=True) + \
                glob.glob(os.path.join(input_dir, '**', '*.gpx.gz'), recursive=True)
    file_paths = sorted(fit_paths + gpx_paths)
    
    if not file_paths:
        print(f"❌ Error: No .fit or .gpx files (or their .gz compressed versions) found in {input_dir}. Please check the folder path.")
        return

    all_coordinates = []
    total_files = len(file_paths)
    print(f"Found {total_files} activity files. Starting to process...")

    # 2. Process all files and collect coordinates
    for i, input_file in enumerate(file_paths):
        relative_path = os.path.relpath(input_file, input_dir)
        print(f"  Processing file {i+1}/{total_files}: {relative_path}")
        
        file_name_lower = input_file.lower()
        
        if file_name_lower.endswith('.fit') or file_name_lower.endswith('.fit.gz'):
            points = get_fit_points(input_file)
        elif file_name_lower.endswith('.gpx') or file_name_lower.endswith('.gpx.gz'):
            points = get_gpx_points(input_file)
        else:
            continue # Should not happen with the glob above, but good practice

        if points:
            all_coordinates.extend(points)

    if not all_coordinates:
        print("❌ Error: Zero track points were successfully extracted. Check your files for corruption.")
        return
    
    # 3. Standardize Data using Pandas
    df = pd.DataFrame(all_coordinates, columns=['lat', 'lon'])
    print(f"\n✅ Successfully extracted {len(df)} total track points.")

    # 4. Generate the Heatmap
    print("🎨 Generating interactive Folium heatmap...")
    
    # Calculate the average center for the initial map view
    start_lat = df['lat'].mean()
    start_lon = df['lon'].mean()
    
    # Create the base map
    m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    
    # Add the HeatMap layer. The coordinates should be in a list of [lat, lon].
    HeatMap(df[['lat', 'lon']].values.tolist()).add_to(m)
    
    # 5. Save the Map
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file_name)
    m.save(output_path)
    
    print(f"\n--- Done ---")
    print(f"🎉 Heatmap successfully saved to: {output_path}")
    print(f"Open '{output_file_name}' in your web browser to view the result.")


if __name__ == "__main__":
    # Ensure the configured input folder actually exists before processing
    if not os.path.isdir(INPUT_FOLDER):
        print(f"❗ Error: Input folder not found: {INPUT_FOLDER}")
        print("Please create the folder or update INPUT_FOLDER to the correct path containing your .fit/.gpx files.")
    else:
        generate_heatmap(INPUT_FOLDER, OUTPUT_MAP_FILE)