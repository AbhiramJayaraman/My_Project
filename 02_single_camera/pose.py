"""
pose.py

Provides functions for estimating ground positions using MediaPipe Pose landmarks.
Focuses on extracting foot positions (or extrapolated equivalents) from detected persons,
and projecting them onto a real-world coordinate system using homography.

Key functionality:
- Setup of the MediaPipe pose estimator.
- `get_ground_position_from_landmarks()`: Estimates ground position from feet or inferred lower-body keypoints.
- Annotates pose landmarks, foot points, and interpolation steps on the original image.

Used for improving localization accuracy of humans detected via bounding boxes by
relying on precise body part positions.
"""


from typing import Optional, Tuple, List

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats.landmark_pb2 import NormalizedLandmarkList


from parameters_file import configuration

# === POSE SETUP ===
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose_estimator = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False
)


def get_ground_position_from_landmarks(
    label_name: str,
    results: NormalizedLandmarkList,
    bbox: Tuple[int, int, int, int],
    frame: np.ndarray,
    H: np.ndarray,
    confidence_threshold: float = configuration.pose.GENERAL_CONFIDENCE_THRESHOLD
) -> Optional[Tuple[float, float]]:
    """Estimates ground position from foot landmarks using MediaPipe pose data.

    Args:
        label_name (str): Object label, must be 'person' to process.
        results (NormalizedLandmarkList): Pose estimation results.
        bbox (Tuple[int, int, int, int]): Bounding box (x, y, w, h) of the detection.
        frame (np.ndarray): Current image frame to annotate.
        H (np.ndarray): Homography matrix to map image coordinates to ground coordinates.
        confidence_threshold (float): Visibility threshold for landmarks to be considered valid.

    Returns:
        Optional[Tuple[float, float]]: (x, y) ground coordinates in world space, or None if unavailable.
    """
    if label_name.lower() != "person" or not results.pose_landmarks:
        return None

    landmarks = results.pose_landmarks.landmark
    x, y, w, h = bbox
    foot_pts: List[Tuple[int, int]] = []

    # === DRAW POSE SKELETON INSIDE BBOX ===
    for start_idx, end_idx in mp_pose.POSE_CONNECTIONS:
        start = landmarks[start_idx]
        end = landmarks[end_idx]

        if start.visibility > confidence_threshold and end.visibility > confidence_threshold:
            x1 = int(start.x * frame.shape[1])
            y1 = int(start.y * frame.shape[0])
            x2 = int(end.x * frame.shape[1])
            y2 = int(end.y * frame.shape[0])

            if x <= x1 <= x + w and y <= y1 <= y + h and x <= x2 <= x + w and y <= y2 <= y + h:
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # === DIRECT FOOT LANDMARKS ===
    for idx in [mp_pose.PoseLandmark.LEFT_FOOT_INDEX, mp_pose.PoseLandmark.RIGHT_FOOT_INDEX]:
        lm = landmarks[idx]
        if lm.visibility > confidence_threshold:
            fx = int(lm.x * frame.shape[1])
            fy = int(lm.y * frame.shape[0])
            if x <= fx <= x + w and y <= fy <= y + h:
                foot_pts.append((fx, fy))
                cv2.circle(frame, (fx, fy), 4, (255, 0, 255), -1)
                cv2.putText(frame, "Foot", (fx + 5, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

    # only interpolate the foot position if the real foot position could not be found directly
    if len(foot_pts) < 2:
        try_hip = False
        #try to interpolate foot position from the knee and ankle first, as it is more precise
        for knee_idx, ankle_idx in [
            (mp_pose.PoseLandmark.LEFT_KNEE, mp_pose.PoseLandmark.LEFT_ANKLE),
            (mp_pose.PoseLandmark.RIGHT_KNEE, mp_pose.PoseLandmark.RIGHT_ANKLE),
        ]:
            knee = landmarks[knee_idx]
            ankle = landmarks[ankle_idx]

            if knee.visibility > confidence_threshold and ankle.visibility > confidence_threshold:
                dx = ankle.x - knee.x
                dy = ankle.y - knee.y

                extrapolated_x = ankle.x + dx * 0.5
                extrapolated_y = ankle.y + dy * 0.5

                fx = int(extrapolated_x * frame.shape[1])
                fy = int(extrapolated_y * frame.shape[0])
                foot_pts.append((fx, fy))

                cv2.circle(frame, (fx, fy), 4, (0, 165, 255), -1)
                cv2.putText(frame, "Foot (interpolated)", (fx + 5, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
            else:
                try_hip = True

        #as the last resort, try to interpolate the foot from the hip and knee, not as precise
        if try_hip:
            for hip_idx, knee_idx in [
                (mp_pose.PoseLandmark.LEFT_HIP, mp_pose.PoseLandmark.LEFT_KNEE),
                (mp_pose.PoseLandmark.RIGHT_HIP, mp_pose.PoseLandmark.RIGHT_KNEE),
            ]:
                hip = landmarks[hip_idx]
                knee = landmarks[knee_idx]

                if hip.visibility > confidence_threshold and knee.visibility > confidence_threshold:
                    vx = knee.x - hip.x
                    vy = knee.y - hip.y

                    est_x = knee.x + vx
                    est_y = knee.y + vy

                    fx = int(est_x * frame.shape[1])
                    fy = int(est_y * frame.shape[0])
                    foot_pts.append((fx, fy))

                    cv2.circle(frame, (fx, fy), 4, (0, 165, 255), -1)
                    cv2.putText(frame, "Foot (from hip→knee)", (fx + 5, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

    #localize the human from the direct or interpolated foot positions, otherwise use bounding box bottom in main
    if len(foot_pts) == 2:
        avg_fx = int((foot_pts[0][0] + foot_pts[1][0]) / 2)
        avg_fy = int((foot_pts[0][1] + foot_pts[1][1]) / 2)

        img_pt = np.array([avg_fx, avg_fy, 1.0])
        ground_pt = H @ img_pt
        ground_pt /= ground_pt[2]

        return float(ground_pt[0]), float(ground_pt[1])

    return None
