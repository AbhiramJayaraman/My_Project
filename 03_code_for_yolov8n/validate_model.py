"""
YOLOv8 Validation Script

This script performs validation of a trained YOLOv8 model using the Ultralytics API.
It loads the trained model, runs validation on the dataset defined in `config.py`,
and attempts to visualize validation losses (box loss and class loss) from the training logs.

To run this script independently:
    python validate_model.py
"""

from ultralytics import YOLO  # Import the YOLO model class
from config import *  # Import constants such as TRAINED_MODEL, DATA_YAML, CONF_THRESHOLD
import matplotlib.pyplot as plt  # For plotting validation loss
import pandas as pd  # For reading CSV logs

def validate_model():
    """
    Loads a trained YOLOv8 model and performs validation on the dataset.

    It uses the dataset path and confidence threshold from the `config.py` file.
    After validation, it tries to read and plot validation loss metrics from
    `runs/detect/train/results.csv`.

    Returns:
        None
    """
    # Load the trained model (path specified in config)
    model = YOLO(TRAINED_MODEL)

    # Run validation using dataset YAML and confidence threshold
    val_results = model.val(data=DATA_YAML, conf=CONF_THRESHOLD)

    try:
        # Try loading training/validation metrics from CSV file
        df = pd.read_csv("runs/detect/train/results.csv")

        # Plot validation loss curves
        plt.figure(figsize=(10, 5))#TODO: could you please include this in the corresponding config.py? just a small detail
        plt.plot(df["epoch"], df["val/box_loss"], label="Val Box Loss")
        plt.plot(df["epoch"], df["val/cls_loss"], label="Val Class Loss")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend()
        plt.show()

    except FileNotFoundError:
        # If the CSV is not found, inform the user
        print("Training log not found")

# If script is run directly, execute validation
if __name__ == "__main__":
    validate_model()
