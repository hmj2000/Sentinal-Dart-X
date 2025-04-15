import cv2
import numpy as np
import os
import time
import gc
from blacklist import BlacklistDatabase, check_face_against_blacklist

class SimpleFace:
    """Simple face class for testing, similar to Face in FaceBuffer"""
    def __init__(self, x, y, w, h, face_id=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.faceId = face_id
        self.framesSinceLastSeen = 0

def setup_camera(camera_index=0):
    """Initialize camera with settings optimized for shorter range detection"""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        exit()
    
    # Use moderate resolution for better accuracy at short range
    width = 426
    height = 320
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, 15)  # Reduced FPS
    
    return cap, width, height

def calculate_distance(face_width, focal_length=400):
    """Calculate estimated distance based on face width"""
    face_width_cm = 15  # Average human face width in cm
    return (face_width_cm * focal_length) / (face_width * 10)  # in meters

def draw_faces(frame, faces, blacklisted_faces=None, focal_length=400):
    """Draw detected faces with distance estimation and blacklist status"""
    if blacklisted_faces is None:
        blacklisted_faces = {}
    
    for face_id, face in faces.items():
        # Calculate distance - calibrated for 0-4m range
        estimated_distance = calculate_distance(face.w, focal_length)
        
        # Highlight faces within 4m range
        in_target_range = estimated_distance <= 4.0
        
        # Mark blacklisted faces with red color
        if face_id in blacklisted_faces:
            color = (0, 0, 255)  # Red
            name = blacklisted_faces[face_id].get('name', 'Unknown')
            cv2.putText(frame, f"MATCH: {name}", (face.x, face.y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, "FIRE", (face.x, face.y + face.h + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
        elif in_target_range:
            # Yellow for faces in the 0-4m range but not blacklisted
            color = (0, 255, 255)
        else:
            # Green for normal faces outside target range
            color = (0, 255, 0)
        
        # Draw rectangle around face
        cv2.rectangle(frame, (face.x, face.y), (face.x + face.w, face.y + face.h), color, 2)
        
        # Add face ID
        cv2.putText(frame, f"ID: {face_id}", (face.x, face.y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Add estimated distance with color coding for target range
        distance_color = (0, 255, 255) if in_target_range else (255, 255, 255)
        cv2.putText(frame, f"{estimated_distance:.1f}m", 
                   (face.x, face.y + face.h + 15), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, distance_color, 1, cv2.LINE_AA)
        
        # Show face size in pixels
        cv2.putText(frame, f"{face.w}x{face.h}px", 
                   (face.x + face.w + 5, face.y), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.4, (255, 255, 255), 1, cv2.LINE_AA)

def main():
    print("Starting Blacklist Test with 0-4m Range Detection")
    
    # Set OpenCV environment variables for better performance on ARM devices
    os.environ['OPENCV_OPENCL_RUNTIME'] = ''  # Disable OpenCL
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'  # Disable debug info
    
    # Initialize blacklist database
    print("Loading blacklist database...")
    blacklist_db = BlacklistDatabase()
    
    # Print number of faces in blacklist
    faces = blacklist_db.get_all_faces()
    print(f"Loaded {len(faces)} faces from blacklist")
    
    if len(faces) == 0:
        print("Warning: Blacklist is empty. Please add faces first with blacklist_manager.py")
        cont = input("Continue anyway? (y/n): ")
        if cont.lower() != 'y':
            return
    
    # Initialize camera
    print("Setting up camera...")
    cap, width, height = setup_camera()
    
    # Initialize face cascade classifier
    print("Loading face detector...")
    # For short range, the default classifier works well
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Performance monitoring
    frame_times = []
    last_time = time.time()
    start_time = time.time()
    frames = 0
    
    # Face tracking variables
    next_face_id = 0
    tracked_faces = {}  # face_id -> SimpleFace
    current_blacklisted_faces = {}  # face_id -> metadata (raw/unstable matches)
    stable_blacklisted_faces = {}   # face_id -> metadata (stable matches)
    face_match_counters = {}        # face_id -> consecutive match count
    face_recognition_cache = {}     # face_id -> [is_match, blacklist_id, metadata, ttl]
    
    # Stability thresholds - addresses flickering
    stable_match_threshold = 2      # Need 2 consecutive matches to be stable (reduced from 3)
    stable_unmatch_threshold = -4   # Need 4 consecutive non-matches to remove from stable (reduced from 6)
    cache_lifetime = 30             # Cache lifetime in frames (reduced from 45)
    
    # Distance and detection parameters
    check_blacklist_frame_counter = 0
    check_blacklist_frequency = 5  # Check every 5 frames (reduced from 10)
    
    # Camera parameters
    focal_length = 400  # Define focal length here for use throughout the function
    
    # These values are calibrated for 0-4m range
    face_width_cm = 15  # Average human face width in cm
    min_check_distance = 0.0  # meters - Minimum distance to check (changed from 3.0 to 0)
    max_check_distance = 4.0  # meters - Maximum distance to check
    
    processing_scale = 1.0  # No downscaling for short range accuracy
    
    print("Press 'q' to exit, 's' to save current frame")
    print("Starting main loop...")
    
    frame_count = 0
    saved_frame_count = 0
    
    while True:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        frames += 1
        frame_count += 1
        
        if current_time - start_time > 5:  # Update FPS every 5 seconds
            fps = frames / (current_time - start_time)
            print(f"FPS: {fps:.1f}")
            frames = 0
            start_time = current_time
        
        # Trigger garbage collection periodically
        if frame_count % 300 == 0:  # Every 300 frames
            gc.collect()
        
        # Read frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # Process frame - no downscaling for short range
        process_frame = frame.copy()
        
        # Convert to grayscale
        gray = cv2.cvtColor(process_frame, cv2.COLOR_BGR2GRAY)
        
        # Apply light contrast enhancement
        gray = cv2.equalizeHist(gray)
        
        # Calculate min face size for 4m (furthest detection range)
        min_face_width_4m = int((face_width_cm * focal_length) / (4.0 * 10))
        min_face_size = (min_face_width_4m, min_face_width_4m)
        
        # Detect faces with parameters optimized for shorter range
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1,  # Lower for better detection at short range
            minNeighbors=4,   # Slightly higher for fewer false positives
            minSize=min_face_size,  # Calibrated for 4m
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Release processing frames to free memory
        del process_frame
        del gray
        
        # Update tracked faces
        # First mark all as not seen in this frame
        for face_id in tracked_faces:
            tracked_faces[face_id].framesSinceLastSeen += 1
        
        # Now update with new detections
        for (x, y, w, h) in faces:
            # Check if this face matches any existing tracked face
            matched = False
            for face_id, face in list(tracked_faces.items()):
                # Simple distance-based matching
                center_x1 = face.x + face.w/2
                center_y1 = face.y + face.h/2
                center_x2 = x + w/2
                center_y2 = y + h/2
                
                distance = np.sqrt((center_x1 - center_x2)**2 + (center_y1 - center_y2)**2)
                
                # If centers are close, consider it the same face
                if distance < (face.w + w)/3:  # Threshold based on face size
                    # Update face position
                    face.x = x
                    face.y = y
                    face.w = w
                    face.h = h
                    face.framesSinceLastSeen = 0
                    matched = True
                    break
            
            # If no match found, add as new face
            if not matched:
                tracked_faces[next_face_id] = SimpleFace(x, y, w, h, next_face_id)
                next_face_id += 1
        
        # Remove faces not seen for too long
        for face_id in list(tracked_faces.keys()):
            if tracked_faces[face_id].framesSinceLastSeen > 15:  # Remove after 15 frames (~1 second)
                del tracked_faces[face_id]
                if face_id in face_recognition_cache:
                    del face_recognition_cache[face_id]
                if face_id in face_match_counters:
                    del face_match_counters[face_id]
                if face_id in stable_blacklisted_faces:
                    del stable_blacklisted_faces[face_id]
        
        # Update face recognition cache TTL
        for face_id in list(face_recognition_cache.keys()):
            face_recognition_cache[face_id][3] -= 1
            if face_recognition_cache[face_id][3] <= 0:
                del face_recognition_cache[face_id]
        
        # Reset blacklisted faces for this frame
        current_blacklisted_faces = {}
        
        # Check blacklist periodically
        check_blacklist_frame_counter += 1
        if check_blacklist_frame_counter >= check_blacklist_frequency:
            check_blacklist_frame_counter = 0
            
            # Check tracked faces against blacklist
            for face_id, face in tracked_faces.items():
                # Check if already in cache
                if face_id in face_recognition_cache:
                    is_match, blacklist_id, metadata = face_recognition_cache[face_id][:3]
                    if is_match:
                        current_blacklisted_faces[face_id] = metadata
                        continue
                
                # Calculate estimated distance
                est_distance = calculate_distance(face.w, focal_length)
                
                # Check if within target range (0-4m)
                if min_check_distance <= est_distance <= max_check_distance:
                    try:
                        # Convert SimpleFace to format expected by check_face_against_blacklist
                        is_match, blacklist_id, metadata = check_face_against_blacklist(
                            blacklist_db, frame, face, tolerance=0.7)  # Increased tolerance
                        
                        # Cache the result
                        face_recognition_cache[face_id] = [is_match, blacklist_id, metadata, cache_lifetime]
                        
                        if is_match:
                            current_blacklisted_faces[face_id] = metadata
                            print(f"Blacklisted face detected at estimated distance: {est_distance:.1f}m")
                    except Exception as e:
                        print(f"Error checking face against blacklist: {e}")
        
        # Update stable blacklist tracking to prevent flickering
        tracked_face_ids = list(tracked_faces.keys())
        
        # Remove faces that are no longer tracked
        for face_id in list(face_match_counters.keys()):
            if face_id not in tracked_face_ids:
                del face_match_counters[face_id]
                if face_id in stable_blacklisted_faces:
                    del stable_blacklisted_faces[face_id]
        
        # Update match counters for each face
        for face_id in tracked_face_ids:
            if face_id in current_blacklisted_faces:
                # If face is in current blacklist, increment counter
                face_match_counters[face_id] = face_match_counters.get(face_id, 0) + 1
                
                # If counter reaches threshold, add to stable blacklist
                if face_match_counters[face_id] >= stable_match_threshold:
                    stable_blacklisted_faces[face_id] = current_blacklisted_faces[face_id]
            else:
                # If face is not in current blacklist, decrement counter
                face_match_counters[face_id] = face_match_counters.get(face_id, 0) - 1
                
                # If counter goes below negative threshold, remove from stable blacklist
                if face_match_counters[face_id] <= stable_unmatch_threshold and face_id in stable_blacklisted_faces:
                    del stable_blacklisted_faces[face_id]
        
        # Create display frame
        display_frame = frame.copy()
        
        # Draw tracked faces using the stable blacklist results
        draw_faces(display_frame, tracked_faces, stable_blacklisted_faces, focal_length)
        
        # Add debugging information
        cv2.putText(display_frame, f"Tracked faces: {len(tracked_faces)}", (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
        
        elapsed = time.time() - start_time
        if elapsed > 0:
            fps = frames / elapsed if elapsed > 0 else 0
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 40), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
        
        # Draw target range indicator (0-4m)
        cv2.putText(display_frame, "TARGET RANGE: 0-4.0m", 
                   (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        
        # Add range markers - face size at 4m distance
        ref_width_4m = int(15 * focal_length / (4.0 * 10))  # Width of face at 4m
        
        cv2.rectangle(display_frame, (10, height - 20), (10 + ref_width_4m, height - 10), (0, 255, 255), 2)
        cv2.putText(display_frame, "4m", (10 + ref_width_4m + 5, height - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        
        # Add stability counters for debugging
        for face_id, face in tracked_faces.items():
            if face_id in face_match_counters:
                counter_value = face_match_counters[face_id]
                is_stable = "Yes" if face_id in stable_blacklisted_faces else "No"
                is_current = "Yes" if face_id in current_blacklisted_faces else "No"
                cv2.putText(display_frame, f"C:{counter_value} S:{is_stable} Curr:{is_current}", 
                          (face.x, face.y + face.h + 45), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, cv2.LINE_AA)
        
        # Show frame
        cv2.imshow('Blacklist Test (0-4m Range)', display_frame)
        
        # Process keypresses
        key = cv2.waitKey(1) & 0xFF
        
        # 'q' to quit
        if key == ord('q'):
            break
            
        # 's' to save current frame
        elif key == ord('s'):
            filename = f'captured_frame_{saved_frame_count}.jpg'
            cv2.imwrite(filename, display_frame)
            print(f"Saved frame to {filename}")
            saved_frame_count += 1
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print("Test complete")

if __name__ == "__main__":
    main()
