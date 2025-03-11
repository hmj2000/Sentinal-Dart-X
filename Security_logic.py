import time
import cv2
import traceback
import math
import random
from shapely.geometry import Point, Polygon
from map_store import MapStore

# ---------------------------- Configuration Class ----------------------------
class Configuration:
    def __init__(self):
        # Communication and database settings
        self.SERIAL_PORT = '/dev/ttyUSB0'          # Robot serial port
        self.BAUD_RATE = 115200                    # Baud rate
        self.DATABASE_FOLDER = 'path/to/database'   # Face database path

        # Motion control parameters
        self.ALIGNMENT_THRESHOLD = 20              # Permissible deviation in pixels for target alignment
        self.TURN_SPEED = 1000                     # Maximum turning speed
        self.SCAN_ROTATION_SPEED = 500             # Rotation speed during scanning
        self.FIRE_DURATION = 1                     # Firing duration (in seconds)
        self.FORWARD_SPEED = 800                   # Forward movement speed
        self.BACKWARD_SPEED = 600                  # Backward movement speed

        # Safety parameters
        self.SAFE_DISTANCE = 50                    # Minimum safe distance from obstacles (units depend on implementation)
        self.SCAN_INTERVAL = 0.1                   # Interval between scans
        self.OBSTACLE_AREA_THRESHOLD = 1000        # Minimum area for contours to be considered obstacles
        self.FULL_SCAN_ANGLE = 360                 # Full rotation angle for scanning (degrees)
        self.SCAN_STEP_ANGLE = 10                  # Rotation angle per step during scanning (degrees)

        # Electronic fence (allowed patrol area), e.g., a rectangular region defined by coordinates
        self.PATROL_AREA = [(0, 0), (640, 0), (640, 480), (0, 480)]

    def validate(self):
        """
        Validate the configuration parameters.
        """
        assert isinstance(self.ALIGNMENT_THRESHOLD, (int, float)) and self.ALIGNMENT_THRESHOLD > 0
        assert isinstance(self.TURN_SPEED, (int, float)) and self.TURN_SPEED > 0
        assert isinstance(self.SCAN_ROTATION_SPEED, (int, float)) and self.SCAN_ROTATION_SPEED > 0
        assert isinstance(self.FIRE_DURATION, (int, float)) and self.FIRE_DURATION > 0
        assert isinstance(self.SAFE_DISTANCE, (int, float)) and self.SAFE_DISTANCE > 0
        assert isinstance(self.SCAN_INTERVAL, (int, float)) and self.SCAN_INTERVAL > 0
        assert isinstance(self.FORWARD_SPEED, (int, float)) and self.FORWARD_SPEED > 0
        assert isinstance(self.BACKWARD_SPEED, (int, float)) and self.BACKWARD_SPEED > 0
        assert isinstance(self.OBSTACLE_AREA_THRESHOLD, (int, float)) and self.OBSTACLE_AREA_THRESHOLD > 0
        assert isinstance(self.FULL_SCAN_ANGLE, (int, float)) and self.FULL_SCAN_ANGLE > 0
        assert isinstance(self.SCAN_STEP_ANGLE, (int, float)) and self.SCAN_STEP_ANGLE > 0

# ---------------------------- Simulated Face Detection and Blacklist Recognition ----------------------------
class FakeBlackList:
    """
    Simulated blacklist detection module.
    Replace this class with the actual face detection and blacklist recognition module in production.
    """
    def __init__(self, database_folder):
        self.database_folder = database_folder
        # Initialize the camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Unable to open the camera")
        
        # For simulation purposes, occasionally return a fake detection
        self.detection_counter = 0
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def getBlackListedFacesInView(self):
        """
        Simulate capturing the current frame from the camera and detecting faces on the blacklist.
        In this simulation, randomly return a fake detection approximately every 50 calls.
        """
        self.detection_counter += 1
        
        # In a real implementation, you would use actual face detection here
        # For simulation, return a fake detection occasionally
        if self.detection_counter % 50 == 0:
            # Generate random face position with appropriate structure
            fake_face_width = random.randint(80, 120)
            fake_face_x = random.randint(0, self.frame_width - fake_face_width)
            fake_face_y = random.randint(0, self.frame_height - fake_face_width)
            
            return [{
                '_resolution': (self.frame_width, self.frame_height),
                'x': fake_face_x,
                'y': fake_face_y,
                'w': fake_face_width,
                'h': fake_face_width,
                'confidence': 0.95,
                'name': 'Simulation_Target'
            }]
        return []
    
    def get_current_frame(self):
        """
        Get the current frame from the camera.
        """
        ret, frame = self.cap.read()
        if ret:
            return frame
        else:
            return None
    
    def cleanup(self):
        """
        Release camera resources.
        """
        if self.cap:
            self.cap.release()
            cv2.destroyAllWindows()

