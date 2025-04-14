from ultralytics import YOLO
from config import *
import matplotlib.pyplot as plt
import pandas as pd


def validate_model():
    model = YOLO(TRAINED_MODEL)


    val_results = model.val(data=DATA_YAML, conf=CONF_THRESHOLD)

    try:
        df = pd.read_csv("runs/detect/train/results.csv")
        plt.figure(figsize=(10, 5))
        plt.plot(df["epoch"], df["val/box_loss"], label="Val Box Loss")
        plt.plot(df["epoch"], df["val/cls_loss"], label="Val Class Loss")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend()
        plt.show()
    except FileNotFoundError:
        print("Training log not found")


if __name__ == "__main__":
    validate_model()