"""
select_points_utils.py

This module provides state, utility functions, and user interaction callbacks to support
interactive 2D point selection from an image using OpenCV. It includes support for:

- Corner and edge detection (with real-time parameter adjustment)
- Click-based point selection with zoom and pan functionality
- Labeling and saving of selected points to CSV
- Visual HUD overlay for user guidance

This module is intended to be used with `select_main.py` for an interactive GUI-based
camera calibration or feature mapping workflow.
"""
from typing import Tuple, List, Optional
import cv2
import numpy as np
import csv
from config import *

# === State and parameters ===
zoom = 1.0
pan_offset = [0, 0]
drag_start = None
click_position = None
selection_mode = "free"
current_edge_idx = 0

canny_low = CANNY_LOW
canny_high = CANNY_HIGH
hough_threshold = HOUGH_THRESHOLD
min_line_length = MIN_LINE_LENGTH
max_line_gap = MAX_LINE_GAP
corner_quality = CORNER_QUALITY
corner_min_distance = CORNER_MIN_DISTANCE

labeled_points = []
awaiting_label = False
label_buffer = ""
label_prompt_visible = False

# === Image and detection features ===
image = cv2.imread(IMAGE_FILENAME)
if image is None:
    raise FileNotFoundError("Check your image path!")

undistorted = image
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

hough_lines = []
edge_points = []
corners = []

def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp a value between a minimum and maximum bound.

    Args:
        value: The input number to be clamped.
        min_value: The lower bound.
        max_value: The upper bound.

    Returns:
        The clamped value between min_value and max_value.
    """

    return max(min_value, min(value, max_value))

def detect_features() -> None:
    """
    Detects image features in the grayscale input:
    - Canny edges
    - Hough lines
    - Shi-Tomasi corners

    Updates the global lists:
        - edge_points: interpolated points from lines
        - hough_lines: detected Hough lines
        - corners: detected corners as (x, y) points
    """

    global edge_points, corners, hough_lines

    edges = cv2.Canny(gray, canny_low, canny_high)
    hough_lines = cv2.HoughLinesP(edges, 1, np.pi / 180, hough_threshold,
                                  minLineLength=min_line_length,
                                  maxLineGap=max_line_gap)
    edge_points.clear()
    if hough_lines is not None:
        for line in hough_lines:
            x1, y1, x2, y2 = line[0]
            num_points = int(np.hypot(x2 - x1, y2 - y1))
            xs = np.linspace(x1, x2, num_points, dtype=int)
            ys = np.linspace(y1, y2, num_points, dtype=int)
            edge_points.extend(zip(xs, ys))

    crn = cv2.goodFeaturesToTrack(gray, 200, corner_quality, corner_min_distance)
    corners[:] = crn.squeeze(axis=1) if crn is not None else []

def find_nearest_point(target: Tuple[int, int],
                       points: List[Tuple[int, int]]) -> Tuple[Optional[Tuple[int, int]], Optional[int]]:
    """
    Find the nearest point to a given target from a list of 2D points.

    Args:
        target: Target (x, y) coordinates.
        points: List of (x, y) points to search from.

    Returns:
        A tuple of:
            - The nearest point as (x, y), or None if list is empty.
            - The index of the nearest point, or None if list is empty.
    """
    if not points:
        return None, None
    points = np.array(points)
    dists = np.linalg.norm(points - target, axis=1)
    idx = np.argmin(dists)
    return tuple(points[idx]), idx

def draw_hud(view: np.ndarray) -> None:
    """
    Draws the on-screen heads-up display (HUD) with keybindings, parameter values,
    and label prompt (if active).

    Args:
        view: The image on which the HUD will be rendered.
    """

    lines = [
        f"[e/c/f] Mode: {selection_mode.upper()}",
        f"[ / ]  Canny Low: {canny_low}",
        f"{{ / }}  Canny High: {canny_high}",
        f"[1/2] Hough Thresh: {hough_threshold}",
        f"[3/4] MinLineLen: {min_line_length}",
        f"[5/6] MaxLineGap: {max_line_gap}",
        f"[- / +] Corner Quality: {corner_quality:.3f}",
        f"[, / .] Corner MinDist: {corner_min_distance}",
        f"[a / d] Move along edge",
        f"[s] Save points and exit",
        f"[ESC] Exit"
    ]
    for i, line in enumerate(lines):
        cv2.putText(view, line, (10, 20 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
    if label_prompt_visible:
        cv2.putText(view, f"Label: {label_buffer}_",
                    (10, view.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 255), 2, cv2.LINE_AA)

def mouse_callback(event: int, x: int, y: int, flags: int, _: int) -> None:
    """
    OpenCV mouse callback for handling user interactions.

    Supports:
        - Left button drag to pan
        - Mouse wheel to zoom
        - Click to select and label points depending on the mode

    Args:
        event: The OpenCV mouse event code.
        x: Current x-coordinate of the cursor.
        y: Current y-coordinate of the cursor.
        flags: Additional event flags (e.g. scroll direction).
        _: Unused OpenCV parameter (commonly ignored).
    """

    global zoom, pan_offset, drag_start, click_position
    global awaiting_label, label_buffer, label_prompt_visible, current_edge_idx

    if event == cv2.EVENT_LBUTTONDOWN:
        drag_start = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        drag_start = None
        cx = int((x + pan_offset[0]) / zoom)
        cy = int((y + pan_offset[1]) / zoom)
        click_candidate = (cx, cy)

        if selection_mode == "edge":
            pt, idx = find_nearest_point(click_candidate, edge_points)
            if pt:
                click_position = pt
                current_edge_idx = idx
        elif selection_mode == "corner":
            pt, _ = find_nearest_point(click_candidate, corners)
            if pt is not None:
                click_position = tuple(map(int, pt))
        else:
            click_position = click_candidate

        if click_position:
            label_buffer = ""
            awaiting_label = label_prompt_visible = True
            print("Type label and press Enter to confirm, or ESC to cancel.")
    elif event == cv2.EVENT_MOUSEMOVE and drag_start:
        dx = x - drag_start[0]
        dy = y - drag_start[1]
        pan_offset[0] = clamp(pan_offset[0] - dx, 0, int(undistorted.shape[1] * zoom) - WINDOW_SIZE[0])
        pan_offset[1] = clamp(pan_offset[1] - dy, 0, int(undistorted.shape[0] * zoom) - WINDOW_SIZE[1])
        drag_start = (x, y)
    elif event == cv2.EVENT_MOUSEWHEEL:
        old_zoom = zoom
        zoom = clamp(zoom + (0.1 if flags > 0 else -0.1), 0.1, 10.0)
        factor = zoom / old_zoom
        pan_offset[0] = int((pan_offset[0] + x) * factor - x)
        pan_offset[1] = int((pan_offset[1] + y) * factor - y)

def save_points() -> None:
    """
    Saves the labeled points to a CSV file defined in POINTS_FILENAME.
    Each row contains a label and its (x, y) coordinates.
    """

    with open(POINTS_FILENAME, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "x", "y"])
        for label, (x, y) in labeled_points:
            writer.writerow([label, x, y])
    print("Saved to selected_points.csv")