# ---------------------------- Simulated Robot Control ----------------------------
class SecurityRobot:
    """
    Simulated robot control module.
    Replace this class with the actual robot control code in production.
    """
    def __init__(self, serial_port, baud_rate):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        # Initialize serial communication here
        print(f"Initializing robot on serial port: {serial_port}, baud rate: {baud_rate}")
        
        # For simulation purposes, track the robot's position and orientation
        self.position = (320, 240)  # Start in the middle of the patrol area
        self.orientation = 0  # In degrees, 0 is pointing east, 90 is north
        self.left_speed = 0
        self.right_speed = 0
        self.is_moving = False

    def set_left_stepper(self, speed):
        self.left_speed = speed
        self.is_moving = (self.left_speed != 0 or self.right_speed != 0)
        print(f"Setting left stepper motor speed to: {speed}")
        self._update_position()

    def set_right_stepper(self, speed):
        self.right_speed = speed
        self.is_moving = (self.left_speed != 0 or self.right_speed != 0)
        print(f"Setting right stepper motor speed to: {speed}")
        self._update_position()

    def _update_position(self):
        """
        Simulate the movement of the robot based on motor speeds.
        This is a simplified simulation - in a real robot, position would be tracked using sensors.
        """
        if not self.is_moving:
            return
            
        # Calculate rotation based on the difference between left and right motor speeds
        if self.left_speed != self.right_speed:
            # Turning
            rotation = (self.right_speed - self.left_speed) / 1000.0  # Scale down for simulation
            self.orientation = (self.orientation + rotation) % 360
        
        # Calculate forward/backward movement (average of both motor speeds)
        avg_speed = (self.left_speed + self.right_speed) / 2
        if avg_speed != 0:
            # Convert orientation to radians for trig functions
            orientation_rad = math.radians(self.orientation)
            # Calculate new position based on orientation and speed
            dx = math.cos(orientation_rad) * avg_speed / 5000.0  # Scale down for simulation
            dy = math.sin(orientation_rad) * avg_speed / 5000.0
            self.position = (self.position[0] + dx, self.position[1] + dy)
            print(f"Robot moved to position: {self.position}, orientation: {self.orientation}°")

    def move_forward(self, speed):
        self.set_left_stepper(speed)
        self.set_right_stepper(speed)
        print(f"Moving forward at speed: {speed}")

    def move_backward(self, speed):
        self.set_left_stepper(-speed)
        self.set_right_stepper(-speed)
        print(f"Moving backward at speed: {speed}")

    def turn_left(self, speed):
        self.set_left_stepper(-speed)
        self.set_right_stepper(speed)
        print(f"Turning left at speed: {speed}")

    def turn_right(self, speed):
        self.set_left_stepper(speed)
        self.set_right_stepper(-speed)
        print(f"Turning right at speed: {speed}")

    def toggle_nerf_gun(self, active: bool):
        if active:
            print("Activating Nerf gun")
        else:
            print("Deactivating Nerf gun")

    def stop_everything(self):
        self.set_left_stepper(0)
        self.set_right_stepper(0)
        self.is_moving = False
        print("Stopping all movements")

    def get_position(self):
        return self.position
        
    def get_orientation(self):
        return self.orientation

    def close(self):
        print("Closing robot control resources")

