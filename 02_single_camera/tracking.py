"""
tracking.py

This module initializes and manages object tracking using the BYTETracker algorithm.
It provides functionality for converting detections into the format expected by BYTETracker,
computing bounding box IoU for matching, and maintaining per-track metadata such as
labels, confidence scores, and age.

Main components:
- `tracker`: Initialized BYTETracker instance with parameters from the configuration.
- `detections_to_bytetracker_format()`: Converts detection objects to BYTETracker input format.
- `update_track_metadata()`: Matches tracker outputs to detections and updates global track state.
- `iou()`: Utility function for computing intersection-over-union between bounding boxes.

This module is intended to be called from a main inference loop, where detections and
tracks are updated per frame.
"""


from types import SimpleNamespace
from typing import List, Optional, Dict, Tuple, Any

import numpy as np

from tracker.byte_tracker import BYTETracker
from parameters_file import configuration

# === BYTETracker Parameters ===
args = SimpleNamespace(
    track_thresh=configuration.tracking.TRACK_THRESH,
    track_buffer=configuration.tracking.MAX_AGE,
    match_thresh=configuration.tracking.MATCH_THRESH,
    mot20=configuration.tracking.MOT20,
    low_thresh=configuration.tracking.LOW_THRESH
)

# === Tracker Initialization ===
tracker = BYTETracker(args, frame_rate=configuration.tracking.FRAME_RATE)

# === Global Tracking Metadata ===
track_metadata: Dict[int, Dict[str, Any]] = {}  # track_id -> {label, confidence}
track_age: Dict[int, int] = {}                   # track_id -> stale frame counter


def detections_to_bytetracker_format(detections: List[Any]) -> np.ndarray:
    """
    Convert a list of Detection objects to BYTETracker's expected input format.

    Args:
        detections (List[Any]): List of detection objects with `.box` (x, y, w, h) and `.conf` attributes.

    Returns:
        np.ndarray: Array of shape (N, 5) with detection boxes in [x1, y1, x2, y2, conf] format.
                    Empty array if no detections.
    """
    dets = []
    for det in detections:
        x, y, w, h = det.box
        dets.append([x, y, x + w, y + h, det.conf])
    return np.array(dets, dtype=np.float32) if dets else np.empty((0, 5), dtype=np.float32)


def iou(boxA: List[float], boxB: List[float]) -> float:
    """
    Compute the Intersection-over-Union (IoU) of two bounding boxes.

    Args:
        boxA (List[float]): Bounding box A in format [x1, y1, x2, y2].
        boxB (List[float]): Bounding box B in format [x1, y1, x2, y2].

    Returns:
        float: IoU value between 0.0 and 1.0.
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_area = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    areaA = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    areaB = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

    return inter_area / float(areaA + areaB - inter_area + 1e-6)


def update_track_metadata(
    tracks: List[Any],
    detections: List[Any],
    labels: List[str]
) -> None:
    """
    Update global tracking metadata by matching BYTETracker tracks to detections based on IoU.

    Args:
        tracks (List[Any]): List of active tracks from BYTETracker, each with `.tlwh` and `.track_id`.
        detections (List[Any]): List of detection objects with `.box`, `.conf`, and `.category`.
        labels (List[str]): List of label strings indexed by detection category.

    Updates:
        track_metadata (Dict[int, Dict[str, Any]]): Updates labels and confidences for matched tracks.
        track_age (Dict[int, int]): Resets or increments stale age counters for tracks.
    """
    active_track_ids = set()

    for track in tracks:
        track_id = int(track.track_id)
        x, y, w, h = track.tlwh
        track_box = [x, y, x + w, y + h]

        best_iou = 0.0
        best_det: Optional[Any] = None

        for det in detections:
            dx, dy, dw, dh = det.box
            det_box = [dx, dy, dx + dw, dy + dh]
            i = iou(track_box, det_box)
            if i > best_iou:
                best_iou = i
                best_det = det

        if best_iou > configuration.tracking.IOU_THRESHOLD and best_det:
            track_metadata[track_id] = {
                "label": labels[int(best_det.category)],
                "conf": best_det.conf
            }
            track_age[track_id] = 0
            active_track_ids.add(track_id)

    # Routine cleaning of old tracks to avoid filling up the track dictionary
    for tid in list(track_metadata.keys()):
        if tid not in active_track_ids:
            track_age[tid] = track_age.get(tid, 0) + 1
            if track_age[tid] > configuration.tracking.MAX_AGE:
                track_metadata.pop(tid, None)
                track_age.pop(tid, None)
