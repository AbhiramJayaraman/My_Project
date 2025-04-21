import os


DATASET_PATH = r"C:\Users\abhir\OneDrive\Desktop\Master_Project_SS25\Dataset Of AGV's\MOCAS.v1i"
DATA_YAML = os.path.join(DATASET_PATH, "data.yaml")
TEST_IMAGES = os.path.join(DATASET_PATH, "test/images")


MODEL_TYPE = "yolov8n.pt"
TRAINED_MODEL = "runs/detect/train/weights/last.pt"
EPOCHS = 50
IMGSZ = 640
BATCH = 8
CONF_THRESHOLD = 0.5
Data =11
D =12