"""
location.py

Provides functions for estimating real-world ground positions from image coordinates
using homography, and for drawing positions on a pre-annotated map layout.

Main functionalities:
- `compute_homography()`: Loads the 3x3 matrix that maps image to room coordinates.
- `estimate_ground_position()`: Projects bounding box base points to room (cm) coordinates.
- `create_map_background()`: Loads and scales the grid-based room map for visualization.
- `draw_map_view()`: Draws a labeled point on the map to represent detected positions.

This module supports visual debugging of object locations by rendering their
estimated real-world positions on a top-down room layout image.
"""


from typing import Tuple

import numpy as np
import cv2

from parameters_file import configuration

def compute_homography() -> np.ndarray:
    """
    Load the homography matrix from disk.

    Returns:
        np.ndarray: 3x3 homography matrix mapping image points to ground coordinates.
    """
    try:
        return np.load(configuration.location.HOMOGRAPHY_PATH)  # Must be 3x3
    except FileNotFoundError:
        raise FileNotFoundError(f"Homograhpy file not found at {configuration.location.HOMOGRAPHY_PATH}")


def estimate_ground_position(bbox: Tuple[int, int, int, int], H: np.ndarray) -> Tuple[float, float]:
    """
    Estimate the ground (room) coordinates of the bottom center of a bounding box.

    Args:
        bbox (Tuple[int, int, int, int]): Bounding box as (x_start, x_end, y_start, y_end).
        H (np.ndarray): 3x3 homography matrix.

    Returns:
        Tuple[float, float]: (x, y) position in room coordinates.
    """
    x_start, x_end, y_start, y_end = bbox
    cx = (x_start + x_end) // 2
    cy = y_end  # Bottom of the bounding box
    img_pt = np.array([cx, cy, 1.0])
    ground_pt_h = H @ img_pt
    ground_pt_h /= ground_pt_h[2]
    return ground_pt_h[0], ground_pt_h[1]


def create_map_background(scale: float = 0.5, path: str = configuration.location.MAP_LAYOUT) -> Tuple[np.ndarray, float]:
    """
    Load the annotated map image with grid and axes, scaled down.

    Args:
        scale (float): Scale factor to resize image.
        path (str): Path to grid image file.

    Returns:
        Tuple[np.ndarray, float]: Scaled map image and the used scale factor.

    Raises:
        FileNotFoundError: If the image file cannot be loaded.
    """
    map_img = cv2.imread(path)
    if map_img is None:
        raise FileNotFoundError(f"Map image not found at {path}")
    if scale != 1.0:
        map_img = cv2.resize(map_img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return map_img, scale


def draw_map_view(
        map_img: np.ndarray,
        position_cm: Tuple[float, float],
        label_name: str,
        scale: float = 0.5
) -> np.ndarray:
    """
    Plot a labeled point in cm onto the map image.

    Args:
        map_img (np.ndarray): Scaled map image to draw on.
        position_cm (Tuple[float, float]): (x_cm, y_cm) position in cm.
        label_name (str): Text label for this point.
        scale (float): The scale used when loading the map.

    Returns:
        np.ndarray: Modified image with the drawn dot and label.
    """
    x_cm, y_cm = position_cm

    # Compute full-resolution pixel position relative to the origin
    origin_x_full = (configuration.location.IMG_WIDTH -
                     configuration.location.GRID_WIDTH_CM -
                     configuration.location.MARGIN_RIGHT)
    origin_y_full = configuration.location.MARGIN_TOP
    x_px_full = origin_x_full + (configuration.location.GRID_WIDTH_CM - x_cm)
    y_px_full = origin_y_full + y_cm

    # Scale to match resized map image
    px = int(x_px_full * scale)
    py = int(y_px_full * scale)

    # Draw the point
    cv2.circle(map_img, (px, py), 5, (0, 0, 255), -1)

    label_text = f"{label_name} ({int(x_cm)}cm, {int(y_cm)}cm)"

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    thickness = 1

    text_size, _ = cv2.getTextSize(label_text, font, font_scale, thickness)
    text_width = text_size[0]
    max_width = map_img.shape[1] - px - 10

    if text_width > max_width:
        # Wrap into two lines
        label_main = label_name
        label_coords = f"({int(x_cm)}cm, {int(y_cm)}cm)"
        cv2.putText(map_img, label_main, (px, max(15, py - 15)), font, font_scale, (0, 0, 255), thickness)
        cv2.putText(map_img, label_coords, (px, py - 2), font, font_scale, (0, 0, 255), thickness)
    else:
        text_x = max(0, px - 40)
        text_y = max(15, py - 10)
        cv2.putText(map_img, label_text, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)

    return map_img
