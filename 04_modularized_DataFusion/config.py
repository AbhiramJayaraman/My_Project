# MQTT Settings
BROKER_ADDRESS = "egn-mqtt-01.westeurope-1.ts.eventgrid.azure.net"
PORT = 8883
TOPICS = ["devices/mocas/rpi1", "devices/mocas/rpi2", "devices/mocas/rpi3"]
FUSION_TOPIC = "devices/mocas/fused_tracks"

CLIENT_ID = "mqtt_fusion_subscriber"
USERNAME = "student2"
CERTFILE = "./student2.crt"
KEYFILE = "./student2.key"
CA_CERTS = None

# Fusion Parameters
POSITION_THRESHOLD = 20.0  # cm
COLOR_THRESHOLD = 254
FUSION_WINDOW = 0.5         # seconds, not used
MIN_CONFIDENCE = 0.1
TIME_THRESHOLD = 0.1        # seconds
MIN_AGE = 10

#Kalman Filter parameters
KALMAN_DT = 1.0
KALMAN_R_VALUE = 25.0
KALMAN_Q_POSITION = 1.0
KALMAN_Q_VELOCITY = 1.0
KALMAN_INITIAL_COVARIANCE = 500

LOG_FILE = "mqtt_fusion_log.txt"

#Parameters for map creation
MAP_LAYOUT = "final_grid_map.png",
# Grid map constants
IMG_WIDTH = 1400
IMG_HEIGHT = 1000
GRID_WIDTH_CM = 1000
GRID_HEIGHT_CM = 800
MARGIN_TOP = 100
MARGIN_RIGHT = 100
CM_TO_PX = 1  # 1 cm = 1 px in full resolution
