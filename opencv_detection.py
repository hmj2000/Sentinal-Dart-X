import cv2
import numpy as np

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
            self.cap = cv2.VideoCapture(camera_id)
            if not self.cap.isOpened():
                print("Error: Could not open camera")
                return False
                
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            
            # Verify camera settings
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            print(f"Camera initialized at resolution: {actual_width}x{actual_height}")
            self.is_running = True
            return True
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False

    def stop_camera(self):
        """Stop the camera and clean up resources."""
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        
        # Ensure windows are fully closed
        for i in range(5):
            cv2.waitKey(1)

    def detect_faces(self, frame):
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

    def draw_faces(self, frame, faces):
        """Draw rectangles around detected faces."""
        try:
            for (x, y, w, h) in faces:
                # Draw face rectangle
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # Optional: Add face size information
                face_size = f"Size: {w}x{h}"
                cv2.putText(frame, face_size, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Add face count
            cv2.putText(frame, f"Faces: {len(faces)}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            return frame
            
        except Exception as e:
            print(f"Error drawing faces: {e}")
            return frame

    def process_frame(self):
        """Process a single frame."""
        if not self.is_running or self.cap is None:
            return False, None

        try:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                return False, None

            # Detect and draw faces
            faces = self.detect_faces(frame)
            processed_frame = self.draw_faces(frame, faces)
            
            return True, processed_frame
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return False, None

    def run(self, window_name='Face Detection'):
        """Run the main detection loop."""
        if not self.start_camera():
            return

        print("\nFace detection started.")
        print("Controls:")
        print("- Press 'q' or 'ESC' to exit")
        
        while self.is_running:
            success, frame = self.process_frame()
            if not success:
                break

            cv2.imshow(window_name, frame)

            # Handle keyboard input
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') or key == ord('Q') or key == 27:  # q, Q, or ESC
                print("\nExit requested by user")
                break

            # Check if window was closed
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                print("\nWindow closed by user")
                break

        self.stop_camera()

# Example usage
if __name__ == '__main__':
    try:
        # Create detector with default parameters
        detector = FaceDetector()
        detector.run()
    except Exception as e:
        print(f"An error occurred: {e}")