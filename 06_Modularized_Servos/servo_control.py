# servo_control.py

import time
from config import *
from pca9685 import set_pwm, turn_off_servo, turn_off_all_servos

def angle_to_pwm(angle, servo_config):
    angle = max(0, min(angle, 180))
    pulse_us = servo_config['min_pulse'] + (angle / 180.0) * (servo_config['max_pulse'] - servo_config['min_pulse'])
    period_us = 1000000 / servo_config['freq']
    pwm_counts = int((pulse_us * 4096) / period_us)
    return min(pwm_counts, 4095), pulse_us

def move_servo_to_angle(bus, servo_name, angle):
    config = SERVO_CONFIG[servo_name]
    channel = config['channel']
    pwm_value, pulse_us = angle_to_pwm(angle, config)
    
    print(f"\n Moving {servo_name} to {angle}°: {pulse_us:.0f}μs → PWM {pwm_value}")
    
    if not set_pwm(bus, channel, 0, pwm_value):
        return False
    time.sleep(SETTLE_TIME)
    print(f" Holding position for {HOLD_TIME} seconds...")
    time.sleep(HOLD_TIME)
    turn_off_servo(bus, channel, servo_name)
    return True

def move_servos_simultaneously(bus, rotation_angle, tilt_angle):
    rot_config = SERVO_CONFIG['rotation_servo']
    tilt_config = SERVO_CONFIG['tilt_servo']
    
    rot_pwm, _ = angle_to_pwm(rotation_angle, rot_config)
    tilt_pwm, _ = angle_to_pwm(tilt_angle, tilt_config)
    
    set_pwm(bus, rot_config['channel'], 0, rot_pwm)
    set_pwm(bus, tilt_config['channel'], 0, tilt_pwm)
    
    time.sleep(SETTLE_TIME)
    time.sleep(HOLD_TIME)
    turn_off_all_servos(bus)
    return True

def display_calibration_info():
    print("\n CALIBRATION SETTINGS")
    print("=" * 60)
    for name, cfg in SERVO_CONFIG.items():
        print(f"{name}: ch={cfg['channel']} min={cfg['min_pulse']} max={cfg['max_pulse']}")