# ---------------------------- SecuritySystem Class ----------------------------
class SecuritySystem:
    def __init__(self, config: Configuration):
        self.config = config
        self.config.validate()

        # Initialize the electronic fence (patrol area)
        self.patrol_area = Polygon(self.config.PATROL_AREA)
        
        # Initialize map storage
        self.map_store = MapStore()

        # Initialize the blacklist detection module (simulated)
        try:
            self.blacklist = FakeBlackList(self.config.DATABASE_FOLDER)
        except Exception as e:
            print(f"Failed to initialize blacklist module: {e}")
            raise

        # Initialize robot control (simulated)
        try:
            self.robot = SecurityRobot(self.config.SERIAL_PORT, self.config.BAUD_RATE)
        except Exception as e:
            print(f"Robot initialization failed: {e}")
            raise
        
        self.is_running = True
        self.last_scan_time = 0
        self.scan_start_orientation = 0
        self.current_scan_angle = 0
        self.scan_in_progress = False
        self.state = "IDLE"  # States: IDLE, SCANNING, TRACKING, AVOIDING
        
        # Add the initial robot position to the map
        self._update_robot_position_in_map()

    def _update_robot_position_in_map(self):
        """
        Update the robot's position in the map store.
        """
        position = self.robot.get_position()
        orientation = self.robot.get_orientation()
        self.map_store.update_robot_position(position, orientation)
        
        # Check if the robot is within the patrol area
        if not self.is_within_patrol_area(*position):
            print("WARNING: Robot outside patrol area! Returning to safe zone...")
            self._return_to_safe_zone()

    def is_within_patrol_area(self, x, y):
        """
        Check if the given coordinates are within the allowed patrol area.

        Args:
            x, y: Coordinates.

        Returns:
            bool: True if the point is within the area.
        """
        point = Point(x, y)
        return self.patrol_area.contains(point)
    
    def _return_to_safe_zone(self):
        """
        Return the robot to a safe position within the patrol area.
        This is a simplified implementation - in a real system, path planning would be needed.
        """
        # Get the centroid of the patrol area as a safe point
        centroid = self.patrol_area.centroid
        safe_point = (centroid.x, centroid.y)
        
        # Stop current movement
        self.robot.stop_everything()
        time.sleep(0.5)
        
        # Calculate direction to safe point
        current_pos = self.robot.get_position()
        direction_x = safe_point[0] - current_pos[0]
        direction_y = safe_point[1] - current_pos[1]
        
        # Calculate angle to safe point
        target_angle = math.degrees(math.atan2(direction_y, direction_x)) % 360
        current_angle = self.robot.get_orientation()
        
        # Turn towards safe point
        angle_diff = (target_angle - current_angle + 180) % 360 - 180
        if angle_diff > 0:
            self.robot.turn_right(self.config.TURN_SPEED / 2)
        else:
            self.robot.turn_left(self.config.TURN_SPEED / 2)
            
        # Wait until approximately facing the right direction
        while abs(angle_diff) > 10:
            time.sleep(0.1)
            current_angle = self.robot.get_orientation()
            angle_diff = (target_angle - current_angle + 180) % 360 - 180
        
        # Move towards safe point
        self.robot.move_forward(self.config.FORWARD_SPEED / 2)
        
        # Wait until we're close to the safe point
        while not self.is_within_patrol_area(*self.robot.get_position()):
            time.sleep(0.1)
            self._update_robot_position_in_map()
        
        # Stop when we're back in the patrol area
        self.robot.stop_everything()
        print("Robot successfully returned to patrol area.")
    
    def calculate_turn_speed(self, error, frame_width):
        """
        Calculate the turning speed based on the deviation from the target.

        Args:
            error (float): The deviation of the target's center from the frame center.
            frame_width (float): The width of the frame.

        Returns:
            float: The actual turning speed.
        """
        proportion = abs(error) / (frame_width / 2)
        return min(proportion * self.config.TURN_SPEED, self.config.TURN_SPEED)
    
    def process_target(self, target):
        """
        Process the detected face target.

        Args:
            target: Face target object with keys for face positioning data.
        
        Returns:
            bool: True if the target was successfully processed.
        """
        try:
            if not target:
                return False
                
            # Validate that target has required keys
            required_keys = ['_resolution', 'x', 'w']
            if not all(key in target for key in required_keys):
                print(f"Invalid target format. Missing required keys. Available keys: {target.keys()}")
                return False

            frame_width = target['_resolution'][0]
            face_center_x = target['x'] + target['w'] / 2
            frame_center_x = frame_width / 2
            error = face_center_x - frame_center_x

            self.state = "TRACKING"
            self._update_robot_position_in_map()

            if abs(error) > self.config.ALIGNMENT_THRESHOLD:
                turn_speed = self.calculate_turn_speed(error, frame_width)
                if error > 0:
                    self.robot.set_left_stepper(turn_speed)
                    self.robot.set_right_stepper(-turn_speed)
                else:
                    self.robot.set_left_stepper(-turn_speed)
                    self.robot.set_right_stepper(turn_speed)
                self.robot.toggle_nerf_gun(False)
                return False
            else:
                self.robot.stop_everything()
                time.sleep(0.1)
                self.robot.toggle_nerf_gun(True)
                time.sleep(self.config.FIRE_DURATION)
                self.robot.toggle_nerf_gun(False)
                self.state = "IDLE"
                return True
        except Exception as e:
            print(f"Error processing target: {e}")
            traceback.print_exc()
            self.robot.stop_everything()
            self.robot.toggle_nerf_gun(False)
            self.state = "IDLE"
            return False

    def detect_obstacle(self, frame):
        """
        Use OpenCV to detect obstacles in the captured image.
        This simplified example applies Canny edge detection and contour finding, considering larger contours as obstacles.

        Args:
            frame: The image captured from the camera.
        
        Returns:
            list: A list of obstacle information dictionaries, each containing 'id', 'position', and 'size'.
        """
        obstacles_found = []
        if frame is None:
            return obstacles_found

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 50, 150)
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for idx, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                # Determine if the contour is an obstacle based on its area
                if area > self.config.OBSTACLE_AREA_THRESHOLD:
                    x, y, w, h = cv2.boundingRect(contour)
                    # Convert from image coordinates to world coordinates (simplified)
                    # In a real system, you would use proper coordinate transformation
                    robot_pos = self.robot.get_position()
                    robot_orient = self.robot.get_orientation()
                    
                    # Calculate obstacle position relative to robot
                    # This is a very simplified transformation - in reality, would be more complex
                    rel_x = x + w // 2 - frame.shape[1] // 2
                    rel_y = frame.shape[0] // 2 - (y + h // 2)  # Y is inverted in image coordinates
                    
                    # Convert to angle and distance
                    distance = math.sqrt(rel_x**2 + rel_y**2)
                    angle = math.degrees(math.atan2(rel_y, rel_x))
                    
                    # Transform to world coordinates
                    world_angle = (robot_orient + angle) % 360
                    world_x = robot_pos[0] + distance * math.cos(math.radians(world_angle))
                    world_y = robot_pos[1] + distance * math.sin(math.radians(world_angle))
                    
                    obstacle = {
                        'id': f'obstacle_{int(time.time())}_{idx}',
                        'position': (world_x, world_y),
                        'size': (w, h),
                        'distance': distance,
                        'angle': world_angle
                    }
                    obstacles_found.append(obstacle)
        except Exception as e:
            print(f"Error detecting obstacle: {e}")
            traceback.print_exc()
        
        return obstacles_found

    def avoid_obstacle(self, obstacles):
        """
        Execute an obstacle avoidance strategy based on the detected obstacles.
        """
        self.state = "AVOIDING"
        print(f"Obstacle detected, executing avoidance strategy... ({len(obstacles)} obstacles)")
        
        # Stop current movement
        self.robot.stop_everything()
        time.sleep(0.5)
        
        # Simple avoidance strategy: back up and turn away from obstacle
        # Sort obstacles by distance
        closest_obstacles = sorted(obstacles, key=lambda obs: obs['distance'])
        
        if closest_obstacles:
            closest = closest_obstacles[0]
            rel_angle = (closest['angle'] - self.robot.get_orientation() + 180) % 360 - 180
            
            # Back up first
            self.robot.move_backward(self.config.BACKWARD_SPEED)
            time.sleep(1)
            self.robot.stop_everything()
            time.sleep(0.2)
            
            # Turn away from obstacle
            if abs(rel_angle) < 90:  # Obstacle is in front
                # Turn in the opposite direction of the obstacle
                if rel_angle > 0:
                    self.robot.turn_left(self.config.TURN_SPEED / 2)
                else:
                    self.robot.turn_right(self.config.TURN_SPEED / 2)
                time.sleep(1)  # Turn for 1 second
                self.robot.stop_everything()
            
            # Update position in map
            self._update_robot_position_in_map()
            
            # Transition back to scanning
            self.state = "SCANNING"
            self.scan_in_progress = False
            print("Avoidance complete, resuming scan.")
        else:
            self.state = "IDLE"
            print("No obstacles to avoid, returning to idle state.")

    def start_new_scan(self):
        """
        Start a new 360-degree scan of the environment.
        """
        if self.scan_in_progress:
            return
            
        print("Starting new 360-degree environment scan...")
        self.scan_in_progress = True
        self.state = "SCANNING"
        self.scan_start_orientation = self.robot.get_orientation()
        self.current_scan_angle = 0
        
        # Start rotating
        self.robot.turn_right(self.config.SCAN_ROTATION_SPEED)

    def continue_scan(self):
        """
        Continue the current scan, checking if we've completed a full rotation.
        """
        if not self.scan_in_progress:
            return
            
        current_orientation = self.robot.get_orientation()
        # Calculate how far we've rotated since starting the scan
        self.current_scan_angle = (current_orientation - self.scan_start_orientation + 360) % 360
        
        # Capture frame and detect obstacles
        frame = self.blacklist.get_current_frame()
        if frame is not None:
            obstacles = self.detect_obstacle(frame)
            for obs in obstacles:
                # Store obstacle information in map storage
                self.map_store.add_obstacle(obs)
            
            # If obstacles are detected and they're close, avoid them
            close_obstacles = [obs for obs in obstacles if obs['distance'] < self.config.SAFE_DISTANCE]
            if close_obstacles:
                self.robot.stop_everything()
                self.avoid_obstacle(close_obstacles)
                return  # Early return as we're now in avoidance mode
        
        # Update robot position in map
        self._update_robot_position_in_map()
        
        # Check if we've completed a full rotation
        if self.current_scan_angle >= self.config.FULL_SCAN_ANGLE:
            print("Scan complete! Rotated a full 360 degrees.")
            self.robot.stop_everything()
            self.scan_in_progress = False
            self.state = "IDLE"

    def cleanup(self):
        """
        Clean up system resources, including robot and camera.
        """
        print("Cleaning up system resources...")
        try:
            if self.robot:
                self.robot.stop_everything()
                self.robot.close()
        except Exception as e:
            print(f"Error during robot cleanup: {e}")
        try:
            if self.blacklist:
                self.blacklist.cleanup()
        except Exception as e:
            print(f"Error during camera cleanup: {e}")
        self.is_running = False
        print("System shut down.")

    def run(self):
        """
        Main loop that continuously scans the environment and detects targets,
        while recording map data.
        """
        print("Security system starting...")
        try:
            while self.is_running:
                current_time = time.time()
                if current_time - self.last_scan_time < self.config.SCAN_INTERVAL:
                    time.sleep(0.05)  # Increased sleep time to reduce CPU usage
                    continue
                self.last_scan_time = current_time

                try:
                    # First, check if we're outside the patrol area
                    if not self.is_within_patrol_area(*self.robot.get_position()):
                        self._return_to_safe_zone()
                        continue
                        
                    # Check if any blacklisted faces are detected in view
                    blacklisted_faces = self.blacklist.getBlackListedFacesInView()
                    if blacklisted_faces:
                        # Process the first detected face
                        print(f"Target detected: {blacklisted_faces[0].get('name', 'Unknown')}")
                        processed = self.process_target(blacklisted_faces[0])
                        if not processed:
                            print("Target not yet processed, continuing to track...")
                    elif self.state == "SCANNING" and self.scan_in_progress:
                        # Continue an in-progress scan
                        self.continue_scan()
                    elif self.state != "AVOIDING":  # Don't start a new scan if we're avoiding obstacles
                        # If no face target is detected and we're not scanning, start a new scan
                        self.start_new_scan()
                        
                    # Update the robot's position in the map
                    self._update_robot_position_in_map()
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    traceback.print_exc()
                    time.sleep(1)
        except KeyboardInterrupt:
            print("User requested system stop.")
        except Exception as e:
            print(f"Critical error: {e}")
            traceback.print_exc()
        finally:
            self.cleanup()
            # Output map data collected during the patrol mission
            map_data = self.map_store.get_map_data()
            print("Map data for this patrol mission:")
            print(map_data)
            print("Map data explanation:")
            print("- 'robot_path': List of robot positions and orientations over time")
            print("- 'obstacles': List of detected obstacles with positions and sizes")
            print("- Use this data for post-mission analysis or to improve patrol routes")

def main():
    try:
        config = Configuration()
        security_system = SecuritySystem(config)
        security_system.run()
    except Exception as e:
        print(f"System failed to start: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()
