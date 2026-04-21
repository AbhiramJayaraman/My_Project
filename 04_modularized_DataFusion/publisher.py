"""
MQTT Publisher Module for Multi-Camera Object Tracking System

OVERVIEW:
This module handles the publication of fused tracking data from multiple Raspberry Pi cameras
to MQTT topics for real-time distribution to subscribers (dashboards, analytics, etc.).

MAIN FUNCTIONS:
1. Publishes fused track data to MQTT topics
2. Logs all tracking activity to files for debugging and analysis
3. Handles both active tracking and empty states

INPUTS:
- MQTT client connection for message publishing
- Fused track data from the fusion engine (dict of global_id -> track_info)
- Raw track data from individual RPIs for logging
- Configuration parameters (topics, log files) from config module

OUTPUTS:
- MQTT messages published to fusion topic containing:
  * Timestamp of fusion
  * System status (active/no_tracks)
  * Fused track data with global IDs, positions, colors, confidence scores
  * Source RPI information for each track
- Log files containing:
  * Raw track data from each RPI
  * Fused track results
  * Publishing timestamps and status
  * Error messages and debugging information



USAGE:
- Called by main fusion system after track fusion is complete
- Ensures all subscribers receive timely updates about object presence/absence
- Provides persistent logging for system monitoring and debugging
"""
import json
from datetime import datetime
import paho.mqtt.client as mqtt
from config import FUSION_TOPIC, LOG_FILE

def publish_fused_data(client, fused_tracks):
    """
    Publish fused track data to MQTT fusion topic - ALWAYS publishes even when empty.
    
    Input: client - paho.mqtt.client.Client instance for MQTT communication
           fused_tracks - dict of global_id -> track_info from fusion engine
    Output: None (publishes to MQTT topic)
    Purpose: Broadcasts fused tracking data to all subscribers, ensuring they know
             when objects are detected vs when no objects are present
    """
    try:
        print(f"\n  PUBLISHING FUSED DATA ")
        print(f"Publishing to topic: {FUSION_TOPIC}")
        
        # Always create a publish_data dictionary
        publish_data = {
            "timestamp": datetime.now().timestamp(),
            "status": "active"
        }
        
        if fused_tracks:
            print(f"Number of fused tracks: {len(fused_tracks)}")
            print(f"Publish timestamp: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            # Add tracks information
            publish_data["tracks"] = {}
            for global_id, track_info in fused_tracks.items():
                publish_data["tracks"][global_id] = {
                    'global_id': track_info['global_id'],
                    'label': track_info['label'],
                    'position': track_info['position'],
                    'avg_colour': track_info['avg_colour'],
                    'confidence': track_info['confidence'],
                    'source_rpis': track_info['source_rpis'],
                    'num_sources': track_info['num_sources']
                }
                
                print(f"  {global_id}: {track_info['label']} from {track_info['source_rpis']}")
        else:
            # Explicit empty state
            print(f"Number of fused tracks: 0 (NO OBJECTS DETECTED)")
            print(f"Publish timestamp: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            print(f"  Publishing empty state to clear previous tracks")
            publish_data["status"] = "no_tracks"
            publish_data["message"] = "No objects detected by any camera"
        
        # Publish to fusion topic
        payload = json.dumps(publish_data, indent=2)
        print(f"\nPayload size: {len(payload)} bytes")
        print(f" Publishing now...")
        
        result = client.publish(FUSION_TOPIC, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            if fused_tracks:
                print(f" SUCCESS: Published {len(fused_tracks)} fused tracks")
            else:
                print(f" SUCCESS: Published empty state (no tracks)")
            print(f"Message ID: {result.mid}")
        else:
            print(f" FAILED: Unable to publish fused data")
            print(f" Error code: {result.rc}")
            
    except Exception as e:
        print(f" ERROR in publish_fused_data: {e}")
        
        
def log_message(topic, rpi_id, payload_dict, fused_tracks):
    """
    Log incoming message and fusion results to file for debugging and analysis.
    
    Input: topic - string MQTT topic where message was received
           rpi_id - string identifier of the source RPI
           payload_dict - dict of raw track data from the RPI
           fused_tracks - dict of global_id -> track_info from fusion engine
    Output: None (writes to log file)
    Purpose: Creates persistent record of all tracking activity for debugging,
             performance analysis, and system monitoring
    """
    try:
        with open(LOG_FILE, "a", encoding='utf-8') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"Message from {rpi_id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
            log.write(f"Topic: {topic}\n")
            log.write(f"Raw tracks: {len(payload_dict)}\n")
            log.write(f"{'='*80}\n")
            
            # Log individual tracks
            for track_id, data in payload_dict.items():
                log.write(f"Track {track_id}: {data}\n")
            
            # Log fused tracks and publishing info
            if fused_tracks:
                log.write(f"\nFUSED TRACKS ({len(fused_tracks)}) - PUBLISHED TO {FUSION_TOPIC}:\n")
                log.write(f"Published at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                for global_id, track_info in fused_tracks.items():
                    log.write(f"{global_id}: {track_info}\n")
            else:
                log.write(f"\nNo fused tracks generated - publishing empty state to {FUSION_TOPIC}\n")
            
            log.write(f"{'='*80}\n")
    except Exception as e:
        print(f"Error logging message: {e}")
        
        
        
