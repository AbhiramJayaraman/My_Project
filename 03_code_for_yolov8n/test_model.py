"""
YOLOv8 Testing Script

This script loads a trained YOLOv8 model and runs predictions on a folder of test images
defined in the `config.py` file. It saves the prediction results and displays a few of them
using matplotlib.

To run this script independently:
    python test_model.py
"""

from ultralytics import YOLO  # Import the YOLO model class
from config import *  # Import configuration constants like TRAINED_MODEL, TEST_IMAGES, CONF_THRESHOLD
import matplotlib.pyplot as plt  # For displaying predicted images
import glob  # For file pattern matching
import os  # For file path handling

def test_model():
    """
    Runs prediction using a trained YOLOv8 model on test images.

    The test images folder and model path are defined in `config.py`.
    After prediction, the latest prediction output directory is located, and
    the first 5 predicted images are displayed using matplotlib.

    Returns:
        None
    """
    # Load the trained YOLO model
    model = YOLO(TRAINED_MODEL)

    # Run predictions on the test image folder with saving enabled
    results = model.predict(source=TEST_IMAGES, save=True, conf=CONF_THRESHOLD)

    # Find the most recent prediction folder (e.g., runs/detect/predict3)
    pred_dir = glob.glob("runs/detect/predict*")[-1]

    # Get paths of the first 5 predicted images
    images = glob.glob(os.path.join(pred_dir, "*.jpg"))[:5]

    # Display each image one by one
    for img_path in images:
        img = plt.imread(img_path)
        plt.imshow(img)
        plt.axis('off')  # Hide axes
        plt.title("Prediction (Close to continue)")
        plt.show()

# If the script is executed directly, run testing
if __name__ == "__main__":
    test_model()



