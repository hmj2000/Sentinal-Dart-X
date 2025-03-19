import struct
import serial
import threading
import time

usleep = lambda x: time.sleep(x/1000000.0)

class SpeedController:
    def __init__(self, ser, serlock, pulse_Per_Rev=800, mm_Per_Rev=43.018):
        self.pulse_Left_Us = 0
        self.pulse_Right_Us = 0
        self.right_Forward = True
        self.left_Forward = True
        self.disable_Left = True
        self.disable_Right = True
        self.state_Lock = threading.Lock()
        self.exit = False
        self.ser = ser
        self.serlock = serlock
        
        self.pulse_Per_Rev = pulse_Per_Rev
        self.mm_Per_Rev = mm_Per_Rev
    
    def left_Loop(self, s_Lock, serlock, ser):
        while True:
            s_Lock.acquire()
            if self.exit == True:
                s_Lock.release()
                break
            disable = self.disable_Left
            sleep_Amount = self.pulse_Left_Us
            forward = self.left_Forward
            s_Lock.release()
            usleep(abs(sleep_Amount))
            if not disable:
                serlock.acquire()
                if forward:
                    ser.write(struct.pack('>BBB', 0x02, 0x00, ord('\n')))
                else:
                    ser.write(struct.pack('>BBB', 0x02, 0x01, ord('\n')))
                serlock.release()
                
            
    def right_Loop(self, s_Lock, serlock, ser):
        while True:
            s_Lock.acquire()
            if self.exit == True:
                s_Lock.release()
                break
            disable = self.disable_Right
            sleep_Amount = self.pulse_Right_Us
            forward = self.right_Forward
            s_Lock.release()
            usleep(abs(sleep_Amount))
            if not disable:
                serlock.acquire()
                if forward:
                    ser.write(struct.pack('>BBB', 0x02, 0x02, ord('\n')))
                else:
                    ser.write(struct.pack('>BBB', 0x02, 0x03, ord('\n')))
                serlock.release()
            
    
    def start(self):
        self.t1 = threading.Thread(target=self.left_Loop, args=(self.state_Lock, self.serlock, self.ser))
        self.t2 = threading.Thread(target=self.right_Loop, args=(self.state_Lock, self.serlock, self.ser))
        self.t1.start()
        self.t2.start()
    
    def mms_To_Us_Per_Pulse(self, mms):
        return (1000000)/(mms * (1/self.mm_Per_Rev)*self.pulse_Per_Rev)
    
    
    def set_Speed_Left(self,mms):
        self.state_Lock.acquire()
        if (mms == 0):
            self.pulse_Left_Us = 1000
            self.disable_Left = True
        else:
            self.pulse_Left_Us = self.mms_To_Us_Per_Pulse(mms)
            self.disable_Left = False
        self.state_Lock.release()
    
    def set_Speed_Right(self,mms):
        self.state_Lock.acquire()
        if (mms == 0):
            self.pulse_Right_Us = 1000
            self.disable_Right = True
        else:
            self.pulse_Right_Us = self.mms_To_Us_Per_Pulse(mms)
            self.disable_Right = False
        self.state_Lock.release()
    
    def stop(self):
        self.state_Lock.acquire()
        self.exit = True
        self.state_Lock.release()
        
    
    
    

class SecurityRobot:
        
    def __init__(self, serial_port: str = "/dev/ttyUSB0", baud_rate: int = 115200):
        """
        Initialize the SecurityRobot communication interface.
        :param serial_port: The serial device file (e.g., '/dev/ttyUSB0')
        :param baud_rate: Baud rate for serial communication (default: 115200)
        """
        self.serlock = threading.Lock()
        self.ser = serial.Serial(serial_port, baud_rate, timeout=1)
        self.sc = SpeedController(self.ser, self.serlock)
        self.sc.start()

    def send_command(self, command: int, units: int):
        message = struct.pack('>BBB', command, units, ord('\n'))
        self.serlock.acquire()
        self.ser.write(message)
        self.serlock.release()
    
    def stop_everything(self):
        """Sends the stop command to halt all operations."""
        self.send_command(0, 0)
    
    def toggle_nerf_gun(self, state: bool):
        """Toggles the Nerf gun on or off.
        :param state: True to start shooting, False to stop shooting.
        """
        self.send_command(1, 1 if state else 0)
    
    def set_left_stepper(self, mms: int):
        self.sc.set_Speed_Left(mms)
    
    def set_right_stepper(self, mms: int):

        self.sc.set_Speed_Right(mms)
    
    def close(self):
        """Closes the serial connection."""
        self.sc.stop()
        self.serlock.acquire()
        self.ser.close()
        self.serlock.release()

# Example Usage:
# robot = SecurityRobot('/dev/ttyUSB0')
# robot.stop_everything()
# robot.toggle_nerf_gun(True)
# robot.set_left_stepper(-1000)
# robot.set_right_stepper(1500)
# robot.close()
