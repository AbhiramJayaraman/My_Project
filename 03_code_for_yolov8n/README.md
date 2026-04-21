# Code to train YOLOV8n network
## Subtitle
Re-training of Yolov8n from Ultralytics

## About
This repository contains a complete YOLOv8 training pipeline implemented using the Ultralytics framework. The system provides a modular approach to train, validate, and test YOLOv8 models with customizable configurations and easy-to-use command-line interface.
The pipeline is designed for object detection tasks and includes automated training workflows, validation metrics visualization, and comprehensive testing capabilities.

### Requirements
To run the system, you will need:

1. Python 3.8+ with pip package manager
2. CUDA-compatible GPU (optional but recommended for faster training)
3. YOLOv8-formatted dataset with corresponding data.yaml configuration
4. Ultralytics YOLOv8 package and dependencies

## Overview
### Folder structure
<pre>
├── config.py              # Centralized configuration file
├── main.py                # Control panel script with CLI interface
├── train_model.py         # Training pipeline implementation
├── validate_model.py      # Validation and metrics visualization
├── test_model.py          # Testing and prediction script
├── requirements.txt       # Python dependencies
├── data.yaml              # Dataset configuration (user-provided)
├── runs/                  # Training outputs and results
│   └── detect/
│       ├── train/         # Training logs and weights
│       └── predict*/      # Prediction results
└── README.md   
</pre>
#### Code files
The codebase is organized into the following modules:
- `config.py`: Centralized configuration management containing all hyperparameters, paths, and training settings
- `main.py`: Command-line control panel allowing selective execution of training, validation, and testing phases
- `train_model.py`: Core training implementation with transfer learning capabilities and GPU support
- `validate_model.py`: Model validation with automatic metrics visualization and loss curve plotting
- `test_model.py`: Testing pipeline for running predictions on test datasets with result visualization
- `requirements.txt`: Python package dependencies for the entire pipeline
- `convert_yolo.py`: Python file to convert the yolo model into .zip format, which is then afterwards converted to .rpk.

## Usage instructions
-Running the Complete Pipeline
The main control panel script allows you to run different phases of the pipeline:
bash
1. Run all phases (training, validation, and testing)
   python main.py --train --val --test

2. Run only training
   python main.py --train

3. Run validation and testing
   python main.py --val --test

4. Run individual phases
   python main.py --val
   python main.py --test

## Configuration Setup
1. Edit config.py to match your dataset and training requirements:
     - Set DATASET_PATH to your dataset root directory
     - Configure DATA_YAML path to your YOLO dataset configuration
     - Adjust hyperparameters like EPOCHS, BATCH, IMGSZ, etc.
     - Set confidence thresholds and model types

2. Prepare your dataset in YOLO format with proper data.yaml configuration
3. Run the pipeline using the control panel or individual scripts


### Troubleshooting error messages
1. Training Issues
    .CUDA out of memory: Reduce BATCH size in config.py
    .Dataset not found: Verify DATASET_PATH and DATA_YAML paths are correct
    .Model loading errors: Ensure the specified MODEL_TYPE is valid (e.g., yolov8n.pt, yolov8s.pt)

2. Validation Issues
    .Results CSV not found: Run training first to generate the results file
    .Plotting errors: Ensure matplotlib is properly installed and configured

3. Testing Issues
    .No test images: Verify TEST_IMAGES path contains valid image files
    .Prediction folder not found: Run prediction with save=True to generate output folder

### Recommendations
- GPU Usage: Enable CUDA for significantly faster training times
- Transfer Learning: The pipeline uses frozen layers (first 21) for effective transfer learning
- Batch Size: Start with smaller batch sizes and increase based on available GPU memory
- Monitoring: Use the validation loss plots to monitor training progress and detect overfitting
- Testing: Regularly test on held-out data to evaluate model performance
- Optimizer Selection: Use optimizer=auto in training configuration to let Ultralytics automatically select the best optimizer   and learning rate(which is given as default by ultralytics)

