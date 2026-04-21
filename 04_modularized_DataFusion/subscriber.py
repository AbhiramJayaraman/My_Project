"""

This script functions as an MQTT subscriber for multiple Raspberry Pi (RPI) devices.
It receives object tracking data from RPIs over MQTT, processes and fuses the data to
produce a global view of tracked objects, and then publishes the fused results. It also
visualizes the tracking map and logs incoming messages for record-keeping.


"""
from config import TOPICS
from fusion_engine import DataFusion
from publisher import publish_fused_data, log_message
from fusion_map import create_map_background,draw_map_view
from datetime import datetime
import json
import cv2
import numpy as np
import re
#import threading
import time


# Fusion control
fusion_window = 0.015  # seconds
last_fusion_time = 0
fusion_timer = None
rpi_received = set()
latest_data_buffer = {}  # {rpi_id: processed_tracks}


fusion_engine = DataFusion()

def on_connect(client, userdata, flags, rc):
    """
    Callback when client connects to the MQTT broker.

    Inputs:
    - client: MQTT client instance
    - flags: Response flags from broker
    - rc: Connection result code

    Output:
    - Prints connection status and subscribes to pre-defined topics.
    """
    if rc == 0:
        print("Connected to broker successfully")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"Subscribed to topic '{topic}'")
    else:
        print(f"Connection failed with code {rc}")
        
def on_message(client, userdata, msg):
    """
    MQTT callback for incoming messages from RPIs.

    Handles data collection, buffer management, fusion triggering,
    map drawing, publishing and logging.
    """
    global last_fusion_time, latest_data_buffer, rpi_received

    try:
        now = time.time()

        # Decode message
        payload_str = msg.payload.decode('utf-8')
        payload_dict = json.loads(payload_str)
        rpi_id = extract_rpi_id(msg.topic)

        print_received_message(rpi_id)

        processed_tracks = process_and_store_tracks(rpi_id, payload_dict)

        # If first message, start fusion window
        if last_fusion_time == 0:
            last_fusion_time = now

        # Check fusion condition
        if should_trigger_fusion(now):
            print("\n[FUSION] Triggering data fusion after buffer window...")

            # Create map background
            map_img, scalemap = create_map_background(scale=0.5)

            # Draw raw tracks
            draw_raw_tracks_on_map(map_img, scalemap)

            # Run data fusion
            fused_tracks = run_data_fusion()

            # Print fused data
            print_fused_tracks(fused_tracks)

            # Draw fused tracks
            draw_fused_tracks_on_map(map_img, scalemap, fused_tracks)

            # Publish
            publish_fused_data(client, fused_tracks)

            # Show map or fallback save
            show_or_save_map(map_img)

            # Log message
            log_message(msg.topic, rpi_id, payload_dict, fused_tracks)

            # Reset buffers
            reset_fusion_buffers()

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Raw payload: {msg.payload.decode('utf-8', errors='replace')}")
    except Exception as e:
        print(f"Error in on_message: {e}")

