# main.py
import os
import cv2
import gc
import time
import numpy as np
from Constants import Constants
from FaceBuffer import FaceBuffer, RawFace
from Commands import Commands
from Sound import Sound
from blacklist import BlacklistDatabase, check_face_against_blacklist
from face_detector_mediapipe import MPFaceDetector

def debug() -> bool:
    return Constants.mode == "debug"

def deployed() -> bool:
    return Constants.mode == "deployed"

def setup_capture_device():
    """
    Initialize video capture for short‑range detection.
    Sets resolution to 426×320 @ 15 FPS.
    """
    cap = cv2.VideoCapture(Constants.cameraIndex)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  426)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 320)
    cap.set(cv2.CAP_PROP_FPS,          15)
    Constants.captureResolutionWidth  = 426
    Constants.captureResolutionHeight = 320
    return cap

def calculate_distance(face_width: float, focal_length: float = 400.0) -> float:
    """
    Estimate distance (in meters) from face pixel width.
    Assumes average face width ≈ 15 cm.
    """
    real_face_cm = 15.0
    return (real_face_cm * focal_length) / (face_width * 10.0)

def draw_tracked_faces(faces, frame, blacklisted: dict, focal_length: float = 400.0):
    """
    Draw bounding boxes, IDs, distances, and blacklist annotations.
    Red box for blacklisted, yellow for in-range, green otherwise.
    """
    for face in faces:
        dist = calculate_distance(face.w, focal_length)
        in_range = dist <= 4.0

        # choose box color
        if face.faceId in blacklisted:
            color = (0, 0, 255)  # red
            name = blacklisted[face.faceId].get("name", "Unknown")
            cv2.putText(frame, f"TARGET: {name}", (face.x, face.y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        elif in_range:
            color = (0, 255, 255)  # yellow
        else:
            color = (0, 255, 0)    # green

        # draw rectangle and ID
        cv2.rectangle(frame, (face.x, face.y),
                      (face.x + face.w, face.y + face.h),
                      color, 2)
        cv2.putText(frame, f"ID:{face.faceId}", (face.x, face.y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

        # draw distance below
        dist_color = (0,255,255) if in_range else (255,255,255)
        cv2.putText(frame, f"{dist:.1f}m",
                    (face.x, face.y + face.h + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, dist_color, 1, cv2.LINE_AA)

def display_frame(window_name: str, frame) -> int:
    """
    Show the frame in a window and return the key pressed.
    """
    cv2.imshow(window_name, frame)
    return cv2.waitKey(1) & 0xFF

def loop(cap, fb: FaceBuffer, s: Sound, cs: Commands, db: BlacklistDatabase):
    """
    Main processing loop:
      1) detect faces with MediaPipe
      2) update FaceBuffer
      3) periodically encode & compare against blacklist
      4) maintain stable blacklist matches
      5) draw results and fire or move
    """
    detector = MPFaceDetector(model_selection=0, min_confidence=0.6)

    # caches and counters for stable matching
    face_cache = {}  # faceId -> [is_match, blk_id, metadata, ttl]
    match_counters = {}  # faceId -> consecutive match count
    stable_blacklist = {}  # faceId -> metadata

    # thresholds
    cache_ttl = 30
    match_threshold = 2
    unmatch_threshold = -4
    check_interval = 5
    frame_counter = 0

    start_time = time.time()
    fps_count = 0

    print("Entering main loop with MediaPipe detection...")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        # update FPS
        fps_count += 1
        now = time.time()
        if now - start_time > 5.0:
            print(f"FPS: {fps_count / (now - start_time):.1f}")
            fps_count = 0
            start_time = now

        # 1) detect face boxes with MediaPipe
        boxes = detector.detect(frame)  # list of (top, right, bottom, left)

        # convert to RawFace
        raw_faces = []
        for top, right, bottom, left in boxes:
            x = left
            y = top
            w = right - left
            h = bottom - top
            raw_faces.append(RawFace(x, y, w, h))

        # 2) update tracker
        fb.processNewFrame(raw_faces)
        tracked = fb.getFaces()

        # 3) decrement cache TTL
        for fid in list(face_cache):
            face_cache[fid][3] -= 1
            if face_cache[fid][3] <= 0:
                del face_cache[fid]

        # 4) periodic blacklist check
        frame_counter = (frame_counter + 1) % check_interval
        if frame_counter == 0:
            current_hits = {}
            for face in tracked:
                fid = face.faceId
                # reuse cache if match
                if fid in face_cache and face_cache[fid][0]:
                    current_hits[fid] = face_cache[fid][2]
                    continue

                # only check faces within 4m
                dist = calculate_distance(face.w)
                if dist <= 4.0:
                    is_match, blk_id, md = check_face_against_blacklist(
                        db, frame, face, tolerance=0.5
                    )
                    face_cache[fid] = [is_match, blk_id, md, cache_ttl]
                    if is_match:
                        current_hits[fid] = md
                        print(f"[Blacklist] {blk_id} detected at {dist:.1f}m")

            # update stable matches
            for face in tracked:
                fid = face.faceId
                if fid in current_hits:
                    match_counters[fid] = match_counters.get(fid, 0) + 1
                    if match_counters[fid] >= match_threshold:
                        stable_blacklist[fid] = current_hits[fid]
                else:
                    match_counters[fid] = match_counters.get(fid, 0) - 1
                    if match_counters[fid] <= unmatch_threshold:
                        stable_blacklist.pop(fid, None)

        # 5) draw and trigger actions
        output = frame.copy()
        draw_tracked_faces(tracked, output, stable_blacklist)

        # check oldest tracked for firing
        oldest = fb.getOldestTrackedFace()
        if oldest and oldest.faceId in stable_blacklist:
            # fire if deployed
            if deployed():
                cs.fire()
            # play sound
            s.play()
            if debug():
                cv2.putText(output, "FIRE TARGET", (10,80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)

        # (keep original movement logic here if needed...)

        # 6) display in debug mode
        if debug():
            key = display_frame("Sentinel Dart X", output)
            if key == ord('q'):
                break

    # cleanup
    detector.close()
    cap.release()
    if debug():
        cv2.destroyAllWindows()

def main():
    """Entry point: initialize everything and start loop."""
    print("Initializing system...")
    os.environ["OPENCV_OPENCL_RUNTIME"] = ""
    os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

    cap = setup_capture_device()
    fb = FaceBuffer()
    snd = Sound()
    cmd = Commands(Constants.serialDevice) if deployed() else None
    db  = BlacklistDatabase()

    print(f"Loaded {len(db.get_all_faces())} blacklisted faces")
    gc.collect()

    try:
        loop(cap, fb, snd, cmd, db)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        cap.release()
        if debug():
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
