"""
select_points_main.py

This script launches an interactive OpenCV-based GUI for selecting and labeling 2D points
in an image. It supports corner and edge detection modes, panning, zooming, labeling,
and saving of labeled points.

Features:
- Mouse-based point selection with HUD feedback.
- Live view with pan/zoom and interactive overlays.
- Adjustable feature detection parameters (e.g., Canny edges, Hough lines, corners).
- Modes for selecting corners, edges, or free-form points.
- Label entry via keyboard, with live HUD display.
- Saves selected and labeled points to file on keypress.

Key Bindings:
- ESC: Exit or cancel labeling.
- S: Save labeled points and exit.
- C: Switch to corner selection mode.
- E: Switch to edge selection mode.
- F: Switch to free point mode.
- A/D: Navigate edge points left/right.
- [/] and {}/1-6/-/+/., etc.: Adjust feature detection parameters in real-time.

Dependencies:
- OpenCV (cv2)
- `select_points_utils.py` for detection logic and state handling.
- `config.py` for display/window constants.

Intended Use:
- Homography calculation workflows where labeled 2D points are needed from corners, edges, or arbitrary clicks.
"""

import cv2
from config import *
import select_points_utils as su

cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
cv2.setMouseCallback(WIN_NAME, su.mouse_callback)

su.detect_features()

while True:
    resized = cv2.resize(su.undistorted, None, fx=su.zoom, fy=su.zoom)
    h, w = resized.shape[:2]
    su.pan_offset[0] = su.clamp(su.pan_offset[0], 0, max(w - WINDOW_SIZE[0], 0))
    su.pan_offset[1] = su.clamp(su.pan_offset[1], 0, max(h - WINDOW_SIZE[1], 0))

    view = resized[su.pan_offset[1]:su.pan_offset[1] + WINDOW_SIZE[1],
                   su.pan_offset[0]:su.pan_offset[0] + WINDOW_SIZE[0]].copy()

    if su.click_position:
        px = int(su.click_position[0] * su.zoom - su.pan_offset[0])
        py = int(su.click_position[1] * su.zoom - su.pan_offset[1])
        if 0 <= px < view.shape[1] and 0 <= py < view.shape[0]:
            cv2.circle(view, (px, py), 5, (0, 0, 255), -1)

    if su.selection_mode == "corner":
        for pt in su.corners:
            x, y = map(int, pt)
            x = int(x * su.zoom - su.pan_offset[0])
            y = int(y * su.zoom - su.pan_offset[1])
            if 0 <= x < view.shape[1] and 0 <= y < view.shape[0]:
                cv2.circle(view, (x, y), 2, (0, 255, 0), -1)
    elif su.selection_mode == "edge" and su.hough_lines is not None:
        for line in su.hough_lines:
            x1, y1, x2, y2 = line[0]
            x1 = int(x1 * su.zoom - su.pan_offset[0])
            y1 = int(y1 * su.zoom - su.pan_offset[1])
            x2 = int(x2 * su.zoom - su.pan_offset[0])
            y2 = int(y2 * su.zoom - su.pan_offset[1])
            cv2.line(view, (x1, y1), (x2, y2), (0, 255, 255), 1)

    su.draw_hud(view)
    cv2.imshow(WIN_NAME, view)
    key = cv2.waitKey(20)

    if su.awaiting_label:
        if key in (13, 10):  # Enter
            if su.label_buffer.strip():
                su.labeled_points.append((su.label_buffer.strip(), su.click_position))
                print(f"Saved point: {su.label_buffer.strip()} -> {su.click_position}")
            su.awaiting_label = su.label_prompt_visible = False
            su.click_position = None
        elif key == 27:  # ESC
            su.awaiting_label = su.label_prompt_visible = False
            su.click_position = None
        elif key == 8:  # Backspace
            su.label_buffer = su.label_buffer[:-1]
        elif 32 <= key <= 126:
            su.label_buffer += chr(key)
        continue

    if key == 27:
        break
    elif key == ord("s"):
        su.save_points()
        break
    elif key == ord("e"):
        su.selection_mode = "edge"
    elif key == ord("c"):
        su.selection_mode = "corner"
    elif key == ord("f"):
        su.selection_mode = "free"
    elif key == ord("a") and su.edge_points:
        su.current_edge_idx = max(su.current_edge_idx - 1, 0)
        su.click_position = tuple(su.edge_points[su.current_edge_idx])
    elif key == ord("d") and su.edge_points:
        su.current_edge_idx = min(su.current_edge_idx + 1, len(su.edge_points) - 1)
        su.click_position = tuple(su.edge_points[su.current_edge_idx])
    elif key == ord("["):
        su.canny_low = max(0, su.canny_low - 10); su.detect_features()
    elif key == ord("]"):
        su.canny_low += 10; su.detect_features()
    elif key == ord("{"):
        su.canny_high = max(0, su.canny_high - 10); su.detect_features()
    elif key == ord("}"):
        su.canny_high += 10; su.detect_features()
    elif key == ord("1"):
        su.hough_threshold = max(1, su.hough_threshold - 5); su.detect_features()
    elif key == ord("2"):
        su.hough_threshold += 5; su.detect_features()
    elif key == ord("3"):
        su.min_line_length = max(1, su.min_line_length - 5); su.detect_features()
    elif key == ord("4"):
        su.min_line_length += 5; su.detect_features()
    elif key == ord("5"):
        su.max_line_gap = max(0, su.max_line_gap - 1); su.detect_features()
    elif key == ord("6"):
        su.max_line_gap += 1; su.detect_features()
    elif key == ord("-"):
        su.corner_quality = max(0.001, su.corner_quality - 0.001); su.detect_features()
    elif key in (ord("+"), ord("=")):
        su.corner_quality = min(1.0, su.corner_quality + 0.001); su.detect_features()
    elif key == ord(","):
        su.corner_min_distance = max(1, su.corner_min_distance - 1); su.detect_features()
    elif key == ord("."):
        su.corner_min_distance += 1; su.detect_features()

cv2.destroyAllWindows()
