"""
evaluation.py

Computes Mean Absolute Error (MAE) of track data vs. a ground truth line.
"""

import numpy as np
from typing import List, Tuple, Dict

def fit_line_between_points(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[np.ndarray, np.ndarray]:
    p1_np = np.array(p1)
    p2_np = np.array(p2)
    direction = p2_np - p1_np
    return p1_np, direction

def compute_point_to_line_error(point: Tuple[float, float], line_start: np.ndarray, direction: np.ndarray) -> float:
    point_vec = np.array(point) - line_start
    proj_length = np.dot(point_vec, direction) / np.linalg.norm(direction)
    proj_point = line_start + proj_length * direction / np.linalg.norm(direction)
    error = np.linalg.norm(point_vec - (proj_point - line_start))
    return error

def compute_mae(track_data: List[Dict], line_start: Tuple[float, float], line_end: Tuple[float, float]) -> float:
    start, direction = fit_line_between_points(line_start, line_end)
    errors = []

    for entry in track_data:
        pos = tuple(entry['position'])
        err = compute_point_to_line_error(pos, start, direction)
        errors.append(err)

    return np.mean(errors)
