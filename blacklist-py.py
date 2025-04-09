import pickle
import os
import face_recognition
import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional, Union
import uuid
from datetime import datetime

class BlacklistDatabase:
    def __init__(self, pickle_path: str = "blacklist.pickle"):
        """Initialize the blacklist database"""
        self.pickle_path = pickle_path
        self.blacklist = self._load_database()
        
    def _load_database(self) -> Dict[str, Dict]:
        """Load blacklist database from pickle file"""
        if os.path.exists(self.pickle_path):
            try:
                with open(self.pickle_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading blacklist database: {e}")
                return {}
        else:
            return {}
            
    def _save_database(self) -> None:
        """Save blacklist database to pickle file"""
        with open(self.pickle_path, 'wb') as f:
            pickle.dump(self.blacklist, f)
            
    def add_face(self, face_id: str, face_encoding: np.ndarray, metadata: Dict = None) -> bool:
        """Add a face to the blacklist
        
        Args:
            face_id: Unique identifier for the face
            face_encoding: Face encoding/embedding vector
            metadata: Additional information about the person (name, notes, etc.)
            
        Returns:
            bool: True if successfully added
        """
        if metadata is None:
            metadata = {}
            
        # Add timestamp
        metadata['added_on'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        self.blacklist[face_id] = {
            'encoding': face_encoding,
            'metadata': metadata
        }
        
        self._save_database()
        return True
        
    def remove_face(self, face_id: str) -> bool:
        """Remove a face from the blacklist
        
        Args:
            face_id: Unique identifier for the face
            
        Returns:
            bool: True if successfully removed
        """
        if face_id in self.blacklist:
            del self.blacklist[face_id]
            self._save_database()
            return True
        return False
        
    def check_face(self, face_encoding: np.ndarray, tolerance: float = 0.6) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check if a face matches any face in the blacklist
        
        Args:
            face_encoding: Face encoding/embedding vector to check
            tolerance: Strictness of face comparison (lower is stricter)
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]: 
                - Whether the face matches a blacklisted face
                - face_id if matched, None otherwise
                - metadata if matched, None otherwise
        """
        if not self.blacklist:
            return False, None, None
            
        # Convert to list format required by face_recognition library
        known_encodings = [entry['encoding'] for entry in self.blacklist.values()]
        
        if not known_encodings:
            return False, None, None
            
        # Compare with all known faces
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
        
        if True in matches:
            # Find the matched face_id
            face_ids = list(self.blacklist.keys())
            matched_index = matches.index(True)
            matched_face_id = face_ids[matched_index]
            matched_metadata = self.blacklist[matched_face_id]['metadata']
            
            return True, matched_face_id, matched_metadata
            
        return False, None, None
        
    def get_all_faces(self) -> Dict[str, Dict]:
        """Get all faces in the blacklist
        
        Returns:
            Dict: Dictionary of all faces keyed by face_id
        """
        return self.blacklist
        
    def encode_face_from_image(self, image_path: str) -> Optional[np.ndarray]:
        """Generate face encoding from an image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            np.ndarray: Face encoding vector, None if no face found
        """
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                print(f"No face found in {image_path}")
                return None
                
            # If multiple faces found, use the first one
            face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
            return face_encoding
            
        except Exception as e:
            print(f"Error encoding face from image: {e}")
            return None
            
    def encode_face_from_frame(self, frame: np.ndarray, face_location=None) -> Optional[np.ndarray]:
        """Generate face encoding from a video frame
        
        Args:
            frame: OpenCV frame/image
            face_location: Optional face location tuple (top, right, bottom, left)
            
        Returns:
            np.ndarray: Face encoding vector, None if no face found
        """
        try:
            # Convert from BGR (OpenCV) to RGB (face_recognition)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations if not provided
            if face_location is None:
                face_locations = face_recognition.face_locations(rgb_frame)
                if not face_locations:
                    return None
                face_location = face_locations[0]
            
            # Generate encoding
            face_encoding = face_recognition.face_encodings(rgb_frame, [face_location])[0]
            return face_encoding
            
        except Exception as e:
            print(f"Error encoding face from frame: {e}")
            return None


def convert_opencv_face_to_face_recognition(face, frame_height):
    """
    Convert OpenCV face coordinates (x, y, w, h) to face_recognition format (top, right, bottom, left)
    
    Args:
        face: Face object with x, y, w, h attributes
        frame_height: Height of the frame
        
    Returns:
        tuple: (top, right, bottom, left)
    """
    left = face.x
    top = face.y
    right = face.x + face.w
    bottom = face.y + face.h
    
    return (top, right, bottom, left)


def check_face_against_blacklist(blacklist_db, frame, face, tolerance=0.6):
    """
    Check if a detected face is in the blacklist
    
    Args:
        blacklist_db: BlacklistDatabase instance
        frame: Current video frame
        face: Face object with x, y, w, h attributes
        tolerance: Face matching tolerance
        
    Returns:
        tuple: (is_match, face_id, metadata)
    """
    # Convert face coordinates
    height, width = frame.shape[:2]
    face_location = convert_opencv_face_to_face_recognition(face, height)
    
    # Get face encoding
    face_encoding = blacklist_db.encode_face_from_frame(frame, face_location)
    
    if face_encoding is None:
        return False, None, None
    
    # Compare with blacklist
    return blacklist_db.check_face(face_encoding, tolerance=tolerance)
