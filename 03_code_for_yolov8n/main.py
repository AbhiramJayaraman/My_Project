"""
YOLOv8 Training Control Panel Script

This script allows the user to selectively run the training, validation, and testing
pipelines for a YOLOv8 model via command-line arguments.

Usage:
    python control_panel.py --train --val --test

Arguments:
    --train    Run the training pipeline by calling train_model()
    --val      Run the validation pipeline by calling validate_model()
    --test     Run the testing pipeline by calling test_model()

The user can combine these flags as needed. If a flag is omitted, its corresponding
step will be skipped.
"""

import argparse
from train_model import train_model  
from validate_model import validate_model  
from test_model import test_model  

def main():
    # Create an ArgumentParser object to handle command-line arguments
    parser = argparse.ArgumentParser(description="YOLOv8 Training Control Panel")

    # Define flags for train, val, and test
    parser.add_argument("--train", action="store_true", help="Run training")
    parser.add_argument("--val", action="store_true", help="Run validation")
    parser.add_argument("--test", action="store_true", help="Run testing")

    # Parse the command-line arguments
    args = parser.parse_args()

    # If --train flag is set, run training
    if not args.train:
        print("Starting training...")
        train_model()  # Call the training function
    else:
        print("Skipping training (use --train to enable)")

    # If --val flag is set, run validation
    if not args.val:
        print("\nStarting validation...")
        validate_model()  # Call the validation function

    # If --test flag is set, run testing
    if not args.test:
        print("\nStarting testing...")
        test_model()  # Call the testing function

# Entry point of the script
if __name__ == "__main__":
    main()


