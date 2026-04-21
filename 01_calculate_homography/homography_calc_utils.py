"""
homography_calc_utils.py

This utility module provides a set of functions for computing, evaluating, and analyzing
homographies between 2D points in camera space and corresponding world coordinates.

Key Features:
- Load labeled 2D points from CSV files.
- Check for colinearity of point subsets to ensure valid homography estimation.
- Compute homographies using OpenCV.
- Evaluate reprojection accuracy of a homography.
- Average multiple homographies.
- Print per-point and average errors for homography validation.

Typical usage involves calling `load_points`, generating combinations of point sets,
computing homographies with `compute_homography`, and validating them using `evaluate_homography`
or `print_evaluation`.
"""

import numpy as np
import csv
import itertools
import cv2
from typing import List, Tuple, Dict
from config import COLINEARITY_THRESHOLD

def load_points(cam_path: str, world_path: str) -> Tuple[Dict[str, Tuple[float, float]],
                                                         Dict[str, Tuple[float, float]],
                                                         List[str]]:
    """
    Loads labeled 2D points from two CSV files (camera and world coordinates) and
    returns only the points that are common between both files.

    Args:
        cam_path (str): Path to the camera points CSV file.
        world_path (str): Path to the world points CSV file.

    Returns:
        Tuple containing:
            - cam_points (Dict[str, Tuple[float, float]]): Dictionary of image-space points.
            - world_points (Dict[str, Tuple[float, float]]): Dictionary of world-space points.
            - common_labels (List[str]): List of labels that exist in both files.
    """

    def read_csv(path: str) -> Dict[str, Tuple[float, float]]:
        points = {}
        with open(path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                label = row['label']
                x = float(row['x'])
                y = float(row['y'])
                points[label] = (x, y)
        return points

    cam_points = read_csv(cam_path)
    world_points = read_csv(world_path)
    common_labels = list(set(cam_points.keys()) & set(world_points.keys()))
    print(f"Found {len(common_labels)} matching points.")
    return cam_points, world_points, common_labels

def are_points_colinear(pts: List[Tuple[float, float]]) -> bool:
    """
    Determines if any subset of 3 points among the input set is colinear.

    Args:
        pts (List[Tuple[float, float]]): List of 2D points.

    Returns:
        bool: True if any 3-point combination is colinear (i.e., forms near-zero area), False otherwise.
    """

    def area(a, b, c):
        return abs((a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1])) / 2.0)
    for comb in itertools.combinations(pts, 3):
        if area(*comb) < COLINEARITY_THRESHOLD:
            return True
    return False

def compute_homography(cam_pts: List[Tuple[float, float]],
                       world_pts: List[Tuple[float, float]]) -> np.ndarray:
    """
    Computes a homography matrix from camera points to world coordinates.

    Args:
        cam_pts (List[Tuple[float, float]]): List of 2D image coordinates.
        world_pts (List[Tuple[float, float]]): List of corresponding 2D world coordinates.

    Returns:
        np.ndarray: 3x3 homography matrix mapping image to world coordinates.
    """
    cam_pts_np = np.array(cam_pts, dtype=np.float32)
    world_pts_np = np.array(world_pts, dtype=np.float32)
    H, _ = cv2.findHomography(cam_pts_np, world_pts_np)
    return H

def evaluate_homography(H: np.ndarray,
                        test_cam_pts: Dict[str, Tuple[float, float]],
                        test_world_pts: Dict[str, Tuple[float, float]]) -> Tuple[float, Dict[str, float]]:
    """
    Evaluates a homography by projecting image points and comparing to known world coordinates.

    Args:
        H (np.ndarray): Homography matrix.
        test_cam_pts (Dict[str, Tuple[float, float]]): Dictionary of camera-space test points.
        test_world_pts (Dict[str, Tuple[float, float]]): Dictionary of ground-truth world-space points.

    Returns:
        Tuple containing:
            - avg_error (float): Mean Euclidean error across all matched points.
            - errors (Dict[str, float]): Per-point reprojection errors.
    """
    errors = {}
    for label in test_cam_pts:
        if label not in test_world_pts:
            continue
        img_pt = np.array([*test_cam_pts[label], 1.0])
        projected = H @ img_pt
        projected /= projected[2]
        x_proj, y_proj = projected[0], projected[1]

        x_true, y_true = test_world_pts[label]
        error = np.sqrt((x_proj - x_true) ** 2 + (y_proj - y_true) ** 2)
        errors[label] = error

    avg_error = np.mean(list(errors.values())) if errors else float('inf')
    return avg_error, errors

def average_homographies(H_list: List[np.ndarray]) -> np.ndarray:
    """
    Computes an element-wise average of multiple homography matrices.

    Args:
        H_list (List[np.ndarray]): List of 3x3 homography matrices.

    Returns:
        np.ndarray: Averaged 3x3 homography matrix.
    """

    return np.mean(np.stack(H_list), axis=0)

def print_evaluation(H: np.ndarray,
                     name: str,
                     cam_points: Dict[str, Tuple[float, float]],
                     world_points: Dict[str, Tuple[float, float]]):
    """
    Evaluates a homography and prints the per-point error and overall average error.

    Args:
        H (np.ndarray): Homography matrix to evaluate.
        name (str): Identifier name to include in printed output.
        cam_points (Dict[str, Tuple[float, float]]): Dictionary of camera points.
        world_points (Dict[str, Tuple[float, float]]): Dictionary of ground-truth world points.
    """
    avg_err, per_point_errors = evaluate_homography(H, cam_points, world_points)
    print(f"\n--- {name} ---")
    for label, err in per_point_errors.items():
        print(f"Point {label}: Error = {err:.2f} cm")
    print(f"Average Error: {avg_err:.2f} cm")
