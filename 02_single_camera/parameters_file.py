"""
parameters_file.py

Centralized configuration module for the object detection and tracking pipeline.

This file defines constants for all major components using `SimpleNamespace`,
grouped by functional area (main, detection, location, mqtt_client, pose, tracking).
It allows consistent and modular access to shared parameters across the project.

To switch between Raspberry Pi devices, update the `RPI_FLAG` value (1 or 2),
which controls MQTT client identity, certificates, and topic configuration.
"""
from types import SimpleNamespace

#----------------------------
#constants from main.py
#----------------------------
main = SimpleNamespace(
    MODEL_FILE = "assets/networks/yolov8n_3.rpk",
    DEFAULT_FPS = 24,
    CONFIDENCE_THRESHOLD = 0.2,
    DEFAULT_IOU = 0.65,
    MAX_DETECTIONS = 30,
    LABELS_FILE = "assets/networks/labels_v3.txt",
    DEFAULT_BBOX_ORDER = "xy",
    IMAGE_SIZE = (640,640),
    BUFFER_COUNT = 12,
    PROCESSES = 4,
    USE_MAP = True
)
#----------------------------
#constants from detection.py
#----------------------------
detection = SimpleNamespace(
    AVG_COLOR_KERNEL_SIZE = 10
)
#----------------------------
#constants from location.py
#----------------------------
location = SimpleNamespace(
    HOMOGRAPHY_PATH = "assets/homography.npy",
    MAP_LAYOUT = "assets/final_grid_map.png",
    # Grid map constants
    IMG_WIDTH = 1400,
    IMG_HEIGHT = 1000,
    GRID_WIDTH_CM = 1000,
    GRID_HEIGHT_CM = 800,
    MARGIN_TOP = 100,
    MARGIN_RIGHT = 100,
    CM_TO_PX = 1  # 1 cm = 1 px in full resolution
)
#----------------------------
# constants from mqtt_client
#----------------------------
RPI_FLAG = 1
FREQUENCY = 1  # Hz
mqtt_client = SimpleNamespace(
    CERTFILE = f"assets/mqtt/student{RPI_FLAG}.crt",
    KEYFILE = f"assets/mqtt/student{RPI_FLAG}.key",
    CA_CERTS = None,
    BROKER_ADDRESS = 'egn-mqtt-01.westeurope-1.ts.eventgrid.azure.net',
    PORT = 8883,
    TOPIC = f"devices/mocas/rpi{RPI_FLAG}",
    CLIENT_ID = f"rpi-{RPI_FLAG:02d}",
    USERNAME = f"student{RPI_FLAG}",
    INTERVAL = 1.0 / FREQUENCY
)

#----------------------------
#constants from pose.py
#----------------------------
pose = SimpleNamespace(
    GENERAL_CONFIDENCE_THRESHOLD = 0.6,
    KNEE_CONFIDENCE_THRESHOLD = 0.6,
    HIP_CONFIDENCE_THRESHOLD = 0.6,
    FOOT_CONFIDENCE_THRESHOLD = 0.6
)
#----------------------------
#constants from tracking.py
#----------------------------
tracking = SimpleNamespace(
    MAX_AGE = 240,  # max number of frames to keep stale tracks
    TRACK_THRESH = 0.4,
    MATCH_THRESH = 0.8,
    MOT20 = False,
    LOW_THRESH = 0.1,
    FRAME_RATE = 24,
    IOU_THRESHOLD = 0.5
)

#----------------------------
#creating the config variable to import
#----------------------------
configuration = SimpleNamespace(
    main = main,
    location = location,
    mqtt_client = mqtt_client,
    pose = pose,
    tracking = tracking,
    detection = detection
    )
