# Datafusion code

## About
This repository contains the complete codebase for a real-time multi-camera object tracking and data fusion system that combines tracking data from multiple Raspberry Pi cameras into globally consistent tracks. The system receives object tracking data via MQTT from up to 3 Raspberry Pi cameras equipped with Sony IMX500 AI camera modules, performs intelligent data fusion to create global object tracks, and publishes fused results for real-time visualization and analysis.

The system handles track matching across different camera viewpoints, maintains global track IDs for consistent object identification, and provides robust operation even with intermittent camera failures.



### Requirements
To run the system, you will need:
  1. MQTT Broker
      - Active MQTT broker (e.g., Azure Event Grid, Mosquitto)
      - Valid TLS certificates (.crt and .key files)
      - Broker address, port, and authentication credentials
  2. Tracking Sources
      - 1-3 Raspberry Pi units running object detection
      - Configured to publish to specified MQTT topics
      - JSON payloads containing:
         - Object positions (x,y in cm)
         - Object labels and confidence scores
         - Color information (BGR format)
         - Timestamps
  3. Visualization
      - Floor plan image (final_grid_map.png)
      - Grid dimensions matching your physical space

## Key Features
- **Multi-Camera Fusion**: Combines data from up to 3 Raspberry Pi cameras
- **Global Tracking**: Maintains consistent object IDs across different camera views
- **Real-time Visualization**: Displays object positions on a floor plan map
- **Robust Operation**: Handles missing or intermittent camera data gracefully
- **Secure Communication**: Uses TLS encryption for MQTT communication
- **Temporal Fusion Window**: Aggregates tracks within a configurable time window to synchronize multi-camera fusion
- **Kalman Filtering**: Smooths fused track positions using 2D Kalman filtering for noise reduction and velocity continuity
- **Minimum Track Age Filtering**: Ignores newly detected tracks until they reach a stable age threshold (avoids flickering)


## Overview
### Folder structure
<pre>
├── config.py # Configuration parameters
├── fusion_engine.py # Core data fusion algorithm
├── fusion_map.py # Map visualization functions
├── main.py # Main entry point
├── publisher.py # MQTT publishing functions
├── subscriber.py # MQTT subscription and message handling
├── final_grid_map.png # Floor plan visualization
├── mqtt_fusion_log.txt # Log file of all fusion activities
├── student2.crt # MQTT TLS certificate
├── student2.key # MQTT private key
├── requirements.txt # all installation
└── README.md # This documentation file
</pre>
#### Code files
1. subscriber.py
    - Listens to 3 RPI cameras via MQTT
    - Introduces a `fusion_window` to collect messages (only fusion process starts when window is closed or expired)
    - Receives object positions (JSON format)
    - Starts data fusion process
2. fusion_engine.py
    - Matches objects across cameras
    - Combines positions/colors
    - Creates global track IDs
    - Used Kalman filter for tracking
    - Handles 1-3 camera scenarios
3. fusion_map.py
    - Shows real-time map
    - Plots camera data (color-coded)
    - Displays fused tracks (red)
4. publisher.py
    - Sends fused data via MQTT
    - Logs all activity
    - Handles empty states
5. config.py
    - Stores all settings:
    - MQTT connection
    - Fusion rules
    - Map dimensions
6. main.py
    - Starts the system
    - Manages connections
    - Handles shutdown

#### Assets
final_grid_map, mqtt (certificate and key)

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
### Download of Asset Files
Make sure the following resources are in place:
-  Put MQTT Certificates and keys in the folder `04_modularized_DataFusion`
-  Put `test.png` inside the same folder 

## Usage instructions
### Running the code
1. Place these in the same folder:
     - student2.crt (MQTT certificate)
     - student2.key (MQTT private key)
     - final_grid_map.png (floor plan image)
2. Configure (Edit config.py to match your:)
     - MQTT broker address
     - Room dimensions
     - Topics to subscribe to	 
3. Run the System
     - python main.py
### Troubleshooting error messages
1. Connection Errors
    - Invalid MQTT credentials or certificates
2. Data Processing Errors
    - Malformed MQTT messages
3. KeyError: 'position'
    - Missing field in incoming data
4. Visualization Errors
5. Certificate Errors

### Recommendations
- Dedicate 5GHz WiFi or wired Ethernet
- Recalibrate homography if cameras move
- Ensure publishing from all camera is synchronized
- Position Threshold - Start with 20cm, increase if missing matches, decrease for crowded scenes
- Color Threshold - Set based on lighting conditions (lower for stable lighting)
- Time Threshold - Match to camera FPS
- Set `MIN_AGE` to at least 2-3 frames to suppress noise from transient detections


## Development instructions
### subscriber.py functionality

