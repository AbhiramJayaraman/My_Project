from smbus2 import SMBus
import time
from config import *

def write_register(bus, reg, value):
    try:
        bus.write_byte_data(PCA9685_ADDRESS, reg, value)
        return True
    except Exception as e:
        print(f" Failed to write register 0x{reg:02X}: {e}")
        return False

def set_pwm(bus, channel, on, off):
    try:
        reg = LED0_ON_L + 4 * channel
        bus.write_byte_data(PCA9685_ADDRESS, reg, on & 0xFF)
        bus.write_byte_data(PCA9685_ADDRESS, reg + 1, on >> 8)
        bus.write_byte_data(PCA9685_ADDRESS, reg + 2, off & 0xFF)
        bus.write_byte_data(PCA9685_ADDRESS, reg + 3, off >> 8)
        return True
    except Exception as e:
        print(f" Failed to set PWM on channel {channel}: {e}")
        return False

def set_pwm_freq(bus, freq_hz):
    try:
        prescale_val = int(25000000.0 / (4096 * freq_hz) - 1 + 0.5)
        prescale_val = max(3, min(prescale_val, 255))
        
        old_mode = bus.read_byte_data(PCA9685_ADDRESS, MODE1)
        new_mode = (old_mode & 0x7F) | 0x10
        
        write_register(bus, MODE1, new_mode)
        write_register(bus, PRESCALE, prescale_val)
        write_register(bus, MODE1, old_mode)
        time.sleep(0.005)
        write_register(bus, MODE1, old_mode | 0xA1)
        
        print(f" PWM frequency set to {freq_hz}Hz")
        return True
    except Exception as e:
        print(f" Failed to set PWM frequency: {e}")
        return False

def initialize_pca9685(bus):
    print(" Initializing PCA9685...")
    try:
        write_register(bus, MODE1, 0x00)
        time.sleep(0.1)
        for channel in range(16):
            set_pwm(bus, channel, 0, 0)
        write_register(bus, MODE2, 0x04)
        time.sleep(0.1)
        print(" PCA9685 initialized")
        return True
    except Exception as e:
        print(f" PCA9685 initialization failed: {e}")
        return False

def turn_off_servo(bus, channel, name=""):
    try:
        set_pwm(bus, channel, 0, 0)
        print(f" {name} servo turned OFF")
        return True
    except Exception as e:
        print(f" Failed to turn off {name} servo: {e}")
        return False

def turn_off_all_servos(bus):
    print(" Turning off all servos...")
    for channel in range(16):
        set_pwm(bus, channel, 0, 0)
    print(" All servos turned OFF")