## Installation instructions
### PIP Installation of Requirements
Create a virtual environment using:
```
python3 -m venv venv --system-site-packages source venv/bin/activate
```
Then install dependencies with:
```
pip install -r requirements.txt
```
### Installation of Other Libraries and Packages
The main dependencies include:
 - ultralytics: YOLOv8 framework
 - torch: PyTorch deep learning framework
 - matplotlib: Plotting and visualization
 - pandas: Data manipulation for metrics
 - opencv-python: Computer vision utilities

## Dataset Preparation
1. Format your dataset in YOLO format with the following structure:
dataset/
├── data.yaml
├── train/
│   ├── images/
│   └── labels/
├── val/
│   ├── images/
│   └── labels/
└── test/
    └── images/
2. Configure data.yaml with proper paths and class names

## Development instructions
1. config.py Functionality
    The configuration file centralizes all settings including dataset paths, model parameters, training hyperparameters, and   thresholds. This modular approach allows easy experimentation with different configurations without modifying the core code.
2. main.py Functionality
    Implements a command-line interface using argparse to selectively run different pipeline phases. The script imports and calls functions from individual modules based on user-specified flags, providing flexibility in pipeline execution.
3. train_model.py Functionality
     Contains the core training logic using Ultralytics YOLO API. Features include:
       - Automatic GPU detection and utilization
       - Transfer learning with frozen layers
       - Configurable hyperparameters
       - Training progress monitoring
       - Automatic optimizer selection: Uses optimizer=auto which automatically determines the best optimizer, learning rate, and momentum based on the model and dataset
4. validate_model.py Functionality
     Handles model validation and performance visualization:
       - Loads trained model weights
       - Runs validation on specified dataset
       - Generates loss curves and metrics plots
       - Handles missing results files gracefully

5. test_model.py Functionality
    Implements the testing pipeline:
       - Loads trained model for inference
       - Runs predictions on test images
       - Saves prediction results
       - Displays sample predictions for visual inspection


## Known shortfalls
1. Fixed freeze layers: Currently freezes first 21 layers, which may not be optimal for all datasets
2. Limited hyperparameter tuning: Some advanced hyperparameters are not exposed in the configuration

## YOLO model conversion
This section aims to walk the user through the procedure necessary to convert a YOLO v8n model to the IMX format, suitable for the Raspberry Pi AI camera, to then run object detection directly on the device.

### Installation
Note that this process must be run on a Linux computer, it does not work on a Windows device.
1. Paste a representative part of the training dataset into the same directory as the code being run. This is fundamental to achieve a good performing compressed model.
2. Install the latest version of ultralytics
```
bash
pip install --upgrade ultralytics numpy
```
### Running the model export on LINUX computer
1. Use the following code snippet to export your trained YOLOv8n model (last.pt) to IMX format:
```
python
from ultralytics import YOLO

model = YOLO("last.pt")
model.export(format="imx")

imx_model = YOLO("yolov8n_imx_model")
```
This process will create a folder or .zip archive (named `packerOut.zip` containing the exported model. Remember that this code must be run on a linux computer
### Finishing the model export in the target RPI
For the second part of the model export, an RPI must be used.
1. Install the required packages
```
bash
(install picamera2, see other readmes)
```
2. Finish the conversion to .rpk format using the `imx500-package`tool. The resulting model wil be saved into a newly created directory, already compatible with the RPI AI camera.
```
bash
imx500-package -i path/to/packerOut.zip -o path/to/output/folder
```

### Further information
This method to compress the model was natively supported by Ultralytics, and as such is to be found in their [repository](https://github.com/ultralytics/ultralytics):

However, after the release of YOLO v11, Ultralytics has since adapted the document to YOLO v11. However, the past documentation can be found in the following commit: `f932a611abf0ed0e359deecbb82fa8d361e23cfe´.
Additionally, this [webpage](https://docs.ultralytics.com/de/integrations/sony-imx500/) contains detailed information on how to run the given code, with all the relevant parameters.
