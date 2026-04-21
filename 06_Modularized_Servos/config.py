# === PCA9685 Configuration ===
PCA9685_ADDRESS = 0x40
MODE1 = 0x00
MODE2 = 0x01
PRESCALE = 0xFE
LED0_ON_L = 0x06

# === Servo Configuration ===
SERVO_CONFIG = {
    'rotation_servo': {
        'min_pulse': 500,
        'max_pulse': 2500,
        'freq': 50,
        'channel': 1
    },
    'tilt_servo': {
        'min_pulse': 1100,
        'max_pulse': 1940,
        'freq': 50,
        'channel': 0
    }
}

# === Target Angles ===
TARGET_ROTATION_ANGLE = 0
TARGET_TILT_ANGLE = 30

# === Timing ===
HOLD_TIME = 3
SETTLE_TIME = 2
