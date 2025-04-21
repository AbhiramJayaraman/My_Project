import argparse
from train_model import train_model
from validate_model import validate_model
from test_model import test_model


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Training Control Panel")

    parser.add_argument("--train", action="store_true", help="Run training")
    parser.add_argument("--val", action="store_true", help="Run validation")
    parser.add_argument("--test", action="store_true", help="Run testing")

    args = parser.parse_args()

    if  args.train:
        print("Starting training...")
        train_model()
    else:
        print(" Skipping training (use --train to enable)")


    if   args.val:
        print("\n Starting validation...")
        validate_model()

    if  args.test:
        print("\n Starting testing...")
        test_model()


if __name__ == "__main__":
    main()

ffvbbbbbbbbbbbbbbbbbb