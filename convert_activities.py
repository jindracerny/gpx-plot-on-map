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
import argparse # Import argparse

# --- CONFIGURATION ---
# 1. SET THE PATH TO YOUR STRAVA ACTIVITIES FOLDER
# IMPORTANT: This should point to the folder containing your .fit and .gpx files.
INPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activities')

# 2. SET THE OUTPUT FILE NAME for the interactive HTML map
OUTPUT_MAP_FILE = "strava_activity_map.html"

# Garmin stores coordinates in semicircles. This constant is used for conversion to degrees.
GARMIN_SEMI_TO_DEG = 180 / (2**31)
# --------------------

def convert_semicircles_to_degrees(semicircles):
    """Converts Garmin semicircle coordinate format to standard degrees."""
    if semicircles is None:
        return None
    return semicircles * GARMIN_SEMI_TO_DEG

def get_fit_points(file_path):
    """Extracts (lat, lon) tuples, activity type, and start time from a single .FIT file, handling .gz compression."""
    points = []
    activity_type = 'Unknown'
    start_time = None # Initialize start_time
    try:
        open_func = gzip.open if file_path.endswith('.gz') else open
        with open_func(file_path, 'rb') as f:
            with fitdecode.FitReader(f) as fit_file:
                for frame in fit_file:
                    if isinstance(frame, fitdecode.records.FitDataMessage):
                        if frame.name == 'record':
                            lat_semi = frame.get_value('position_lat', fallback=None)
                            lon_semi = frame.get_value('position_long', fallback=None)
                            
                            if lat_semi is not None and lon_semi is not None:
                                lat_deg = convert_semicircles_to_degrees(lat_semi)
                                lon_deg = convert_semicircles_to_degrees(lon_semi)
                                points.append((lat_deg, lon_deg))
                        elif frame.name == 'session': # Extract activity type and start time from session frame
                            sport = frame.get_value('sport', fallback=None)
                            if sport:
                                activity_type = sport.capitalize()
                            if frame.has_field('start_time'):
                                start_time = frame.get_value('start_time')
    except Exception as e:
        print(f"  Warning: Could not parse FIT file {os.path.basename(file_path)}. Error: {e}")
        return [], 'Unknown', None # Return None for start_time on error
    return points, activity_type, start_time

def get_gpx_points(file_path):
    """Extracts (lat, lon) tuples, activity type, and start time from a single .GPX file, handling .gz compression."""
    points = []
    activity_type = 'Unknown'
    start_time = None # Initialize start_time
    try:
        open_func = gzip.open if file_path.endswith('.gz') else open
        with open_func(file_path, 'rt', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            
            start_time = gpx.get_time_bounds().start_time # Extract start time from GPX
            
            if gpx.tracks:
                # Use the type from the first track, which is common for Strava GPX files
                track_type = gpx.tracks[0].type
                if track_type:
                    activity_type = track_type.capitalize()

            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        # Extract only latitude and longitude
                        points.append((point.latitude, point.longitude))
    except Exception as e:
        print(f"  Warning: Could not parse GPX file {os.path.basename(file_path)}. Error: {e}")
        return [], 'Unknown', None # Return None for start_time on error
        
    return points, activity_type, start_time


def generate_activity_map(input_dir, output_file_name, target_year=None): # Add target_year parameter
    """
    Collects all track points from .fit and .gpx files and generates an HTML map with activity polylines.
    """
    
    # Modify output filename if a year is specified
    if target_year: # Use target_year parameter
        base, ext = os.path.splitext(output_file_name)
        output_file_name = f"{base}_{target_year}{ext}"
        print(f"ℹ️  Filtering activities for the year {target_year}.") # Use target_year parameter

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

    all_activities = []
    total_files = len(file_paths)
    print(f"Found {total_files} activity files. Starting to process...")

    # 2. Process all files and collect coordinates, activity types, and start times
    for i, input_file in enumerate(file_paths):
        relative_path = os.path.relpath(input_file, input_dir)
        print(f"  Processing file {i+1}/{total_files}: {relative_path}")
        
        file_name_lower = input_file.lower()
        
        if file_name_lower.endswith('.fit') or file_name_lower.endswith('.fit.gz'):
            points, activity_type, start_time = get_fit_points(input_file)
        elif file_name_lower.endswith('.gpx') or file_name_lower.endswith('.gpx.gz'):
            points, activity_type, start_time = get_gpx_points(input_file)
        else:
            continue # Should not happen with the glob above, but good practice

        # Filter by year if target_year is set
        if target_year and (not start_time or start_time.year != target_year): # Use target_year parameter
            continue

        if points:
            all_activities.append({'points': points, 'type': activity_type, 'date': start_time})

    if not all_activities:
        print("❌ Error: Zero activities with track points were successfully extracted. Check your files for corruption or the year filter.")
        return
    
    # 3. Calculate Map Center from all points
    all_points_for_center = [pt for activity in all_activities for pt in activity['points']]
    if not all_points_for_center:
        print("❌ Error: No GPS points found in any activities after filtering.")
        return

    df_center = pd.DataFrame(all_points_for_center, columns=['lat', 'lon'])
    print(f"\n✅ Successfully processed {len(all_activities)} activities with GPS data.")

    # 4. Generate the Activity Map
    print("🎨 Generating interactive Folium activity map...")
    
    # Calculate the average center for the initial map view
    start_lat = df_center['lat'].mean()
    start_lon = df_center['lon'].mean()
    
    # Create the base map
    m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    
    # Add each activity as a red line
    for activity in all_activities:
        activity_type = activity.get('type', 'Unknown')
        activity_date = activity.get('date')
        date_str = activity_date.strftime('%Y-%m-%d') if activity_date else 'N/A'
        
        folium.PolyLine(
            locations=activity['points'],
            color='red', # All activities will be red
            weight=3,
            opacity=0.8,
            popup=f"Activity: {activity_type}<br>Date: {date_str}"
        ).add_to(m)
    
    # 5. Save the Map
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file_name)
    m.save(output_path)
    
    print(f"\n--- Done ---")
    print(f"🎉 Activity map successfully saved to: {output_path}")
    print(f"Open '{output_file_name}' in your web browser to view the result.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an interactive map of Strava activities.")
    parser.add_argument('--year', type=int, help="Filter activities for a specific year (e.g., 2025). If not provided, all years are processed.")
    args = parser.parse_args()

    # Ensure the configured input folder actually exists before processing
    if not os.path.isdir(INPUT_FOLDER):
        print(f"❗ Error: Input folder not found: {INPUT_FOLDER}")
        print("Please create the folder or update INPUT_FOLDER to the correct path containing your .fit/.gpx files.")
    else:
        generate_activity_map(INPUT_FOLDER, OUTPUT_MAP_FILE, target_year=args.year) # Pass args.year