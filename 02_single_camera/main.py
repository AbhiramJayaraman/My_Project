"""
main.py

Entry point for the real-time human tracking system using the IMX500 camera.

This script performs the following tasks:
- Initializes the IMX500 neural network and loads object detection intrinsics.
- Captures frames using Picamera2 and processes them with a detection model.
- Tracks detected objects using BYTETracker.
- Uses MediaPipe Pose to estimate more accurate foot positions.
- Projects positions onto a ground plane using a homography matrix.
- Sends position data via MQTT to a central server.
- Displays live annotated camera feed alongside a top-down map view.

Threads:
- One thread draws detections and tracks on frames.
- One thread sends selected tracking data to MQTT.

Requirements:
- Properly configured `parameters_file.py` and all required certificate files.
"""


import argparse
import multiprocessing
import threading
import queue
import time
import sys

import numpy as np
import cv2

from picamera2 import Picamera2, MappedArray
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics
from functools import lru_cache

# === Imports from our custom modules ===
from detection import get_labels_cached, draw_detection_label, average_color_at_center, get_detection_position,draw_roi,resize_map_to_match
from tracking import tracker, detections_to_bytetracker_format, update_track_metadata, track_metadata, track_age
from pose import pose_estimator
from location import compute_homography, estimate_ground_position, create_map_background, draw_map_view
from mqtt_client import mqtt_sender_thread, update_track_storage
from parameters_file import configuration


class Detection:
    """Detection object to hold bounding box and classification results."""

    def __init__(self, coords: np.ndarray, category: int, conf: float, metadata: dict) -> None:
        """
        Args:
            coords (np.ndarray): Coordinates of detection box.
            category (int): Detected class category.
            conf (float): Confidence score.
            metadata (dict): Metadata from the camera/detection pipeline.
        """
        self.category = category
        self.conf = conf
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)


def parse_detections(metadata: dict) -> list[Detection] | None:
    """
    Parse detection results from model metadata.

    Args:
        metadata (dict): Metadata returned from capture request.

    Returns:
        list[Detection] | None: List of Detection objects if detections found, else None.
    """
    bbox_normalization = intrinsics.bbox_normalization
    bbox_order = intrinsics.bbox_order
    threshold = args.threshold
    iou = args.iou
    max_detections = args.max_detections

    np_outputs = imx500.get_outputs(metadata, add_batch=True)
    input_w, input_h = imx500.get_input_size()
    if np_outputs is None:
        return None
    if intrinsics.postprocess == "nanodet":
        boxes, scores, classes = \
            postprocess_nanodet_detection(outputs=np_outputs[0], conf=threshold, iou_thres=iou,
                                          max_out_dets=max_detections)[0]
        from picamera2.devices.imx500.postprocess import scale_boxes
        boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
    else:
        boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]
        if bbox_normalization:
            boxes = boxes / input_h
        if bbox_order == "xy":
            boxes = boxes[:, [1, 0, 3, 2]]
        boxes = np.array_split(boxes, 4, axis=1)
        boxes = zip(*boxes)

    detections = [
        Detection(box, category, score, metadata)
        for box, score, category in zip(boxes, scores, classes)
        if score > threshold
    ]
    return detections


