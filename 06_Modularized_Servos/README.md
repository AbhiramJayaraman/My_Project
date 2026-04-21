# Modular Servo Control System

## Overview

This repository provides a Python-based modular servo control system for controlling two servos (rotation and tilt) using a Raspberry Pi and a PCA9685 16-channel PWM controller.

The system offers:

- Smooth angle-based servo control (0° to 180°)
- Independent calibration for each servo
- Multiple operating modes (sequential, simultaneous, calibration test)
- Safe startup and shutdown
- User-friendly console interface with error recovery

---

## Features

- **Modular Design**: Cleanly separated logic into multiple files (`main.py`, `servo_control.py`, `pca9685.py`, `config.py`)
- **Flexible Calibration**: Each servo has its own configurable min/max pulse values
- **Three Control Modes**:
  - **Sequential**: Move servos one after the other
  - **Simultaneous**: Move both servos at once
  - **Calibration**: Move through test angles to verify calibration
- **Safe Shutdown**: Automatically turns off all servos when exiting
- **Robustness**: Handles I2C errors gracefully

---

## Folder Structure
├── config.py # Servo calibration and system parameters
├── main.py # Main menu and execution entry point
├── pca9685.py # Functions to initialize and control PCA9685 PWM board
├── servo_control.py # Functions to convert angle to PWM and move servos
├── requirements.txt # Python dependencies
└── README.md # Project documentation

---

## Hardware Setup

### Components Used

- Raspberry Pi (with I2C enabled)
- PCA9685 PWM Driver (16-channel, 12-bit)
- 2x Servo Motors (SG90, MG996R, or similar)
- Jumper Wires

### Wiring Instructions

| Wire Color | Connect To       | Purpose          |
|------------|------------------|------------------|
| Brown      | GND (on PCA9685) | Ground           |
| Red        | V+ (5V)          | Power supply     |
| Orange     | S1/S0            | PWM signal line  |

Ensure:
- PCA9685 is powered externally with 5V if servos draw high current.
- All GNDs (Pi, PCA9685, and servos) are connected together.
(The connection must be correct or it will lead for burning the servo motor)
---

## Servo Setup Guide

### Step 1: Enable I2C on Raspberry Pi

sudo raspi-config
Navigate to Interfacing Options → I2C → Enable
sudo reboot

###  step 2: Instanll Dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### step 3: Run the Script
python main.py

## Recommendations
1. Adjusting the Servo Angle Range 
      - If your servo does not reach the full 0–180° range, tweak min_pulse and max_pulse   values.
      - You’ll find these settings in the SERVO_CONFIG dictionary inside config.py.

2. Use Calibration Mode 
     -  python main.py
     → choose option 3 (Calibration Verification Test)   
     -  This moves both servos through 0°, 45°, 90°, 135°, and 180°.
     -  Observe each position and adjust min_pulse / max_pulse if any angle is off.
      

### Known shortfalls
1. Twisting of IMX500 Camera Cable     
     - Servo movement, especially rotation, can twist the flat ribbon or jumper cables  connected to the camera.
     - Repeated twisting may stress or snap the cable.