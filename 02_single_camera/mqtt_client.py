"""
mqtt_client.py

Handles MQTT communication for publishing object tracking data to a remote broker.

This module manages:
- Storing per-track metadata (label, confidence, position, pose usage, color).
- Selecting the best data per track based on confidence and pose estimation.
- Formatting and serializing data to JSON for MQTT.
- Connecting securely to the broker using TLS certificates.
- Publishing data at a fixed interval defined in the configuration.
- Running the MQTT publishing loop in a background thread to avoid blocking the main pipeline.

Includes exception handling for missing/invalid certificate files and connection errors.
"""

import threading
import time
import json
import os
import ssl
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import paho.mqtt.client as mqtt
import numpy as np

from parameters_file import configuration

# Global Variables
track_data_storage: defaultdict[int, List[Dict[str, Any]]] = defaultdict(list)
track_data_lock = threading.Lock()
last_send_time: Optional[datetime] = None
last_send_lock = threading.Lock()


def update_track_storage(
    track_id: int,
    label_name: str,
    confidence: float,
    position: Tuple[float, float, float],
    avg_colour: Tuple[int, int, int],
    used_pose: bool
) -> None:
    """
    Update the global track data storage with a new entry for a given track.

    Args:
        track_id (int): Unique ID of the tracked object.
        label_name (str): Label of the detected object.
        confidence (float): Confidence score of the detection.
        position (Tuple[float, float, float]): 3D position coordinates.
        avg_colour (Tuple[int, int, int]): Average color in RGB.
        used_pose (bool): Whether pose estimation was used for this entry.

    Returns:
        None
    """
    entry = {
        "timestamp": time.time(),
        "label_name": label_name,
        "confidence": confidence,
        "position": position,
        "avg_colour": avg_colour,
        "used_pose": used_pose,
    }
    with track_data_lock:
        track_data_storage[track_id].append(entry)


def select_and_clear_data_for_mqtt() -> Dict[int, Dict[str, Any]]:
    """
    Select the best entry per track to send via MQTT and clear stored entries.

    Selection logic:
      - For non-'person' labels: select the latest entry.
      - For 'person' labels: select the latest entry with used_pose == True;
        if none, select the latest entry.

    Clears the track data storage after selection.

    Returns:
        Dict[int, Dict[str, Any]]: Mapping of track_id to selected data entry.
    """
    mqtt_data: Dict[int, Dict[str, Any]] = {}
    with track_data_lock:
        for track_id, entries in list(track_data_storage.items()):
            if not entries:
                continue

            # Sort newest to oldest
            entries_sorted = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
            latest_label = entries_sorted[0]["label_name"]

            if latest_label != "person":
                selected = entries_sorted[0]
            else:
                pose_entries = [e for e in entries_sorted if e["used_pose"]]
                selected = pose_entries[0] if pose_entries else entries_sorted[0]

            mqtt_data[track_id] = selected

        # If not cleared, the track data storage would fill up. Only clear after sending data
        track_data_storage.clear()
    return mqtt_data


def mqtt_sender_thread():
    try:
        # Validate certificate paths to avoid errors
        for name, path in {
            "CERTFILE": configuration.mqtt_client.CERTFILE,
            "KEYFILE": configuration.mqtt_client.KEYFILE
        }.items():
            if path is None or not os.path.isfile(path):
                raise FileNotFoundError(f"❌ MQTT certificate file not found or not set: {name} -> {path}")

        client = mqtt.Client(client_id=configuration.mqtt_client.CLIENT_ID, protocol=mqtt.MQTTv311, transport="tcp")
        client.tls_set(
            certfile=configuration.mqtt_client.CERTFILE,
            keyfile=configuration.mqtt_client.KEYFILE,
            ca_certs=configuration.mqtt_client.CA_CERTS
        )
        client.username_pw_set(configuration.mqtt_client.USERNAME)

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("✅ MQTT connected successfully.")
            else:
                print(f"⚠️ MQTT connection failed with code {rc}")

        client.on_connect = on_connect
        client.connect(configuration.mqtt_client.BROKER_ADDRESS, configuration.mqtt_client.PORT)
        client.loop_start()

    except FileNotFoundError as e:
        print(e)
        return
    except ssl.SSLError as e:
        print(f"❌ SSL error during MQTT setup: {e}")
        return
    except Exception as e:
        print(f"❌ Unexpected error during MQTT setup: {e}")
        return

    global last_send_time
    while True:
        try:
            #need to synchronize clocks to enable good data fusion functionality
            now = time.time()
            next_time = ((now // configuration.mqtt_client.INTERVAL) + 1) * configuration.mqtt_client.INTERVAL
            time.sleep(next_time - now)

            mqtt_payload_dict = select_and_clear_data_for_mqtt()
            #only sends when having data, avoids unnecessary bandwidth usage
            if not mqtt_payload_dict:
                continue

            payload = {
                str(track_id): {
                    "label": data["label_name"],
                    "confidence": data["confidence"],
                    "position": data["position"],
                    "avg_colour": data["avg_colour"],
                    "used_pose": data["used_pose"],
                    "timestamp": data["timestamp"]
                }
                for track_id, data in mqtt_payload_dict.items()
            }
            payload = make_json_serializable(payload)

            print(f"Publishing at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

            result = client.publish(configuration.mqtt_client.TOPIC, json.dumps(payload))
            status = result[0]
            #ensure the user is aware of sending results
            if status == 0:
                print(f"Message sent successfully to topic `{configuration.mqtt_client.TOPIC}`")
            else:
                print(f"⚠️ Failed to send message to topic `{configuration.mqtt_client.TOPIC}`, status: {status}")

            timestamp = datetime.now(timezone.utc)
            #as the code is run in a thread, need to ensure mutual exclusion
            with last_send_lock:
                last_send_time = timestamp

        except Exception as e:
            print(f"Error in MQTT sender thread: {e}")
            time.sleep(1)


def get_last_sync_time() -> Optional[datetime]:
    """
    Get the timestamp of the last successful MQTT publish.
    Returns:
        Optional[datetime]: Last send time in UTC or None if not sent yet.
    """
    with last_send_lock:
        return last_send_time


def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert objects to JSON serializable types.

    Converts numpy types to native Python types.

    Args:
        obj (Any): Object to convert.

    Returns:
        Any: JSON-serializable version of the input object.
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
