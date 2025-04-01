import cv2
from Constants import Constants
from FaceBuffer import FaceBuffer, RawFace, Face
from Commands import Commands
from Sound import Sound

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

def drawTrackedFaces(faces, resizedFrame):
    for face in faces:
        cv2.rectangle(resizedFrame, (face.x, face.y), (face.x + face.w, face.y + face.h), (0,255,0), 3)
        cv2.putText(resizedFrame, str(face.faceId), (face.x, face.y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(resizedFrame, f'Pixel Area: {face.w * face.h}', (face.x, face.y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(resizedFrame, f'Distance From Center: {(face.x + (face.w / 2)) - (Constants.captureResolutionWidth/2)}', (face.x, face.y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv2.LINE_AA)

def displayFrame(frame):
    cv2.imshow('Sentinel Dart X', frame)
    cv2.waitKey(1)

def loop(faceCascade, cap, fb, s, cs):
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
        
        if debug():
            trackedFaces = fb.getFaces()
            drawTrackedFaces(trackedFaces, resizedFrame)
        
        oldestFace = fb.getOldestTrackedFace()
        
        
        if oldestFace is not None:
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
    if deployed():
        cs = Commands(Constants.serialDevice)
    else:
        cs = None
    
    loop(faceCascade, cap, fb, s, cs)
    cap.release()
    if debug():
        cv2.destroyAllWindows()

main()
