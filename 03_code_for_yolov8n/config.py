"""
YOLOv8 Configuration File

This file stores all the global configuration settings used for training,
validation, and testing of the YOLOv8 model, including dataset paths, model type,
hyperparameters, and thresholds.

Modify the values here to adapt the pipeline to different datasets or training setups.
"""

import os

# Root path to the dataset directory
DATASET_PATH = "" #Give your path for the dataset

# Path to the YOLO data configuration YAML file
DATA_YAML = os.path.join(DATASET_PATH, "data.yaml")

# Path to the folder containing test images
TEST_IMAGES = os.path.join(DATASET_PATH, "test/images")

# YOLO model type to be used for training (e.g., yolov8n.pt, yolov8s.pt, etc.)
MODEL_TYPE = "yolov8n.pt"

# Path to the trained model weights (used for validation and testing)
TRAINED_MODEL = "runs/detect/train/weights/last.pt"

# Number of training epochs
EPOCHS = 5

# Image size to use during training and validation
IMGSZ = 640

# Batch size for training
BATCH = 8

# Confidence threshold for predictions during validation and testing
CONF_THRESHOLD = 0.5

#add some other variables, from train_model.py
#LR0=0.0001
#FREEZE=21
#last variable from validate_model.py
#FIGSIZE=(10, 5)