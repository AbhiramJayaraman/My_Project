"""
config.py

Centralized configuration for localization precision evaluation.
Adjust all parameters here.
"""

# Input logfile path
LOG_PATH = 'assets/mqtt_fusion_log_new_8.txt'  # Update with your filename

# Source to analyze
# For RPi tracks: e.g., '1'
# For fused data use "fused"
SOURCE_TO_ANALYZE = '2'
#Desired track_id to analyze, use a number '673' for single camera, or for fused tracks 'GLOBAL_001'
TRACK_ID = '673'
#Automatic track selection selects the track with most datapoints for a given source and label
AUTO_SELECT_TRACK = True
DESIRED_LABEL = "AGV" #Label to be evaluated, 'person' or 'AGV'

# Reference line for MAE calculation (start and end points in centimeters)
LINE_START = (400.0, 164.0)
LINE_END = (850.0, 164.0)

MIN_X = 480 #use this variable to filter out unwanted data (when AGV/person was not running in our line)
MAX_X = 800 #use this variable to filter out unwanted data

# Output directory
OUTPUT_DIR = 'assets/'

# Whether to plot the results
ENABLE_PLOTTING = True