def draw_detections(jobs: queue.Queue) -> None:
    """
    Thread worker function to draw detections, estimate poses, update tracking and show combined camera/map view.

    Args:
        jobs (queue.Queue): Queue of jobs, each is a tuple of (request, async_result).
    """
    last_pose_time = 0
    POSE_INTERVAL = 0.2
    last_detections = []
    labels = get_labels_cached(tuple(intrinsics.labels), intrinsics.ignore_dash_labels)

    while (job := jobs.get()) is not None:
        request, async_result = job
        detections = async_result.get() or last_detections
        last_detections = detections

        with MappedArray(request, 'main') as m:
            frame = m.array
            h, w, _ = frame.shape
            (input_h, input_w) = configuration.main.IMAGE_SIZE
            run_pose = (time.time() - last_pose_time) >= POSE_INTERVAL

            if configuration.main.USE_MAP:
                map_img, scalemap = create_map_background(scale=0.5)

            # === TRACKING ===
            tracker_input = detections_to_bytetracker_format(detections)
            tracks = tracker.update(tracker_input, img_info=(h, w), img_size=(input_h, input_w))
            update_track_metadata(tracks, detections, labels)

            for track in tracks:
                track_id = track.track_id
                x, y, w, h = map(int, track.tlwh)
                bbox = (x, y, w, h)

                #creation of labels kept in draw_detections to avoid dealing with possible threading issues
                meta = track_metadata.get(track_id, {})
                label_name = meta.get("label", "unknown")
                conf = meta.get("conf", 0.0)
                label = f"{label_name} ({conf:.2f} ID: {track_id})"
                draw_detection_label(frame, label, bbox)

                avg_color = average_color_at_center(frame, bbox)

                used_pose = False
                person_crop = frame[y:y + h, x:x + w]
                results = None
                if label_name.lower() == "person" and run_pose and person_crop.size > 0:
                    results = pose_estimator.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    last_pose_time = time.time()

                position, used_pose = get_detection_position(
                    label_name,
                    results,
                    bbox,
                    frame,
                    H,
                    estimate_ground_position
                )

                if configuration.main.USE_MAP:
                    map_img = draw_map_view(map_img, position, label, scalemap)

                update_track_storage(track_id, label, conf, position, avg_color, used_pose) #save data for MQTT communication

            if intrinsics.preserve_aspect_ratio:
                roi = imx500.get_roi_scaled(request)
                draw_roi(frame, roi)

            if configuration.main.USE_MAP:
                map_img = resize_map_to_match(frame, map_img)
                combined = np.hstack((frame, map_img))
            else:
                combined = frame

            cv2.imshow('Camera + Map View', combined)
            cv2.waitKey(1)

        request.release()


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=configuration.main.MODEL_FILE)
    parser.add_argument("--fps", type=int, default=configuration.main.DEFAULT_FPS)
    parser.add_argument("--bbox-normalization", default=True, action=argparse.BooleanOptionalAction)
    parser.add_argument("--threshold", type=float, default=configuration.main.CONFIDENCE_THRESHOLD)
    parser.add_argument("--iou", type=float, default=configuration.main.DEFAULT_IOU)
    parser.add_argument("--max-detections", type=int, default=configuration.main.MAX_DETECTIONS)
    parser.add_argument("--ignore-dash-labels", action=argparse.BooleanOptionalAction)
    parser.add_argument("--postprocess", choices=["", "nanodet"], default=None)
    parser.add_argument("-r", "--preserve-aspect-ratio", action=argparse.BooleanOptionalAction)
    parser.add_argument("--labels", type=str, default=configuration.main.LABELS_FILE)
    parser.add_argument("--print-intrinsics", action="store_true")
    parser.add_argument("--bbox-order", choices=["yx", "xy"], default=configuration.main.DEFAULT_BBOX_ORDER,
                        help="Set bbox order yx -> (y0, x0, y1, x1) xy -> (x0, y0, x1, y1)")
    return parser.parse_args()


if __name__ == "__main__":
    """
    Entry point for real-time detection, tracking, and localization using the IMX500 camera.

    This script:
    - Loads command-line arguments and configures IMX500 network intrinsics.
    - Validates and loads label files.
    - Initializes the Picamera2 pipeline with the configured image size and frame rate.
    - Starts multiprocessing for detection parsing.
    - Starts a drawing thread for detections and pose estimation.
    - Starts a background MQTT thread to publish tracking data.
    - Continuously captures frames and dispatches detections to the worker pool.

    Exits cleanly on KeyboardInterrupt.
    """
    H = compute_homography()
    args = get_args()

    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics

    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"
        print("inside the not intrinsics code logic")
    elif intrinsics.task != "object detection":
        print("Network is not an object detection task", file=sys.stderr)
        exit()

    for key, value in vars(args).items():
        if key == 'labels' and value is not None:
            with open(value, 'r') as f:
                intrinsics.labels = f.read().splitlines()
        elif hasattr(intrinsics, key) and value is not None:
            setattr(intrinsics, key, value)

    if intrinsics.labels is None:
        raise RuntimeError("Failed to load labels: no label file specified and 'intrinsics.labels' is None.")
    intrinsics.update_with_defaults()

    if args.print_intrinsics:
        print(intrinsics)
        exit()

    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration({'format': 'RGB888', 'size': configuration.main.IMAGE_SIZE},
                                                  controls={"FrameRate": intrinsics.inference_rate}, buffer_count=configuration.main.BUFFER_COUNT)
    imx500.show_network_fw_progress_bar()
    picam2.start(config, show_preview=False)

    if intrinsics.preserve_aspect_ratio:
        imx500.set_auto_aspect_ratio()

    pool = multiprocessing.Pool(processes=configuration.main.PROCESSES)
    jobs = queue.Queue()

    thread = threading.Thread(target=draw_detections, args=(jobs,))
    thread.start()
    # MQTT data sending
    mqtt_thread = threading.Thread(target=mqtt_sender_thread)
    mqtt_thread.daemon = True
    mqtt_thread.start()

try:
    while True:
        request = picam2.capture_request()
        metadata = request.get_metadata()
        if metadata:
            async_result = pool.apply_async(parse_detections, (metadata,))
            jobs.put((request, async_result))
        else:
            request.release()
except KeyboardInterrupt:
    print("\nExiting main object detection program")
    pool.close()   # Prevents more tasks from being submitted
    pool.join()    # Waits for worker processes to finish cleanly
    cv2.destroyAllWindows()


