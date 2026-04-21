# config.py
#Default capture_jpeg.py constants
IMAGE_SIZE = (640,640)
IMAGE_FILENAME = "cam_pose.jpg"

IMAGE_FILENAME = "assets/cam_pose.jpg"
POINTS_FILENAME = "assets/points/selected_points.csv"
WINDOW_SIZE = (800, 600)
WIN_NAME = "Point Selector"

# Default detection parameters
CANNY_LOW = 100
CANNY_HIGH = 200
HOUGH_THRESHOLD = 50
MIN_LINE_LENGTH = 40
MAX_LINE_GAP = 10
CORNER_QUALITY = 0.01
CORNER_MIN_DISTANCE = 10

#HOMOGRAPHY CALCULATION
CAM_POINTS_PATH = "assets/points/selected_points.csv"
WORLD_POINTS_PATH = "assets/points/world_points.csv"
AVG_BEST_HOMOGRAPHY_PATH = "assets/homographies/homography_avg_best.npy"
PERCENTAGE_BEST_HOMOGRAPHIES = 0.3
COLINEARITY_THRESHOLD = 1e-5
