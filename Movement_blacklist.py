import time
from BlackList import BlackList
from struct_lib import SecurityRobot

class Configuration:
    """
    Configuration parameter management for the security system.
    """
    def __init__(self):
        # Communication settings
        self.SERIAL_PORT = '/dev/ttyUSB0'    # Serial port for robot
        self.BAUD_RATE = 115200              # Baud rate for serial communication
        self.DATABASE_FOLDER = 'path/to/database'  # Path to face database
        
        # Motion control parameters
        self.ALIGNMENT_THRESHOLD = 20    # Target alignment threshold (pixels)
        self.TURN_SPEED = 1000          # Base turning speed (mm/s)
        self.SCAN_ROTATION_SPEED = 500  # Scanning rotation speed (mm/s)
        self.FIRE_DURATION = 1          # Firing duration (seconds)
        
        # Safety parameters
        self.SAFE_DISTANCE = 50         # Minimum safe distance (cm)
        self.SCAN_INTERVAL = 0.1        # Minimum time between scans (seconds)
        
    def validate(self):
        """Validate configuration parameters"""
        assert isinstance(self.ALIGNMENT_THRESHOLD, (int, float)) and self.ALIGNMENT_THRESHOLD > 0
        assert isinstance(self.TURN_SPEED, (int, float)) and self.TURN_SPEED > 0
        assert isinstance(self.SCAN_ROTATION_SPEED, (int, float)) and self.SCAN_ROTATION_SPEED > 0
        assert isinstance(self.FIRE_DURATION, (int, float)) and self.FIRE_DURATION > 0
        assert isinstance(self.SAFE_DISTANCE, (int, float)) and self.SAFE_DISTANCE > 0
        assert isinstance(self.SCAN_INTERVAL, (int, float)) and self.SCAN_INTERVAL > 0

class SecuritySystem:
    """
    Main security system integrating BlackList detection with robot control.
    """
    def __init__(self, config: Configuration):
        """
        Initialize security system with configuration.
        
        Args:
            config (Configuration): System configuration parameters
        """
        self.config = config
        self.blacklist = None
        self.robot = None
        self.is_running = False
        self.last_scan_time = 0
        
        try:
            # Initialize BlackList system (which includes FaceDetector)
            self.blacklist = BlackList(config.DATABASE_FOLDER)
            
            # Initialize robot control
            self.robot = SecurityRobot(config.SERIAL_PORT, config.BAUD_RATE)
            
            self.is_running = True
            print("Security system initialized successfully")
            
        except Exception as e:
            print(f"Initialization failed: {e}")
            self.cleanup()
            raise

    def calculate_turn_speed(self, error, frame_width):
        """
        Calculate proportional turn speed based on target offset.
        
        Args:
            error (float): Pixel error from center
            frame_width (float): Width of frame in pixels
        
        Returns:
            float: Calculated turn speed
        """
        # Implement proportional control
        proportion = abs(error) / (frame_width / 2)
        return min(proportion * self.config.TURN_SPEED, self.config.TURN_SPEED)

    def process_target(self, target):
        """
        Process detected blacklisted face.
        
        Args:
            target: Face object with position information
        
        Returns:
            bool: True if target was successfully processed
        """
        try:
            if not target:
                return False

            # Calculate target position error
            frame_width = target._resolution[0]
            face_center_x = target.x + target.w / 2
            frame_center_x = frame_width / 2
            error = face_center_x - frame_center_x

            # Handle target alignment
            if abs(error) > self.config.ALIGNMENT_THRESHOLD:
                turn_speed = self.calculate_turn_speed(error, frame_width)
                
                # Apply turning motion
                if error > 0:  # Target is to the right
                    self.robot.set_left_stepper(turn_speed)
                    self.robot.set_right_stepper(-turn_speed)
                else:  # Target is to the left
                    self.robot.set_left_stepper(-turn_speed)
                    self.robot.set_right_stepper(turn_speed)
                    
                self.robot.toggle_nerf_gun(False)
                return False
            
            # Target is centered - execute response
            self.robot.stop_everything()
            time.sleep(0.1)  # Brief pause to ensure stop
            self.robot.toggle_nerf_gun(True)
            time.sleep(self.config.FIRE_DURATION)
            self.robot.toggle_nerf_gun(False)
            return True

        except Exception as e:
            print(f"Target processing error: {e}")
            self.robot.stop_everything()
            self.robot.toggle_nerf_gun(False)
            return False

    def scan_environment(self):
        """Execute scanning rotation when no target is detected"""
        try:
            self.robot.set_left_stepper(-self.config.SCAN_ROTATION_SPEED)
            self.robot.set_right_stepper(self.config.SCAN_ROTATION_SPEED)
            self.robot.toggle_nerf_gun(False)
        except Exception as e:
            print(f"Scanning error: {e}")
            self.robot.stop_everything()

    def cleanup(self):
        """Clean up system resources"""
        print("Initiating system shutdown...")
        if self.robot:
            try:
                self.robot.stop_everything()
                self.robot.close()
            except Exception as e:
                print(f"Robot cleanup error: {e}")
        
        # BlackList's destructor will handle camera cleanup
        self.blacklist = None
        self.is_running = False
        print("System shutdown complete")

    def run(self):
        """Main system operation loop"""
        print("Security system starting...")
        try:
            while self.is_running:
                current_time = time.time()
                
                # Control scan frequency
                if current_time - self.last_scan_time < self.config.SCAN_INTERVAL:
                    time.sleep(0.01)
                    continue
                    
                self.last_scan_time = current_time
                
                try:
                    # Get blacklisted faces from the detection system
                    blacklisted_faces = self.blacklist.getBlackListedFacesInView()
                    
                    if not self.is_running:
                        break
                        
                    if blacklisted_faces:
                        # Process first detected target
                        if not self.process_target(blacklisted_faces[0]):
                            print("Target processing incomplete, continuing tracking")
                    else:
                        self.scan_environment()
                        
                except Exception as e:
                    print(f"Processing loop error: {e}")
                    time.sleep(1)  # Error recovery delay
                    
        except KeyboardInterrupt:
            print("System shutdown requested by user")
        except Exception as e:
            print(f"Critical system error: {e}")
        finally:
            self.cleanup()

def main():
    """System entry point"""
    try:
        # Initialize configuration
        config = Configuration()
        config.validate()
        
        # Create and run security system
        security_system = SecuritySystem(config)
        security_system.run()
        
    except Exception as e:
        print(f"System startup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
