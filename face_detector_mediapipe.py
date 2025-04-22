# face_detector_mediapipe.py
import cv2
import mediapipe as mp

class MPFaceDetector:
    def __init__(self, model_selection=0, min_confidence=0.6):
        self.detector = mp.solutions.face_detection.FaceDetection(
            model_selection=model_selection,
            min_detection_confidence=min_confidence
        )

    def detect(self, frame):
        """返回 list[(top, right, bottom, left)]"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.detector.process(rgb)
        h, w, _ = frame.shape
        boxes = []
        if res.detections:
            for d in res.detections:
                bb = d.location_data.relative_bounding_box
                x1 = int(bb.xmin * w)
                y1 = int(bb.ymin * h)
                x2 = x1 + int(bb.width * w)
                y2 = y1 + int(bb.height * h)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                boxes.append((y1, x2, y2, x1))
        return boxes

    def close(self):
        self.detector.close()
