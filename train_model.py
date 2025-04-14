from ultralytics import YOLO
import torch
from config import *

def train_model():
    model = YOLO(MODEL_TYPE)

    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device='cuda' if torch.cuda.is_available() else 'cpu',
        lr0 =  0.0001
    )

    print("Training completed!")
    return model

if __name__ == "__main__":
    train_model()