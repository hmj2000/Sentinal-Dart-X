import serial
from Constants import Constants

class Commands:
    def __init__(self, serialPortFile="/dev/ttyUSB0", baudRate=115200):
        self.ser = serial.Serial(serialPortFile)
        self.lastSent = "0"
    
    def _sendString(self,string):
        if self.lastSent != string:
            self.ser.write(string.encode('utf-8'))
            self.lastSent = string
    
    def rotate(self,clockwise = True):
        if clockwise:
            if Constants.reverseControls:
                self._sendString('a')
            else:
                self._sendString('d')
        else:
            if Constants.reverseControls:
                self._sendString('d')
            else:
                self._sendString('a')
            
    def move(self,forward = True):
        if forward:
            if Constants.reverseControls:
                self._sendString('s')
            else:
                self._sendString('w')
        else:
            if Constants.reverseControls:
                self._sendString('w')
            else:
                self._sendString('s')
            
    def roam(self):
        self._sendString('r')
    
    def fire(self):
        self._sendString('f')
        
    def __del__(self):
        self.ser.close()
        
