"""
00_capture_jpeg.py

This script captures a JPEG image using the Raspberry Pi's Picamera2 while the live preview is running.
It saves the captured image to a file and prints the associated metadata.

Key Features:

Requirements:
- Python 3
- picamera2 library
- Raspberry Pi with a compatible camera module

Constants:
- IMAGE_SIZE: Resolution of the captured image (default: 640x640).
- IMAGE_FILENAME: Output filename for the captured image.
"""

import time
from picamera2 import Picamera2, Preview
from config import IMAGE_SIZE, IMAGE_FILENAME

picam2 = Picamera2()

preview_config = picam2.create_preview_configuration(main={"size": IMAGE_SIZE})
picam2.configure(preview_config)

picam2.start_preview(Preview.QTGL)

picam2.start()
time.sleep(2)

metadata = picam2.capture_file(IMAGE_FILENAME)
print(metadata)
picam2.close()
