import cv2
import numpy as np
from Faces import Faces

class FaceDetector:
    def __init__(self, scale_factor=1.1, min_neighbors=5, min_size=(30, 30)):
        """Initialize the face detector with configurable parameters."""
        # Load face detection classifier
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.cap = None
        self.is_running = False
        
        # Detection parameters
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size
        
        # Verify classifier loading
        if self.face_cascade.empty():
            raise RuntimeError("Error: Couldn't load face cascade classifier")
            
    def start_camera(self, camera_id=0, resolution=(640, 480)):
        """Start the camera with specified settings."""
        try:
            self._cap = cv2.VideoCapture(camera_id)
            if not self._cap.isOpened():
                print("Error: Could not open camera")
                return False
                
            # Set camera properties
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            
            # Verify camera settings
            actual_width = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            self._resolution = (actual_width, actual_height)

            print(f"Camera initialized at resolution: {actual_width}x{actual_height}")
            self.is_running = True
            return True
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False

    def stop_camera(self):
        """Stop the camera and clean up resources."""
        self.is_running = False
        if self._cap is not None:
            self._cap.release()
        cv2.destroyAllWindows()
        
        # Ensure windows are fully closed
        for i in range(5):
            cv2.waitKey(1)

    def _detect_faces(self, frame):
        """Detect faces in the frame."""
        try:
            # Image preprocessing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)  # Improve contrast
            
            # Optional: Add Gaussian blur to reduce noise
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=self.scale_factor,
                minNeighbors=self.min_neighbors,
                minSize=self.min_size,
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            return faces
            
        except Exception as e:
            print(f"Error during face detection: {e}")
            return []



    def getAllFacesInView(self):
        try:
            ret, image = self._cap.read()
            if not ret:
                return False, []
            
            faces = self._detect_faces(image)

            output = []

            for face in faces:
                x, y, w, h = face
                croppedFaceImageData = image[y:y+h, x:x+w]
                output.append(Faces(croppedFaceImageData, x, y, w, h, self._resolution))

            return True, output

        except Exception as e:
            print(f"Error during face aggregation: {e}")
            return False, []