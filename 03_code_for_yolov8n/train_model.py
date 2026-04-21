"""
YOLOv8 Training Script

This script initializes a YOLOv8 model using Ultralytics' API and trains it based
on parameters defined in a separate configuration file (`config.py`).

It uses GPU if available, otherwise falls back to CPU. 
The model and training configuration are customizable through the config variables.

To run this script independently:
    python train_model.py
"""

from ultralytics import YOLO  
import torch  
from config import *  
def train_model():
    """
    Initializes and trains a YOLOv8 model using Ultralytics' API.

    The training parameters such as model type, dataset path, number of epochs,
    image size, and batch size are imported from the `config.py` file.

    The training runs on GPU if available, otherwise on CPU.
    The first 21 layers of the model are frozen (useful for transfer learning).

    Returns:
        YOLO: A trained YOLO model instance that can be used for validation, testing,
              or saving to disk.
    """
    # Initialize the YOLO model 
    model = YOLO(MODEL_TYPE)

    # Start training with the specified configuration
    results = model.train(
        data=DATA_YAML,                      
        epochs=EPOCHS,                       
        imgsz=IMGSZ,                         
        batch=BATCH,                        
        device='cuda' if torch.cuda.is_available() else 'cpu',  
        lr0=0.0001,   #TODO: could you set this in config.py please?
        freeze=21, # Freeze first 21 layers (useful for transfer learning) #TODO: same for this variable please, otherwise all good
    )

    print("Training completed!")
    return model  

# If script is run directly, execute training
if __name__ == "__main__":
    train_model()
