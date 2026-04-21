"""
main.py

This script serves as the main entry point for running the Multi-RPI MQTT Subscriber
with Data Fusion functionality. It sets up the MQTT client, connects to the broker,
subscribes to topics, and continuously listens for incoming messages while handling
publishing and visualization of fused tracking data.

Dependencies:
- subscriber.py: Contains the MQTT client setup and message handling logic.
- config.py: Contains configuration parameters like broker address, topics, and certificates.

Run this script to start the subscriber and fusion system.
"""
from subscriber import setup_mqtt_client
from config import BROKER_ADDRESS, PORT, TOPICS, FUSION_TOPIC

def main():
    """
    Main function to start the MQTT subscriber and data fusion process.

    Inputs:
    - None (uses configuration from config.py)

    Output:
    - Establishes MQTT connection and starts the message loop to handle incoming data.
    """
    print("Starting Multi-RPI MQTT Subscriber with Data Fusion...")
    print(f"Broker: {BROKER_ADDRESS}:{PORT}")
    print(f"Subscribed Topics: {', '.join(TOPICS)}")
    print(f"FUSION PUBLISHING TOPIC: {FUSION_TOPIC}")
    print("-" * 80)

    try:
        client = setup_mqtt_client()
        client.connect(BROKER_ADDRESS, PORT, keepalive=60)
        print("Starting message loop...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nShutting down subscriber...")
        client.disconnect()
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    main()
