import struct
import serial

class SecurityRobot:
    def __init__(self, serial_port: str, baud_rate: int = 115200):
        """
        Initialize the SecurityRobot communication interface.
        :param serial_port: The serial device file (e.g., '/dev/ttyUSB0')
        :param baud_rate: Baud rate for serial communication (default: 115200)
        """
        self.ser = serial.Serial(serial_port, baud_rate, timeout=1)

    def send_command(self, command: int, units: int):
        """
        Sends a command to the ESP32 over serial communication.
        :param command: 8-bit unsigned integer representing the command number.
        :param units: 16-bit unsigned integer representing the unit value.
        """
        message = struct.pack('>BHB', command, units, ord('\n'))
        self.ser.write(message)
    
    def stop_everything(self):
        """Sends the stop command to halt all operations."""
        self.send_command(0, 0)
    
    def toggle_nerf_gun(self, state: bool):
        """Toggles the Nerf gun on or off.
        :param state: True to start shooting, False to stop shooting.
        """
        self.send_command(1, 1 if state else 0)
    
    def set_left_stepper(self, velocity: int):
        """Sets the velocity of the left stepper motor.
        :param velocity: Velocity in mm/s. Adjusted to fit unsigned representation.
        """
        units = velocity + 32768
        self.send_command(2, units)
    
    def set_right_stepper(self, velocity: int):
        """Sets the velocity of the right stepper motor.
        :param velocity: Velocity in mm/s. Adjusted to fit unsigned representation.
        """
        units = velocity + 32768
        self.send_command(3, units)
    
    def close(self):
        """Closes the serial connection."""
        self.ser.close()

# Example Usage:
# robot = SecurityRobot('/dev/ttyUSB0')
# robot.stop_everything()
# robot.toggle_nerf_gun(True)
# robot.set_left_stepper(-1000)
# robot.set_right_stepper(1500)
# robot.close()