This script acts as a central MQTT subscriber, receiving live tracking data from multiple Raspberry Pi devices and fusing them into a unified global view. It also provides visual feedback by displaying a map with raw and fused positions and publishes the results onward.

**Key Functional Areas**
- Subscribes to multiple MQTT topics (e.g., rpi1, rpi2, rpi3).
- Collects object tracking data and temporarily buffers it.
- Uses a short fusion window to synchronize incoming data.
- Calls the fusion engine to combine overlapping tracks.
- Publishes fused results to an MQTT topic and logs them for inspection.
- Provides a map visualization showing both raw and fused track positions.

**Function Summaries:**

### `on_message()`
- Central callback for handling incoming MQTT messages.
- Decodes JSON payloads, stores per-RPI data, and checks if the fusion window has elapsed.
- If conditions are met, runs full fusion pipeline and visualization.

### `run_data_fusion()`
- Calls fusion_engine.add_track_data() for each RPI.
- Triggers the fuse_tracks() method to generate globally consistent tracks.

### `draw_raw_tracks_on_map()` and  `draw_fused_tracks_on_map()`
- Annotates a static map image with positions from each RPI (color-coded) or fused outputs (in red).
- Used for visual debugging and user feedback.

### `process_track_data()`
- Prepares and formats incoming track data.
- Extracts fields like timestamp, label, position, color, and whether pose estimation was used.
- Converts timestamps to human-readable format.

### `print_fused_tracks()`
- Logs the full list of fused tracks in the console.
- Includes which RPIs contributed to each global ID and their individual timestamps.

### `setup_mqtt_client()`
- Creates and configures a secure MQTT client using TLS.
- Registers all required MQTT callbacks (on_connect, on_message, etc.).
- Credentials and certificate paths are loaded from the config file.

### `show_or_save_map()`
- Displays the annotated map using OpenCV.
- In case of headless environments, saves a fallback PNG file.

### fusion_engine.py functionality 

This module performs multi-camera data fusion to combine and smooth object tracks across multiple Raspberry Pi cameras. It generates globally consistent object IDs, filters noisy detections, and improves spatial accuracy using Kalman filtering

**Key Functional Areas:**
- Collects and stores per-camera track data from up to 3 RPI clients.
- Matches and fuses detections from different cameras into single global tracks.
- Applies minimum age filtering to reduce flickering tracks from transient detections.
- Uses a 2D Kalman Filter to smooth global position estimates over time.
- Maintains track continuity even during camera dropout or when objects move between cameras

**Function Summaries:**

### `add_track_data(rpi_id, track_data)`
- Collects incoming data from each Raspberry Pi.
- Increments an age counter for each local track.
- Supports empty inputs to signal "active but no detection".

### `fuse_tracks()`
- Main method that runs the fusion pipeline.
- Returns a dictionary of fused global tracks with positions, colors, and IDs.
- Applies a three-phase strategy:
    1.  RPI1 as reference, match with RPI2/RPI3.
    2.  RPI2 unmatched tracks, match with RPI3.
    3.  Remaining RPI3 tracks are added independently.

### `create_fused_track(global_id, all_tracks, reference_data)`
- Computes the average position, color, and confidence across matched tracks.
- Applies Kalman filtering for smoother trajectory estimation.
- Returns a unified fused track dictionary.

### `find_matching_previous_global_id(source_tracks)`
- Ensures ID continuity by comparing current source tracks to previous frame associations.
- Avoids unnecessary creation of new global IDs.

### `calculate_distance()` and `calculate_color_difference()`
- Utility functions to measure spatial and appearance similarity between tracks.

### `Kalman2D class`
- Implements a lightweight 2D Kalman filter for position smoothing.
- Initialized per global track and reused across frames.

### publisher.py functionality

This module handles the final step of the multi-camera tracking pipeline: it publishes fused object tracks via MQTT and maintains a log of all tracking events for post-analysis and debugging. It ensures timely and reliable dissemination of object presence/absence to all connected subscribers

**Key Functional Areas:**
- Publishes fused object tracks to a central MQTT topic.
- Handles both active tracking data and empty state notifications (no detections).
- Logs both raw incoming RPI tracks and fused outputs to a persistent file.
- Provides detailed status feedback, publishing diagnostics, and error tracing.

**Function Summaries:**

### `publish_fused_data(client, fused_tracks)`
- Publishes real-time tracking results to the MQTT fusion topic (from config.FUSION_TOPIC).
- Always publishes a message, even when no objects are detected.
- Payload contains:
    - Current timestamp
    - Status: "active" or "no_tracks"
    - List of fused objects (with global ID, label, position, color, confidence, source RPIs)
- Publishes with QoS 1 to ensure reliable delivery.
- Prints publishing diagnostics to the console for verification:
    - Number of tracks
    - Payload size
    - Publishing result and return code

