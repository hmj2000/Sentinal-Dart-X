import cv2
from Constants import Constants
from FaceBuffer import FaceBuffer, RawFace, Face
from Commands import Commands
from Sound import Sound
from blacklist import BlacklistDatabase, check_face_against_blacklist

def debug():
    return Constants.mode == "debug"

def deployed():
    return Constants.mode == "deployed"

def setupCaptureDevice():
    cap = cv2.VideoCapture(Constants.cameraIndex)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        exit()
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Constants.captureResolutionWidth)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Constants.captureResolutionHeight)
    cap.set(cv2.CAP_PROP_FPS, Constants.captureFPS)
    return cap

def drawTrackedFaces(faces, resizedFrame, blacklisted_faces=None):
    if blacklisted_faces is None:
        blacklisted_faces = {}
        
    for face in faces:
        # Mark blacklisted faces with red color
        if face.faceId in blacklisted_faces:
            color = (0, 0, 255)  # Red
            name = blacklisted_faces[face.faceId].get('name', 'Unknown')
            cv2.putText(resizedFrame, f"BLACKLISTED: {name}", (face.x, face.y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            color = (0, 255, 0)  # Green
            
        cv2.rectangle(resizedFrame, (face.x, face.y), (face.x + face.w, face.y + face.h), color, 3)
        cv2.putText(resizedFrame, str(face.faceId), (face.x, face.y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(resizedFrame, f'Pixel Area: {face.w * face.h}', (face.x, face.y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(resizedFrame, f'Distance From Center: {(face.x + (face.w / 2)) - (Constants.captureResolutionWidth/2)}', (face.x, face.y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv2.LINE_AA)

def displayFrame(frame):
    cv2.imshow('Sentinel Dart X', frame)
    cv2.waitKey(1)

def loop(faceCascade, cap, fb, s, cs, blacklist_db):
    # Store blacklisted faces in current frame
    current_blacklisted_faces = {}
    
    # Blacklist check frequency control (check every 5 frames to improve performance)
    check_blacklist_frame_counter = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Failed to grab frame")
            break
        
        resizedFrame = cv2.resize(frame,(Constants.captureResolutionWidth,Constants.captureResolutionHeight))
        gray = cv2.cvtColor(resizedFrame, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, scaleFactor=Constants.cascadeScaleFactor, minNeighbors=Constants.cascadeMinNeighbors)
        
        rawFaces = [RawFace(face[0], face[1], face[2], face[3]) for face in faces]
        fb.processNewFrame(rawFaces)
        
        # Reset blacklisted faces list
        current_blacklisted_faces = {}
        
        # Check blacklist every 5 frames
        check_blacklist_frame_counter += 1
        if check_blacklist_frame_counter >= 5:
            check_blacklist_frame_counter = 0
            
            # Check if any tracked faces are in the blacklist
            trackedFaces = fb.getFaces()
            for face in trackedFaces:
                is_match, face_id, metadata = check_face_against_blacklist(blacklist_db, resizedFrame, face)
                if is_match:
                    current_blacklisted_faces[face.faceId] = metadata
        
        if debug():
            trackedFaces = fb.getFaces()
            drawTrackedFaces(trackedFaces, resizedFrame, current_blacklisted_faces)
        
        oldestFace = fb.getOldestTrackedFace()
        
        # Check if the oldest tracked face is a blacklisted face
        blacklisted_face_detected = False
        if oldestFace is not None and oldestFace.faceId in current_blacklisted_faces:
            blacklisted_face_detected = True
        
        if blacklisted_face_detected:
            # Blacklisted target found, fire regardless of position
            if deployed():
                cs.fire()
            if debug():
                cv2.putText(resizedFrame, "FIRE - BLACKLISTED TARGET", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
            s.play()
        elif oldestFace is not None:
            # Continue with normal targeting logic
            def deltaFromCenter(face):
                centerX = Constants.captureResolutionWidth / 2
                return face.x + (face.w / 2) - centerX

            def pixelArea(face):
                return face.w * face.h

            if abs(deltaFromCenter(oldestFace)) < Constants.maxXDistanceFromCenter:
                if pixelArea(oldestFace) >= Constants.minimumPixelAreaFireRange:
                    if deployed():
                        cs.fire()
                    if debug():
                        cv2.putText(resizedFrame, "FIRE", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 2, cv2.LINE_AA)
                    s.play()
                else:
                    if deployed():
                        cs.move(forward=True)
                    if debug():
                        cv2.putText(resizedFrame, "FORWARD", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                if deltaFromCenter(oldestFace) < 0:
                    if deployed():
                        cs.rotate(clockwise=False)
                    if debug():
                        cv2.putText(resizedFrame, "ROTATE LEFT", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 2, cv2.LINE_AA)
                else:
                    if deployed():
                        cs.rotate(clockwise=True)
                    if debug():
                        cv2.putText(resizedFrame, "ROTATE RIGHT", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            if deployed():
                cs.roam()
            if debug():
                cv2.putText(resizedFrame, "ROAM", (0,80), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 2, cv2.LINE_AA)
        
        if debug():
            displayFrame(resizedFrame)

def main():
    faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = setupCaptureDevice()
    fb = FaceBuffer()
    s = Sound()
    
    # Initialize blacklist database
    blacklist_db = BlacklistDatabase()
    
    if deployed():
        cs = Commands(Constants.serialDevice)
    else:
        cs = None
    
    loop(faceCascade, cap, fb, s, cs, blacklist_db)
    cap.release()
    if debug():
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
