import cv2
from Constants import Constants
from FaceBuffer import FaceBuffer, RawFace, Face
from Commands import Commands
from Sound import Sound
from blacklist import BlacklistDatabase, check_face_against_blacklist
import time
import os
import gc
import numpy as np

def debug():
    return Constants.mode == "debug"

def deployed():
    return Constants.mode == "deployed"

def setupCaptureDevice():
    cap = cv2.VideoCapture(Constants.cameraIndex)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        exit()
    
    # Use moderate resolution for better accuracy at short range
    reduced_width = 426
    reduced_height = 320
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, reduced_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, reduced_height)
    cap.set(cv2.CAP_PROP_FPS, 15)  # Reduced FPS
    
    # Update constants to match the actual resolution we're using
    Constants.captureResolutionWidth = reduced_width
    Constants.captureResolutionHeight = reduced_height
    
    return cap

def calculate_distance(face_width, focal_length=400):
    """Calculate estimated distance based on face width
    
    Args:
        face_width: Width of face in pixels
        focal_length: Camera focal length parameter
        
    Returns:
        float: Estimated distance in meters
    """
    face_width_cm = 15  # Average human face width in cm
    return (face_width_cm * focal_length) / (face_width * 10)  # in meters

def drawTrackedFaces(faces, resizedFrame, blacklisted_faces=None, focal_length=400):
    if blacklisted_faces is None:
        blacklisted_faces = {}
        
    for face in faces:
        # Calculate distance
        estimated_distance = calculate_distance(face.w, focal_length)
        
        # Check if in target range (4m or less)
        in_target_range = estimated_distance <= 4.0
        
        # Mark blacklisted faces with red color
        if face.faceId in blacklisted_faces:
            color = (0, 0, 255)  # Red
            name = blacklisted_faces[face.faceId].get('name', 'Unknown')
            cv2.putText(resizedFrame, f"TARGET: {name}", (face.x, face.y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        elif in_target_range:
            # Yellow for faces within 4m range
            color = (0, 255, 255)
        else:
            # Green for normal faces outside target range
            color = (0, 255, 0)
            
        cv2.rectangle(resizedFrame, (face.x, face.y), (face.x + face.w, face.y + face.h), color, 2)
        cv2.putText(resizedFrame, str(face.faceId), (face.x, face.y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Add distance information
        distance_color = (0, 255, 255) if in_target_range else (255, 255, 255)
        cv2.putText(resizedFrame, f"{estimated_distance:.1f}m", 
                   (face.x, face.y + face.h + 15), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, distance_color, 1, cv2.LINE_AA)

def displayFrame(frame):
    cv2.imshow('Sentinel Dart X', frame)
    key = cv2.waitKey(1)
    return key

def loop(faceCascade, cap, fb, s, cs, blacklist_db):
    # Store blacklisted faces in current frame
    current_blacklisted_faces = {}
    
    # Stable blacklist tracking - addresses flickering issue
    stable_blacklisted_faces = {}  # Stores faces that have consistently matched
    stable_match_threshold = 2     # Reduced from 3 to 2 for faster confirmation
    face_match_counters = {}       # Tracks consecutive matches per face
    stable_unmatch_threshold = -4  # Reduced from -6 to -4 for quicker removal
    
    # Blacklist check frequency control
    check_blacklist_frame_counter = 0
    check_blacklist_frequency = 5  # Reduced from 10 to 5 for more frequent checks
    
    # Performance monitoring
    frame_times = []
    last_time = time.time()
    start_time = time.time()
    frames = 0
    
    # Camera and distance parameters
    focal_length = 400  # Define focal length here for distance calculations
    face_width_cm = 15  # Average human face width in cm
    max_check_distance = 4.0  # meters - Maximum distance to check
    min_check_distance = 0.0  # meters - Changed from 3.0 to 0.0 (no minimum)
    
    # Face detection variables
    scale_factor = 1.1  # Lower for better detection at short range
    min_neighbors = 4   # Balanced for short range
    
    # Processing parameters
    processing_scale = 1.0  # No downscaling for short range accuracy
    
    # Face recognition cache
    face_recognition_cache = {}  # face_id -> (result, metadata, last_frame)
    cache_lifetime = 30  # frames - reduced from 45 to 30 for quicker updates
    
    # Memory management
    last_gc_collect = time.time()
    
    print("Starting main loop with 4m range optimization...")
    
    while True:
        # Calculate FPS
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        frames += 1
        if current_time - start_time > 5:  # Update FPS every 5 seconds
            print(f"FPS: {frames / (current_time - start_time):.1f}")
            frames = 0
            start_time = current_time
        
        # Trigger garbage collection periodically
        if current_time - last_gc_collect > 30:  # Every 30 seconds
            gc.collect()
            last_gc_collect = current_time
        
        ret, frame = cap.read()
        
        if not ret:
            print("Failed to grab frame")
            break
        
        # Process at original resolution for short range
        process_frame = frame.copy()
        
        # Convert to grayscale
        gray = cv2.cvtColor(process_frame, cv2.COLOR_BGR2GRAY)
        
        # Apply contrast enhancement for better face detection
        gray = cv2.equalizeHist(gray)
        
        # Calculate min face size for 4m distance (furthest detection range)
        min_face_width_4m = int((face_width_cm * focal_length) / (4.0 * 10))
        min_face_size = (min_face_width_4m, min_face_width_4m)
        
        # Detect faces with parameters optimized for shorter range
        faces = faceCascade.detectMultiScale(
            gray, 
            scaleFactor=scale_factor, 
            minNeighbors=min_neighbors,
            minSize=min_face_size,  # Calibrated for 4m
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Release the processing frames to save memory
        del process_frame
        del gray
        
        rawFaces = [RawFace(face[0], face[1], face[2], face[3]) for face in faces]
        fb.processNewFrame(rawFaces)
        
        # Update the cache frame counter and remove old entries
        face_ids_to_remove = []
        for face_id in face_recognition_cache:
            face_recognition_cache[face_id][3] -= 1
            if face_recognition_cache[face_id][3] <= 0:
                face_ids_to_remove.append(face_id)
        
        for face_id in face_ids_to_remove:
            del face_recognition_cache[face_id]
        
        # Get currently tracked faces
        trackedFaces = fb.getFaces()
        
        # Reset blacklisted faces list
        current_blacklisted_faces = {}
        
        # Check blacklist every N frames
        check_blacklist_frame_counter += 1
        if check_blacklist_frame_counter >= check_blacklist_frequency:
            check_blacklist_frame_counter = 0
            
            # Check if any tracked faces are in the blacklist
            for face in trackedFaces:
                # Check if this face is already in our cache
                if face.faceId in face_recognition_cache:
                    is_match, face_id, metadata = face_recognition_cache[face.faceId][:3]
                    if is_match:
                        current_blacklisted_faces[face.faceId] = metadata
                        continue
                
                # Calculate estimated distance
                est_distance = calculate_distance(face.w, focal_length)
                
                # Check if within target range (0-4m)
                if min_check_distance <= est_distance <= max_check_distance:
                    try:
                        # Only process faces in the target range
                        is_match, face_id, metadata = check_face_against_blacklist(
                            blacklist_db, frame, face, tolerance=0.7)  # Increased tolerance for more lenient matching
                        
                        # Cache the result
                        face_recognition_cache[face.faceId] = [is_match, face_id, metadata, cache_lifetime]
                        
                        if is_match:
                            current_blacklisted_faces[face.faceId] = metadata
                            print(f"Blacklisted face detected at estimated distance: {est_distance:.1f}m")
                    except Exception as e:
                        print(f"Error checking face against blacklist: {e}")
        
        # Update stable blacklist tracking to prevent flickering
        tracked_face_ids = [face.faceId for face in trackedFaces]
        
        # Remove faces that are no longer tracked
        for face_id in list(face_match_counters.keys()):
            if face_id not in tracked_face_ids:
                del face_match_counters[face_id]
                if face_id in stable_blacklisted_faces:
                    del stable_blacklisted_faces[face_id]
        
        # Update match counters for each face
        for face in trackedFaces:
            if face.faceId in current_blacklisted_faces:
                # If face is in current blacklist, increment counter
                face_match_counters[face.faceId] = face_match_counters.get(face.faceId, 0) + 1
                
                # If counter reaches threshold, add to stable blacklist
                if face_match_counters[face.faceId] >= stable_match_threshold:
                    stable_blacklisted_faces[face.faceId] = current_blacklisted_faces[face.faceId]
            else:
                # If face is not in current blacklist, decrement counter
                face_match_counters[face.faceId] = face_match_counters.get(face.faceId, 0) - 1
                
                # If counter goes below negative threshold, remove from stable blacklist
                if face_match_counters[face.faceId] <= stable_unmatch_threshold and face.faceId in stable_blacklisted_faces:
                    del stable_blacklisted_faces[face.faceId]
        
        # Now only use stable_blacklisted_faces for display and decision making
        if debug():
            display_frame = frame.copy()
            # Important: Pass stable_blacklisted_faces to the drawing function
            drawTrackedFaces(trackedFaces, display_frame, stable_blacklisted_faces, focal_length)
            
            # Display FPS
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frames / elapsed if elapsed > 0 else 0
                cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
            
            # Draw target range indicator (0-4m)
            height = Constants.captureResolutionHeight
            cv2.putText(display_frame, "TARGET RANGE: 0-4.0m", 
                       (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
            
            # Add range markers - possible face sizes at target distances
            ref_width_4m = int((face_width_cm * focal_length) / (4.0 * 10))  # Width of face at 4m
            
            cv2.rectangle(display_frame, (10, height - 20), (10 + ref_width_4m, height - 10), (0, 255, 255), 2)
            cv2.putText(display_frame, "4m", (10 + ref_width_4m + 5, height - 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
            
            # Debug info for match stability
            for face in trackedFaces:
                if face.faceId in face_match_counters:
                    counter_value = face_match_counters[face.faceId]
                    is_stable = "Yes" if face.faceId in stable_blacklisted_faces else "No"
                    is_current = "Yes" if face.faceId in current_blacklisted_faces else "No"
                    debug_text = f"C:{counter_value} S:{is_stable} Curr:{is_current}"
                    cv2.putText(display_frame, debug_text, 
                              (face.x, face.y + face.h + 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, cv2.LINE_AA)
        
        oldestFace = fb.getOldestTrackedFace()
        
        # Check if the oldest tracked face is a stable blacklisted face
        blacklisted_face_detected = False
        if oldestFace is not None and oldestFace.faceId in stable_blacklisted_faces:
            blacklisted_face_detected = True
            
            # Only consider blacklisted faces in target range (0-4m)
            est_distance = calculate_distance(oldestFace.w, focal_length)
            blacklisted_face_in_range = est_distance <= max_check_distance
            
            if not blacklisted_face_in_range:
                blacklisted_face_detected = False
        
        if blacklisted_face_detected:
            # Blacklisted target found within range, fire
            if deployed():
                cs.fire()
            if debug():
                cv2.putText(display_frame, "FIRE - TARGET", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
            s.play()
        elif oldestFace is not None:
            # Calculate distance
            est_distance = calculate_distance(oldestFace.w, focal_length)
            in_target_range = est_distance <= max_check_distance
            
            # Continue with normal targeting logic, but prioritize 0-4m range
            def deltaFromCenter(face):
                centerX = Constants.captureResolutionWidth / 2
                return face.x + (face.w / 2) - centerX

            def pixelArea(face):
                return face.w * face.h

            # Only fire in the target range
            if in_target_range and abs(deltaFromCenter(oldestFace)) < Constants.maxXDistanceFromCenter:
                if deployed():
                    cs.fire()
                if debug():
                    cv2.putText(display_frame, "FIRE - IN RANGE", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
                s.play()
            elif abs(deltaFromCenter(oldestFace)) < Constants.maxXDistanceFromCenter:
                if deployed():
                    cs.move(forward=True)
                if debug():
                    cv2.putText(display_frame, "FORWARD", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                if deltaFromCenter(oldestFace) < 0:
                    if deployed():
                        cs.rotate(clockwise=False)
                    if debug():
                        cv2.putText(display_frame, "ROTATE LEFT", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
                else:
                    if deployed():
                        cs.rotate(clockwise=True)
                    if debug():
                        cv2.putText(display_frame, "ROTATE RIGHT", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            if deployed():
                cs.roam()
            if debug():
                cv2.putText(display_frame, "ROAM", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
        
        if debug():
            # Show display and check for key press
            key = displayFrame(display_frame)
            # Clean up display frame to save memory
            del display_frame
            
            # If 'q' is pressed, exit
            if key == ord('q'):
                break

def main():
    print("Initializing system with 4m range optimization...")
    
    # Set environment variables for better OpenCV performance on ARM
    os.environ['OPENCV_OPENCL_RUNTIME'] = ''  # Disable OpenCL
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'  # Disable debug info
    
    # Load face detector with optimized parameters
    print("Loading face detector...")
    faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Try to load alternative cascade classifier for better detection
    alt_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
    if os.path.exists(alt_cascade_path):
        print("Using alternative face cascade for better detection...")
        faceCascade = cv2.CascadeClassifier(alt_cascade_path)
    
    print("Setting up camera...")
    cap = setupCaptureDevice()
    
    print("Initializing face buffer...")
    fb = FaceBuffer()
    
    print("Initializing sound...")
    s = Sound()
    
    # Initialize blacklist database
    print("Loading blacklist database...")
    blacklist_db = BlacklistDatabase()
    
    # Print number of faces in blacklist
    faces = blacklist_db.get_all_faces()
    print(f"Loaded {len(faces)} faces from blacklist")
    
    # Run garbage collection before starting main loop
    print("Cleaning memory...")
    gc.collect()
    
    if deployed():
        print("Initializing serial communication...")
        cs = Commands(Constants.serialDevice)
    else:
        cs = None
    
    print("System initialization complete")
    print("Starting main loop with 4m range optimization...")
    try:
        loop(faceCascade, cap, fb, s, cs, blacklist_db)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error in main loop: {e}")
    finally:
        print("Cleaning up...")
        cap.release()
        if debug():
            cv2.destroyAllWindows()
        print("System shutdown complete")

if __name__ == "__main__":
    main()