### `log_message(topic, rpi_id, payload_dict, fused_tracks)`
- Logs all tracking activity to a local file (defined in config.LOG_FILE).
- Each log entry includes:
     - Time of reception
     - Source RPI and topic name
     - Full raw track data per RPI
     - Fused results with global IDs and metadata
     - Summary of whether a publish event occurred or was skipped
- Provides a complete audit trail of incoming and outgoing tracking data.

### fusion_map.py functionality

This module handles visual rendering of object positions onto a pre-annotated map of the environment. It is used for debugging, visualization, and real-time monitoring of object positions after detection and data fusion.

**Key Functional Areas:**
- Loads a floor plan image with pre-drawn grid and axis labels.
- Converts ground-plane positions (in centimeters) to pixel coordinates on the map.
- Annotates the map image with colored dots and labels for tracked objects.
- Supports scaling to fit visualization windows or headless saves.

**Function Summaries:**
### `create_map_background(scale=0.5, path="final_grid_map.png")`
- Loads a map image from disk and resizes it based on a user-defined scale.
- The image typically includes:
    - Pre-drawn axes
    - Grid aligned to world coordinates
    - Static background showing room layout
- Returns:
    - Scaled image (map_img)
    - Actual scale factor used (scale)
- Raises an error if the map image is not found.

### `draw_map_view(map_img, position_cm, label_name, colour, scale=0.5)`
- Plots a point (object) at the given real-world position in centimeters.
- Internally:
    - Converts (x_cm, y_cm) to full-resolution pixel coordinates.
    - Adjusts for top/right margins and grid origin.
    - Scales pixel coordinates to match the resized image.
- Draws:
    - A small circle representing the object.
    - A label (name + coordinates) next to the circle.
    - Automatically wraps long labels onto two lines if needed.
- Inputs:
    - position_cm: A tuple (x_cm, y_cm) in world coordinates
    - label_name: Text to be shown next to the dot (e.g., "person")
    - colour: A BGR tuple for dot color (e.g., (0, 0, 255) for red)
    - scale: Should match the one used when loading the map
- Returns the modified map_img with annotations.

### config.py functionality

This file centralizes all configuration parameters for the multi-camera tracking system. It includes settings for MQTT communication, data fusion logic, Kalman filter tuning, and map projection rendering. Modifying this file allows easy adaptation to different environments and tuning of algorithm behavior without changing core code.

### main.py functionality

This script acts as the entry point for the centralized multi-camera data fusion system. It initializes the MQTT subscriber client, connects to the broker securely, subscribes to the appropriate topics from multiple Raspberry Pi devices, and starts the continuous event loop that handles incoming tracking data.

**Key Functional Areas:**
- Initializes and configures the MQTT client using subscriber.py.
- Loads all required settings from config.py.
- Connects to a secure MQTT broker using TLS certificates.
- Subscribes to all topic streams defined for each RPI.
- Starts the main loop, which listens for messages, performs data fusion, and publishes results via MQTT.

**Function Summaries:**
`main()`
- Prints system startup information (broker, topics, fusion topic).
- Calls setup_mqtt_client() from subscriber.py, which:
    - Registers MQTT callbacks (on_connect, on_message, etc.).
    - Loads certificates and credentials.
- Connects to the broker using the parameters defined in config.py.
- Starts a blocking message loop using loop_forever() to:
    - Handle all incoming MQTT messages
    - Trigger fusion and visualization routines via the callbacks defined in subscriber.py


## Known shortfalls
1. Fusion Breakdown with Multiple RPIs
     When tracking data is received from more than one Raspberry Pi (e.g., RPI1 and RPI2), the fusion algorithm occasionally fails to merge object tracks into a single global track. This is likely due to overly strict fusion conditions (e.g., color or position thresholds), resulting in the same object being interpreted as separate entities.

2. Unreliable Message Handling from RPI1
     RPI1 messages are sometimes dropped or not processed in time, especially under high load or poor network conditions. This appears to stem from the lack of multi-threaded message handling, particularly when the system is publishing or consuming MQTT messages.

3. Duplicate Fused Tracks During Object Motion
     During fast or continuous movement, an object may be visualized as two distinct global tracks due to a mismatch in either the position or color criteria across camera views. If one of the fusion conditions fails (e.g., timestamp misalignment, minor color variation), the system assigns new global IDs to the same physical object, leading to temporary duplication on the map.


## Future Improvement
1. Robust Color Matching Strategy
      Differences in lighting, exposure, or camera angles can cause variations in the perceived object color across cameras.Using more lighting-invariant features might reduce mismatches in such cases.

2. Explore Alternative Data Fusion Techniques
      It may be worthwhile to experiment with alternative fusion architectures such as:
       -  Probabilistic data association (e.g., JPDA)
       -  Graph-based or clustering-based matching      

