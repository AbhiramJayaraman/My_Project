"""
plot_utils.py

Optional module for visualizing localization tracks and error over time.

Functions:
- plot_positions_vs_line(): Plots tracked positions and the reference line.
- plot_error_over_time(): Plots error vs time.
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Tuple

def plot_positions_vs_line(track_data: List[Dict], line_start: Tuple[float, float], line_end: Tuple[float, float], title: str,mae_text:str):
    """
    Plots tracked positions against the reference trajectory line.

    Args:
        track_data (list): List of positions with 'position' field.
        line_start (tuple): Start point of the reference line.
        line_end (tuple): End point of the reference line.
        title (str): Plot title.
        mae_text(str): Text showing the MAE
    """
    xs = [entry['position'][0] for entry in track_data]
    ys = [entry['position'][1] for entry in track_data]

    line_x = [line_start[0], line_end[0]]
    line_y = [line_start[1], line_end[1]]

    plt.figure(figsize=(8,6))
    plt.plot(xs, ys, 'o', label='Tracked positions')
    plt.plot(line_x, line_y, 'r-', label='Reference line')
    plt.xlabel('X (centimeters)')
    plt.ylabel('Y (centimeters)')
    plt.title(title)
    plt.legend()
    plt.axis('equal')
    plt.grid(True)
    plt.text(0.05, 0.95, mae_text,
             transform=plt.gca().transAxes,  # Use axes coordinates (0 to 1)
             fontsize=10,
             verticalalignment='top',
             bbox=dict(boxstyle="round", facecolor="white", alpha=0.5))  # Optional background
    plt.show()

def plot_error_over_time(track_data: List[Dict], errors: List[float], title: str):
    """
    Plots the error over time.

    Args:
        track_data (list): Track data list containing timestamps.
        errors (list): List of error magnitudes.
        title (str): Plot title.
    """
    timestamps = [entry['timestamp'] for entry in track_data]

    plt.figure(figsize=(8,4))
    plt.plot(timestamps, errors, marker='o')
    plt.xlabel('Timestamp (s)')
    plt.ylabel('Error (centimeters)')
    plt.title(title)
    plt.grid(True)
    plt.show()