def print_received_message(rpi_id):
    """
    Prints header for received message from a specific RPI.
    """
    print(f"\n{'='*60}")
    print(f"Message received from {rpi_id} at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    print(f"{'='*60}")

def print_raw_track_info(processed_data, rpi_id):
    """
    Prints individual raw track info from RPI.
    """
    print(f"\n{rpi_id} - Track ID: {processed_data['track_id']}")
    print(f"  Time: {processed_data['readable_time']}")
    print(f"  Label: {processed_data['label']}")
    print(f"  Confidence: {processed_data['confidence']}")
    print(f"  Position: {processed_data['position']}")
    print(f"  Average Color: {processed_data['avg_colour']}")

def print_fused_track_info(global_id, track_info):
    """
    Prints fused track info (no track_id, no readable_time).
    """
    print(f"\nGlobal ID: {global_id}")
    print(f"  Label: {track_info['label']}")
    print(f"  Avg Position: ({track_info['position'][0]:.1f}, {track_info['position'][1]:.1f}) cm")
    print(f"  Color (RGB): ({track_info['avg_colour'][0]}, {track_info['avg_colour'][1]}, {track_info['avg_colour'][2]})")
    print(f"  Confidence: {track_info['confidence']:.2f}")

def print_fused_tracks(fused_tracks):
    """
    Prints all fused tracks with their sources.
    """
    print(f"\n{'*'*60}")
    if fused_tracks:
        print("FUSED GLOBAL TRACKS:")
        print(f"{'*'*60}")

        for global_id, track_info in fused_tracks.items():
            print_fused_track_info(global_id, track_info)
            print(f"  Sources ({track_info['num_sources']} RPIs):")

            for source_id, track_id in track_info['source_tracks']:
                source_data = fusion_engine.data_buffer[source_id].get(track_id, {})
                ts = source_data.get('timestamp')
                if isinstance(ts, (int, float)):
                    ts_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]
                else:
                    ts_str = "N/A"
                print(f"    - {source_id} (Track ID: {track_id}) → Timestamp: {ts_str}")
    else:
        print("NO TRACKS DETECTED - PUBLISHING EMPTY STATE")
        print(f"{'*'*60}")

def process_and_store_tracks(rpi_id, payload_dict):
    """
    Processes incoming tracks, prints them, and updates the data buffer.

    Returns:
    - processed_tracks: Dictionary of processed tracks for this RPI.
    """
    global latest_data_buffer, rpi_received

    processed_tracks = {}
    for track_id, data in payload_dict.items():
        processed_data = process_track_data(track_id, data)
        if processed_data:
            processed_tracks[track_id] = {
                'label': processed_data['label'],
                'confidence': processed_data['confidence'],
                'position': processed_data['raw_position'],
                'avg_colour': processed_data['raw_colour'],
                'timestamp': processed_data['raw_timestamp'],
                'used_pose': processed_data['used_pose'],
                'track_id': processed_data['track_id'],
                'readable_time': processed_data['readable_time']
            }

            print_raw_track_info(processed_data, rpi_id)

    latest_data_buffer[rpi_id] = processed_tracks
    rpi_received.add(rpi_id)

    return processed_tracks

def should_trigger_fusion(now):
    """
    Checks if the fusion window has expired.

    Returns:
    - Boolean: True if fusion should be triggered.
    """
    return (now - last_fusion_time) >= fusion_window

def draw_raw_tracks_on_map(map_img, scalemap):
    """
    Draws raw tracks from all RPIs onto the map.
    """
    for rpi_id, track_dict in latest_data_buffer.items():
        rpicolour = (255, 0, 0) if rpi_id == "rpi1" else (0, 255, 0) if rpi_id == "rpi2" else (0, 0, 0)
        for track_id, track in track_dict.items():
            pos = track.get("position", [0, 0])
            if isinstance(pos, list) and len(pos) >= 2:
                pos_tuple = (float(pos[0]), float(pos[1]))
                draw_map_view(map_img, pos_tuple, track.get("label", ""), rpicolour, scalemap)


def draw_fused_tracks_on_map(map_img, scalemap, fused_tracks):
    """
    Draws fused tracks in red on the map.
    """
    red = (0, 0, 255)
    for global_id, track_info in fused_tracks.items():
        pos = (track_info['position'][0], track_info['position'][1])
        draw_map_view(map_img, pos, track_info['label'], red, scalemap)

def run_data_fusion():
    """
    Runs the data fusion process.

    Returns:
    - fused_tracks: Dictionary of fused tracks.
    """
    for rpi_id, processed_tracks in latest_data_buffer.items():
        fusion_engine.add_track_data(rpi_id, processed_tracks)

    return fusion_engine.fuse_tracks()

