"""
map_store.py
Used to store the map information collected during the current execution,
including obstacles, robot path, and other terrain features.
This data will be cleared when the system shuts down.
"""

import time

class MapStore:
    def __init__(self):
        # Store obstacle information; each obstacle is a dictionary, e.g.,
        # {'id': 'obs1', 'position': (x, y), 'size': (width, height)}
        self.obstacles = []
        
        # Store other terrain features with a similar dictionary format
        self.features = []
        
        # Store robot position history as a list of tuples (timestamp, position, orientation)
        self.robot_path = []
        
        # Current robot position and orientation
        self.robot_position = None
        self.robot_orientation = None
    
    def add_obstacle(self, obstacle):
        """
        Add an obstacle's information.
        Args:
            obstacle (dict): The obstacle information, which must include keys like 'id', 'position', and 'size'.
        """
        # Check if obstacle contains the required keys
        required_keys = ['id', 'position', 'size']
        if not all(key in obstacle for key in required_keys):
            print(f"Warning: Obstacle missing required keys. Required: {required_keys}, Got: {list(obstacle.keys())}")
            return
            
        # Add the obstacle with a timestamp
        obstacle_with_timestamp = obstacle.copy()
        obstacle_with_timestamp['timestamp'] = time.time()
        
        # Check if we already have an obstacle with the same ID
        for i, existing in enumerate(self.obstacles):
            if existing['id'] == obstacle['id']:
                # Update existing obstacle instead of adding a new one
                self.obstacles[i] = obstacle_with_timestamp
                return
                
        self.obstacles.append(obstacle_with_timestamp)
    
    def add_feature(self, feature):
        """
        Add terrain feature information.
        Args:
            feature (dict): For example, {'id': 'wall1', 'position': (x, y), 'description': 'wall'}.
        """
        # Check if feature contains the required keys
        required_keys = ['id', 'position']
        if not all(key in feature for key in required_keys):
            print(f"Warning: Feature missing required keys. Required: {required_keys}, Got: {list(feature.keys())}")
            return
            
        # Add the feature with a timestamp
        feature_with_timestamp = feature.copy()
        feature_with_timestamp['timestamp'] = time.time()
        
        # Check if we already have a feature with the same ID
        for i, existing in enumerate(self.features):
            if existing['id'] == feature['id']:
                # Update existing feature instead of adding a new one
                self.features[i] = feature_with_timestamp
                return
                
        self.features.append(feature_with_timestamp)
    
    def update_robot_position(self, position, orientation):
        """
        Update the current robot position and orientation, and add it to the robot path history.
        
        Args:
            position (tuple): The (x, y) coordinates of the robot.
            orientation (float): The orientation angle in degrees.
        """
        # Update current position and orientation
        self.robot_position = position
        self.robot_orientation = orientation
        
        # Add to path history with timestamp
        timestamp = time.time()
        self.robot_path.append({
            'timestamp': timestamp,
            'position': position,
            'orientation': orientation
        })
        
        # Optionally, limit the path history to prevent excessive memory usage
        # Uncomment the following code if needed:
        # max_path_length = 1000  # Adjust based on your needs
        # if len(self.robot_path) > max_path_length:
        #     self.robot_path = self.robot_path[-max_path_length:]
    
    def get_map_data(self):
        """
        Return the currently stored map data.
        """
        return {
            'obstacles': self.obstacles,
            'features': self.features,
            'robot_path': self.robot_path,
            'current_position': self.robot_position,
            'current_orientation': self.robot_orientation
        }
    
    def get_nearby_obstacles(self, position, radius):
        """
        Get obstacles that are within a certain radius of the given position.
        
        Args:
            position (tuple): The (x, y) coordinates to check from.
            radius (float): The radius within which to find obstacles.
            
        Returns:
            list: A list of obstacles within the specified radius.
        """
        nearby = []
        for obstacle in self.obstacles:
            # Calculate distance from position to obstacle
            obs_pos = obstacle['position']
            distance = ((position[0] - obs_pos[0])**2 + (position[1] - obs_pos[1])**2)**0.5
            if distance <= radius:
                # Add distance information to the obstacle
                obs_with_distance = obstacle.copy()
                obs_with_distance['distance_from_point'] = distance
                nearby.append(obs_with_distance)
        
        # Sort by distance
        return sorted(nearby, key=lambda x: x['distance_from_point'])
    
    def clear(self):
        """
        Clear all stored map information.
        """
        self.obstacles.clear()
        self.features.clear()
        self.robot_path.clear()
        self.robot_position = None
        self.robot_orientation = None
