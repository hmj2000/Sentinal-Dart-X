import os
import argparse
import uuid
import cv2
import numpy as np
from blacklist import BlacklistDatabase

def add_face_from_image(blacklist_db, image_path, name=None, notes=None, detection_method='default'):
    """Add a face from an image file to the blacklist with improved detection"""
    print(f"Adding face from image: {image_path}")
    print(f"Using detection method: {detection_method}")
    
    face_encoding = blacklist_db.encode_face_from_image(image_path, detection_method)
    
    if face_encoding is None:
        print(f"Could not find a face in {image_path}")
        print("Try using a different detection method:")
        print("  --method relaxed : More lenient face detection")
        print("  --method hog : Standard HOG-based detection")
        print("  --method cnn : More accurate CNN-based detection (slower)")
        print("Or try a different photo with a clearer face")
        return False
    
    # Create metadata
    metadata = {}
    if name:
        metadata['name'] = name
    if notes:
        metadata['notes'] = notes
    
    # Generate unique ID for the face
    face_id = str(uuid.uuid4())
    
    # Add to blacklist
    success = blacklist_db.add_face(face_id, face_encoding, metadata)
    
    if success:
        print(f"Added face ID: {face_id} to blacklist" + (f" (Name: {name})" if name else ""))
    else:
        print("Failed to add face to blacklist")
    
    return success

def remove_face(blacklist_db, face_id):
    """Remove a face from the blacklist by ID"""
    success = blacklist_db.remove_face(face_id)
    
    if success:
        print(f"Removed face ID: {face_id} from blacklist")
    else:
        print(f"Could not find face ID: {face_id} in blacklist")
    
    return success

def list_faces(blacklist_db):
    """List all faces in the blacklist"""
    faces = blacklist_db.get_all_faces()
    
    if not faces:
        print("Blacklist is empty")
        return
    
    print(f"Found {len(faces)} faces in blacklist:")
    for face_id, data in faces.items():
        metadata = data['metadata']
        name = metadata.get('name', 'Unknown')
        notes = metadata.get('notes', '')
        added_on = metadata.get('added_on', 'Unknown time')
        print(f"ID: {face_id} | Name: {name} | Added: {added_on}" + (f" | Notes: {notes}" if notes else ""))

def capture_face(output_path=None):
    """Capture a face from webcam for adding to blacklist"""
    print("Capturing face from webcam")
    print("Position your face in the frame")
    print("Press SPACE to capture, ESC to cancel")
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return None
    
    # Initialize face cascade
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    captured_image = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        
        # Draw face rectangles
        display_frame = frame.copy()
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Add instructions
        cv2.putText(display_frame, "SPACE: Capture | ESC: Cancel", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Display the number of faces detected
        cv2.putText(display_frame, f"Detected: {len(faces)} faces", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Show frame
        cv2.imshow('Capture Face', display_frame)
        
        # Process key presses
        key = cv2.waitKey(1)
        
        # ESC key - exit
        if key == 27:
            print("Cancelled")
            break
            
        # SPACE key - capture
        elif key == 32:
            if len(faces) > 0:
                captured_image = frame.copy()
                print("Face captured!")
                break
            else:
                print("No face detected. Please position your face in the frame.")
    
    # Release webcam and close windows
    cap.release()
    cv2.destroyAllWindows()
    
    # If image was captured and output path provided, save it
    if captured_image is not None and output_path:
        cv2.imwrite(output_path, captured_image)
        print(f"Saved captured image to {output_path}")
    
    return captured_image

def test_detection_methods(image_path):
    """Test different face detection methods on an image"""
    print(f"Testing face detection methods on: {image_path}")
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image: {image_path}")
        return
    
    # Display original image
    cv2.imshow("Original Image", image)
    cv2.waitKey(1000)
    
    # Test methods
    methods = [
        ("Standard HOG", "hog"),
        ("Relaxed OpenCV", "relaxed"),
        ("CNN (if available)", "cnn")
    ]
    
    db = BlacklistDatabase()
    
    for name, method in methods:
        print(f"\nTrying method: {name}")
        try:
            # Attempt to encode
            face_encoding = db.encode_face_from_image(image_path, detection_method=method)
            
            if face_encoding is not None:
                print(f"SUCCESS: {name} method detected a face")
                print(f"Check 'detected_face.jpg' or 'detected_face_alt.jpg' for the detected face")
            else:
                print(f"FAILED: {name} method did not detect any face")
        except Exception as e:
            print(f"ERROR with {name} method: {e}")
    
    cv2.destroyAllWindows()
    print("\nTest complete. If any method succeeded, use it with --method parameter.")

def main():
    parser = argparse.ArgumentParser(description='Manage face recognition blacklist database')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add face parser
    add_parser = subparsers.add_parser('add', help='Add a face to the blacklist')
    add_parser.add_argument('image_path', help='Image file path')
    add_parser.add_argument('--name', help='Person name')
    add_parser.add_argument('--notes', help='Additional notes')
    add_parser.add_argument('--method', choices=['default', 'relaxed', 'hog', 'cnn'], 
                           default='default', help='Face detection method')
    
    # Remove face parser
    remove_parser = subparsers.add_parser('remove', help='Remove a face from the blacklist')
    remove_parser.add_argument('face_id', help='Face ID to remove')
    
    # List faces parser
    list_parser = subparsers.add_parser('list', help='List all faces in the blacklist')
    
    # Capture face parser
    capture_parser = subparsers.add_parser('capture', help='Capture a face from webcam')
    capture_parser.add_argument('--name', help='Person name')
    capture_parser.add_argument('--notes', help='Additional notes')
    capture_parser.add_argument('--output', help='Save captured image to file')
    
    # Test detection methods parser
    test_parser = subparsers.add_parser('test', help='Test face detection methods on an image')
    test_parser.add_argument('image_path', help='Image file path')
    
    args = parser.parse_args()
    
    # Initialize blacklist database
    blacklist_db = BlacklistDatabase()
    
    if args.command == 'add':
        add_face_from_image(blacklist_db, args.image_path, args.name, args.notes, args.method)
    elif args.command == 'remove':
        remove_face(blacklist_db, args.face_id)
    elif args.command == 'list':
        list_faces(blacklist_db)
    elif args.command == 'capture':
        # Capture face from webcam
        output_path = args.output or "captured_face.jpg"
        captured_image = capture_face(output_path)
        
        if captured_image is not None:
            # Ask if the user wants to add the captured face to the blacklist
            choice = input("Add captured face to blacklist? (y/n): ")
            if choice.lower() == 'y':
                name = args.name or input("Enter name for this person: ")
                notes = args.notes
                
                # Try different methods until one works
                methods = ['default', 'relaxed', 'hog']
                for method in methods:
                    print(f"\nTrying {method} detection method...")
                    if add_face_from_image(blacklist_db, output_path, name, notes, method):
                        break
    elif args.command == 'test':
        test_detection_methods(args.image_path)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
