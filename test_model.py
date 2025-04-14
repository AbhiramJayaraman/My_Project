from ultralytics import YOLO
from config import *
import matplotlib.pyplot as plt
import glob
import os


def test_model():
    model = YOLO(TRAINED_MODEL)

    results = model.predict(source=TEST_IMAGES, save=True, conf=CONF_THRESHOLD)

    pred_dir = glob.glob("runs/detect/predict*")[-1]
    images = glob.glob(os.path.join(pred_dir, "*.jpg"))[:5]

    for img_path in images:
        img = plt.imread(img_path)
        plt.imshow(img)
        plt.axis('off')
        plt.title("Prediction (Close to continue)")
        plt.show()