def show_or_save_map(map_img):
    """
    Displays the map using OpenCV, or saves fallback image if GUI fails.
    """
    map_img = np.ascontiguousarray(map_img)
    try:
        cv2.namedWindow("Map with track locations", cv2.WINDOW_NORMAL)
        cv2.imshow("Map with track locations", map_img)
        cv2.resizeWindow("Map with track locations", map_img.shape[1], map_img.shape[0])
        cv2.waitKey(1)
    except Exception as e:
        print(f"[WARNING] GUI window failed: {e}")
        cv2.imwrite("fallback_map.png", map_img)

def reset_fusion_buffers():
    """
    Resets fusion buffers for the next cycle.
    """
    global rpi_received, latest_data_buffer, last_fusion_time
    rpi_received.clear()
    latest_data_buffer.clear()
    last_fusion_time = 0



def on_subscribe(client, userdata, mid, granted_qos):
    """
    Callback confirming subscription to MQTT topic.
    """
    print(f"Subscription confirmed with QoS: {granted_qos}")
    
    
def on_disconnect(client, userdata, rc):
    """
    Callback when client disconnects from MQTT broker.
    """
    if rc != 0:
        print(f"Unexpected disconnection. Return code: {rc}")
    else:
        print("Disconnected from broker")
        
        
        
def extract_rpi_id(topic):
    """
    Extract Raspberry Pi ID from MQTT topic string.

    Input:
    - topic: Topic string

    Output:
    - Returns string identifying RPI (rpi1, rpi2, rpi3, or 'unknown')
    """

    if "rpi1" in topic:
        return "rpi1"
    elif "rpi2" in topic:
        return "rpi2"
    elif "rpi3" in topic:
        return "rpi3"
    return "unknown"
    
    
    
def process_track_data(track_id, data):
    """
    Process raw track data into formatted, readable dictionary.

    Inputs:
    - track_id: Unique identifier for the track
    - data: Dictionary of raw data for the track

    Output:
    - Returns dictionary with formatted values or None on error.
    """
    try:
        timestamp = data.get("timestamp", "N/A")
        label = data.get("label", "unknown")
        confidence = data.get("confidence", "N/A")
        position = data.get("position", [0, 0])
        avg_colour = data.get("avg_colour", [0, 0, 0])
        used_pose = data.get("used_pose", False)
        
        # Format timestamp
        if timestamp != "N/A" and isinstance(timestamp, (int, float)):
            readable_time = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        else:
            readable_time = "N/A"
        
        # Format position
        if isinstance(position, list) and len(position) >= 2:
            pos_str = f"({position[0]:.1f}, {position[1]:.1f}) cm"
        else:
            pos_str = "N/A"
        
        # Format color
        if isinstance(avg_colour, list) and len(avg_colour) >= 3:
            color_str = f"BGR({avg_colour[0]:.0f}, {avg_colour[1]:.0f}, {avg_colour[2]:.0f})"
        else:
            color_str = "N/A"
        
        return {
            "track_id": track_id,
            "readable_time": readable_time,
            "label": label,
            "confidence": confidence,
            "position": pos_str,
            "avg_colour": color_str,
            "used_pose": used_pose,
            "raw_timestamp": timestamp,
            "raw_position": position,
            "raw_colour": avg_colour
        }
    except Exception as e:
        print(f"Error processing track data for {track_id}: {e}")
        return None

def setup_mqtt_client():
    """
    Setup and configure the MQTT client with TLS security.

    Output:
    - Returns configured MQTT client instance.
    """
    import paho.mqtt.client as mqtt
    from config import CLIENT_ID, USERNAME, CERTFILE, KEYFILE, CA_CERTS, BROKER_ADDRESS, PORT

    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311, transport="tcp")
    client.tls_set(certfile=CERTFILE, keyfile=KEYFILE, ca_certs=CA_CERTS)
    client.username_pw_set(USERNAME)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe

    return client                        
                