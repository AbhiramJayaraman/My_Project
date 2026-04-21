"""
data_parser.py

Parses custom RPi & fused track logs from multi-line text files.
Extracts positions, timestamps, and IDs for the selected track.

Functions:
- read_log_file(filepath, source, track_id): Extracts position/time for given source and track.
- save_positions_to_csv(track_data, output_path): Saves to CSV.
"""

import re
import csv
from typing import List, Dict, Tuple, Union
from config import MIN_X, MAX_X, DESIRED_LABEL


def read_log_file(filepath: str, source: str, track_id: str) -> Tuple[List[Dict[str, Union[float, List[float]]]], str]:
    """
    Reads custom text logs and extracts position/timestamp for specified source and track ID.

    Args:
        filepath (str): Log file path.
        source (str): 'fused', 'rpi1', 'rpi2', or 'rpi3'.
        track_id (str): Track ID to extract. For fused: 'GLOBAL_001', for RPi: e.g., '1'.

    Returns:
        list: List of {'timestamp': float, 'position': [x, y]} dicts.

    Raises:
        FileNotFoundError, IOError, ValueError
    """
    track_data = []
    label = None
    num_sources = None
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{filepath}' not found.")
    except (IOError, OSError) as e:
        raise IOError(f"Error reading file '{filepath}': {e}")

    current_source = None
    for i, line in enumerate(lines):
        m_source = re.search(r"Message from rpi(\d+)", line)
        if m_source:
            current_source = m_source.group(1)
        m_topic = re.search(r"Topic: devices/mocas/rpi(\d+)", line)
        if m_topic:
            current_source = m_topic.group(1)
        if source == 'fused':
            # Look for fused track entry matching GLOBAL_<track_id>:
            if f"{track_id}:" in line:
                num_sources_match = re.search(r"'num_sources': (\d+)", line)
                if num_sources_match:
                    sources = int(num_sources_match.group(1))
                    if num_sources is None or sources > num_sources:
                        num_sources = sources
                if label is None:
                    label_match = re.search(r"'label': '(\S+)", line)
                    if label_match:
                        label = label_match.group(1)
                match = re.search(r"'position': \[([0-9\.\-]+), ([0-9\.\-]+)\]", line)
                timestamp_match = re.search(r"'timestamp': ([0-9\.]+)", line)
                if match and timestamp_match:
                    x, y = float(match.group(1)), float(match.group(2))
                    timestamp = float(timestamp_match.group(1))
                    #Filter out values outside the line
                    if (MIN_X is not None and x < MIN_X) or (MAX_X is not None and x > MAX_X):
                        continue
                    track_data.append({'timestamp': timestamp, 'position': [x, y], 'num_sources': num_sources})

        else:
            # Look for per-RPi Track entries: Track <id>:
            if source == current_source:
                if f"Track {track_id}:" in line:
                    if label is None:
                        label_match = re.search(r"'label': '(\S+)", line)
                        if label_match:
                            label = label_match.group(1)
                    match = re.search(r"'position': \[([0-9\.\-]+), ([0-9\.\-]+)\]", line)
                    timestamp_match = re.search(r"'timestamp': ([0-9\.]+)", line)
                    if match and timestamp_match:
                        x, y = float(match.group(1)), float(match.group(2))
                        timestamp = float(timestamp_match.group(1))
                        # Filter out values outside the line
                        if (MIN_X is not None and x < MIN_X) or (MAX_X is not None and x > MAX_X):
                            continue
                        track_data.append({'timestamp': timestamp, 'position': [x, y]})
            #else:
                #print(f"Current source {current_source} does not match looked for source {source}")

    if not track_data:
        print(
            f"No data found for source '{source}' and track ID '{track_id}'.\n"
            f"Make sure the track exists in the log and matches the config.\n"
            f"File: {filepath}"
        )
    if label is None:
        raise ValueError(
            f"No label found for source '{source}' and track ID '{track_id}'.\n"
            f"Make sure the label exists in the log.\n"
            f"File: {filepath}"
        )
    if DESIRED_LABEL is not None and label != DESIRED_LABEL:
        print(f"Track {track_id} has label {label} and not {DESIRED_LABEL}")
        # Return empty data to signal that this track should be skipped
        return [], label
    return track_data,label


def save_positions_to_csv(track_data: List[Dict], output_path: str):
    """
    Saves extracted position data to CSV.

    Args:
        track_data (list): List of dicts with 'timestamp' and 'position'.
        output_path (str): Output CSV path.
    """
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'x', 'y'])
        for entry in track_data:
            ts = entry['timestamp']
            x, y = entry['position']
            writer.writerow([ts, x, y])


def get_track_ids_in_log(filepath: str, source: str) -> List[str]:
    """
    Scans the log file to find all track IDs for the given source.

    Args:
        filepath (str): Path to the log file.
        source (str): 'fused', 'rpi1', 'rpi2', etc.

    Returns:
        List[str]: List of track IDs found in the file.
    """
    track_ids = set()

    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{filepath}' not found.")
    except (IOError, OSError) as e:
        raise IOError(f"Error reading file '{filepath}': {e}")

    current_source = None
    for line in lines:
        m_source = re.search(r"Message from rpi(\d+)", line)
        if m_source:
            current_source = m_source.group(1)
        m_topic = re.search(r"Topic: devices/mocas/rpi(\d+)", line)
        if m_topic:
            current_source = m_topic.group(1)
        if source == 'fused':
            match = re.search(r"(GLOBAL_[0-9]+):", line)
            if match:
                track_ids.add(match.group(1))
        else:
            match = re.search(r"Track ([0-9]+):", line)
            if current_source == source:
                if match:
                    track_ids.add(match.group(1))

    return list(track_ids)