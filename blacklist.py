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
        self._preloaded_encodings = None
        
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
        """Add a face to the blacklist"""
        if metadata is None:
            metadata = {}
            
        # Add timestamp
        metadata['added_on'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        self.blacklist[face_id] = {
            'encoding': face_encoding,
            'metadata': metadata
        }
        
        # Reset preloaded encodings
        self._preloaded_encodings = None
        
        self._save_database()
        return True
        
    def remove_face(self, face_id: str) -> bool:
        """Remove a face from the blacklist"""
        if face_id in self.blacklist:
            del self.blacklist[face_id]
            
            # Reset preloaded encodings
            self._preloaded_encodings = None
            
            self._save_database()
            return True
        return False
    
    def preload_encodings(self):
        """Preload encodings for faster matching during runtime"""
        if not self._preloaded_encodings:
            self._preloaded_encodings = {
                'encodings': [entry['encoding'] for entry in self.blacklist.values()],
                'ids': list(self.blacklist.keys())
            }
        return self._preloaded_encodings
        
    def check_face(self, face_encoding: np.ndarray, tolerance: float = 0.6) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check if a face matches any face in the blacklist (optimized)"""
        if not self.blacklist:
            return False, None, None
            
        # Make sure encodings are preloaded
        preloaded = self.preload_encodings()
        known_encodings = preloaded['encodings']
        face_ids = preloaded['ids']
        
        if not known_encodings:
            return False, None, None
        
        # Basic sanity check to avoid shape mismatch errors
        if isinstance(face_encoding, np.ndarray) and isinstance(known_encodings[0], np.ndarray):
            if face_encoding.shape != known_encodings[0].shape:
                print(f"Warning: Shape mismatch - input: {face_encoding.shape}, reference: {known_encodings[0].shape}")
                return False, None, None
        
        try:    
            # Compare with all known faces
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
            
            if True in matches:
                # Find the matched face_id
                matched_index = matches.index(True)
                matched_face_id = face_ids[matched_index]
                matched_metadata = self.blacklist[matched_face_id]['metadata']
                
                return True, matched_face_id, matched_metadata
        except Exception as e:
            print(f"Error comparing faces: {e}")
            
        return False, None, None
        
    def get_all_faces(self) -> Dict[str, Dict]:
        """Get all faces in the blacklist"""
        return self.blacklist
        
    def encode_face_from_image(self, image_path: str) -> Optional[np.ndarray]:
        """Simplified face encoding from an image file"""
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Try HOG-based detection
            face_locations = face_recognition.face_locations(image)
            
            if face_locations:
                # Use the first face
                face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
                return face_encoding
            
            # If HOG failed, try using OpenCV for detection
            image_cv = cv2.imread(image_path)
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Try with relaxed parameters
            faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
            
            if len(faces) > 0:
                # Extract largest face
                largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                x, y, w, h = largest_face
                
                # Convert to face_recognition format
                top, right, bottom, left = y, x+w, y+h, x
                
                # Get encoding
                face_encoding = face_recognition.face_encodings(image, [(top, right, bottom, left)])[0]
                return face_encoding
                
            print(f"No face found in {image_path}")
            return None
                
        except Exception as e:
            print(f"Error encoding face from image: {e}")
            return None
            
    def encode_face_from_frame(self, frame: np.ndarray, face_location=None) -> Optional[np.ndarray]:
        """Simplified face encoding from a video frame"""
        try:
            # Convert from BGR (OpenCV) to RGB (face_recognition)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # If location provided in OpenCV format (x,y,w,h), convert it
            if face_location is not None and hasattr(face_location, 'x'):
                x, y, w, h = face_location.x, face_location.y, face_location.w, face_location.h
                top, right, bottom, left = y, x+w, y+h, x
                face_location_tuple = (top, right, bottom, left)
            
                # Generate encoding
                face_encoding = face_recognition.face_encodings(rgb_frame, [face_location_tuple])[0]
                return face_encoding
            else:
                # No location provided, do full detection
                face_locations = face_recognition.face_locations(rgb_frame)
                if face_locations:
                    face_encoding = face_recognition.face_encodings(rgb_frame, [face_locations[0]])[0]
                    return face_encoding
                
            return None
            
        except Exception as e:
            print(f"Error encoding face from frame: {e}")
            return None


def convert_opencv_face_to_face_recognition(face, frame_height):
    """Convert OpenCV face coordinates to face_recognition format"""
    left = face.x
    top = face.y
    right = face.x + face.w
    bottom = face.y + face.h
    
    return (top, right, bottom, left)


def check_face_against_blacklist(blacklist_db, frame, face, tolerance=0.6):
    """Check if a detected face is in the blacklist (lightweight version)"""
    try:
        # Convert to RGB once here to avoid multiple conversions
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Extract face location
        x, y, w, h = face.x, face.y, face.w, face.h
        top, right, bottom, left = y, x+w, y+h, x
        
        # Generate encoding
        face_encodings = face_recognition.face_encodings(rgb_frame, [(top, right, bottom, left)])
        
        if not face_encodings:
            return False, None, None
            
        face_encoding = face_encodings[0]
        
        # Check against blacklist
        return blacklist_db.check_face(face_encoding, tolerance=tolerance)
    except Exception as e:
        print(f"Error checking face against blacklist: {e}")
        return False, None, None
