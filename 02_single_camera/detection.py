"""
detection.py

Provides helper functions for object detection visualization and label handling.

Includes:
- `get_labels_cached`: Efficient label retrieval with optional filtering of placeholder labels (e.g. "-").
- `draw_detection_label`: Annotates a detection bounding box and label with a translucent background.
- `average_color_at_center`: Computes the average BGR color around the center of a detection box.

These utilities are used for improving the clarity of visual feedback in the main detection pipeline.
"""


from functools import lru_cache
from typing import Tuple, List

import cv2
import numpy as np

from pose import pose_estimator, get_ground_position_from_landmarks
from parameters_file import configuration

@lru_cache
def get_labels_cached(labels_tuple: Tuple[str, ...], ignore_dash_labels: bool) -> List[str]:
    """Returns a cleaned list of labels, optionally removing dash ('-') labels.

    Args:
        labels_tuple (Tuple[str, ...]): Tuple of label strings. Used instead of list to be compatible with lru_cache.
        ignore_dash_labels (bool): If True, removes empty strings and labels equal to "-".

    Returns:
        List[str]: Filtered list of label strings.
    """
    labels = list(labels_tuple)
    if ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels


def draw_detection_label(
    frame: np.ndarray,
    label: str,
    bbox: Tuple[int, int, int, int],
    font: int = cv2.FONT_HERSHEY_SIMPLEX,
    font_scale: float = 0.5,
    text_thickness: int = 1,
    box_color: Tuple[int, int, int] = (0, 255, 0),
    text_color: Tuple[int, int, int] = (0, 0, 255),
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    alpha: float = 0.3
) -> None:
    """Draws a translucent text label and bounding box on a video frame.

    The label is rendered with a semi-transparent background above the top-left
    corner of the bounding box, which is also drawn.

    Args:
        frame (np.ndarray): The image frame to draw on (modified in-place).
        label (str): The text label to display.
        bbox (Tuple[int, int, int, int]): Bounding box in (x, y, width, height) format.
        font (int, optional): OpenCV font type for the label text.
        font_scale (float, optional): Font scale factor.
        text_thickness (int, optional): Thickness of the label text.
        box_color (Tuple[int, int, int], optional): BGR color for the bounding box.
        text_color (Tuple[int, int, int], optional): BGR color for the label text.
        bg_color (Tuple[int, int, int], optional): BGR background color for the label.
        alpha (float, optional): Transparency factor for the label background (0 to 1).

    Returns:
        None
    """
    x, y, w, h = bbox
    (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, text_thickness)

    overlay = frame.copy()
    top_left = (x + 5, y + 15 - text_height)
    bottom_right = (x + 5 + text_width, y + 15 + baseline)
    cv2.rectangle(overlay, top_left, bottom_right, bg_color, cv2.FILLED)

    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    cv2.putText(frame, label, (x + 5, y + 15), font, font_scale, text_color, text_thickness)
    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)


def average_color_at_center(
    image: np.ndarray,
    bbox: Tuple[int, int, int, int],
    kernel_size: int = configuration.detection.AVG_COLOR_KERNEL_SIZE
) -> np.ndarray:
    """Computes the average BGR color at the center of a bounding box.

    Args:
        image (np.ndarray): The full image as captured by the camera.
        bbox (Tuple[int, int, int, int]): Bounding box containing the detection (x, y, w, h).
        kernel_size (int): Size of the square region (in pixels) used to compute the average color.
        Defaults to "configuration.detection.AVG_COLOR_KERNEL_SIZE"

    Returns:
        np.ndarray: The average BGR color within a central kernel_size × kernel_size area.
    """
    x, y, w, h = bbox
    cx = int(x + w // 2)
    cy = int(y + h // 2)
    k = kernel_size // 2

    x1 = max(cx - k, 0)
    x2 = min(cx + k, image.shape[1])
    y1 = max(cy - k, 0)
    y2 = min(cy + k, image.shape[0])

    region = image[y1:y2, x1:x2]
    avg_color = region.mean(axis=(0, 1)) if region.size > 0 else np.array([0, 0, 0])
    return avg_color


def get_detection_position(label_name: str, results: object, bbox: tuple, frame: np.ndarray, H: np.ndarray,
                            fallback_fn) -> tuple:
    """
    Estimate ground position from landmarks or fallback to bounding box.

    Args:
        label_name (str): Object label.
        results (object): Pose estimation results (can be None).
        bbox (tuple): Bounding box (x, y, w, h).
        frame (np.ndarray): Frame image.
        H (np.ndarray): Homography matrix.
        fallback_fn (callable): Fallback function for bbox-based position.

    Returns:
        tuple: (position, used_pose), where used_pose is True if pose landmarks were used.
    """
    used_pose = False
    position = None

    if label_name.lower() == "person" and results:
        # Use landmark-based ground position
        position = get_ground_position_from_landmarks(label_name, results, bbox, frame, H)
        if position is not None:
            used_pose = True

    if position is None:
        # Fallback to bounding box bottom
        x, y, w, h = bbox
        position = fallback_fn([x, x + w, y, y + h], H)

    return position, used_pose


def draw_roi(frame: np.ndarray, roi: tuple) -> None:
    """
    Draw Region of Interest (ROI) on the frame.

    Args:
        frame (np.ndarray): Image frame.
        roi (tuple): (x, y, w, h) ROI coordinates.
    """
    b_x, b_y, b_w, b_h = roi
    cv2.rectangle(frame, (b_x, b_y), (b_x + b_w, b_y + b_h), (255, 0, 0), 1)
    cv2.putText(frame, "ROI", (b_x + 5, b_y + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)


def resize_map_to_match(frame: np.ndarray, map_img: np.ndarray) -> np.ndarray:
    """
    Resize the map image to match the frame height.

    Args:
        frame (np.ndarray): Camera frame.
        map_img (np.ndarray): Map image.

    Returns:
        np.ndarray: Resized map image.
    """
    if map_img.shape[0] != frame.shape[0]:
        scale = frame.shape[0] / map_img.shape[0]
        new_w = int(map_img.shape[1] * scale)
        map_img = cv2.resize(map_img, (new_w, frame.shape[0]))

    return map_img
