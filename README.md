# Strava Activity Heatmap Generator

This Python script processes your entire Strava activity history from a bulk data export to generate a single, interactive heatmap of all your GPS tracks. It's a great way to visualize where you've been over the years.

## Features

-   **Supports Multiple Formats**: Processes both `.fit` and `.gpx` activity files.
-   **Handles Compressed Files**: Automatically decompresses and reads `.fit.gz` and `.gpx.gz` files, which are common in Strava exports.
-   **Recursive Search**: Scans the entire `activities` folder and all its subdirectories, so you don't have to worry about file organization.
-   **Interactive Map**: Generates a single `strava_heatmap.html` file that you can open in any web browser to pan and zoom.
-   **Resilient**: Includes error handling to skip corrupted or unreadable files without crashing.

## Requirements

-   Python 3.6+
-   The required Python libraries, which can be installed via `pip`.

## Setup

### 1. Get Your Strava Data

1.  Log in to your Strava account.
2.  Go to **Settings** > **My Account** > **Download or Delete Your Account**.
3.  Click **Request Your Archive** under "Download your data".
4.  Strava will email you a link to download a `.zip` file containing all your data. This can take a few hours.

### 2. Prepare the Project Folder

1.  Download the `.zip` file from Strava and extract it.
2.  Inside the extracted folder, you will find an `activities` folder.
3.  Place the `convert_activities.py` script in a parent directory. Your folder structure should look like this:

    ```
    your-strava-project/
    ├── convert_activities.py
    └── activities/
        ├── 1234567.fit.gz
        ├── 1234568.gpx.gz
        └── ... (all your other activity files)
    ```

    The script is pre-configured to look for this `activities` subfolder.

### 3. Install Dependencies

Navigate to the project directory in your terminal and install the required libraries using the provided `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Usage

Once your folder is set up and dependencies are installed, simply run the script from your terminal:

```bash
python convert_activities.py
```

The script will scan for all activity files, process them, and generate the heatmap. You will see progress printed in the console.

## Output

After the script finishes, a file named `strava_heatmap.html` will be created in your project directory. Open this file in your web browser to view your personal heatmap.

## Configuration

The script has two main configuration variables at the top of the file:

-   `INPUT_FOLDER`: The path to your `activities` folder. It defaults to a subfolder named `activities` in the same directory as the script.
-   `OUTPUT_MAP_FILE`: The name of the output HTML file. Defaults to `strava_heatmap.html`.

You can modify these if your folder structure is different.
