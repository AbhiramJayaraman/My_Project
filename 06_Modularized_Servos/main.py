from smbus2 import SMBus
from config import TARGET_ROTATION_ANGLE, TARGET_TILT_ANGLE
from pca9685 import initialize_pca9685, set_pwm_freq, turn_off_all_servos
from servo_control import move_servo_to_angle, move_servos_simultaneously, display_calibration_info

def sequential_control():
    with SMBus(1) as bus:
        if not initialize_pca9685(bus): return
        if not set_pwm_freq(bus, 50): return
        move_servo_to_angle(bus, 'rotation_servo', TARGET_ROTATION_ANGLE)
        move_servo_to_angle(bus, 'tilt_servo', TARGET_TILT_ANGLE)
        turn_off_all_servos(bus)

def simultaneous_control():
    with SMBus(1) as bus:
        if not initialize_pca9685(bus): return
        if not set_pwm_freq(bus, 50): return
        move_servos_simultaneously(bus, TARGET_ROTATION_ANGLE, TARGET_TILT_ANGLE)

def calibration_test():
    angles = [0, 45, 90, 135, 180]
    with SMBus(1) as bus:
        initialize_pca9685(bus)
        set_pwm_freq(bus, 50)
        for angle in angles:
            print(f"\nTesting angle {angle}°")
            move_servos_simultaneously(bus, angle, angle)
            input("Check position. Press Enter for next.")
        turn_off_all_servos(bus)

def main():
    print("Select control mode:")
    print("1. Sequential")
    print("2. Simultaneous")
    print("3. Calibration Test")
    choice = input("Enter choice: ").strip()
    
    if choice == '2':
        simultaneous_control()
    elif choice == '3':
        calibration_test()
    else:
        sequential_control()

if __name__ == "__main__":
    main()
