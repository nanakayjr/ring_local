from .motion import MotionDetector
from .face import FaceDetector

class Detector:
    def __init__(self, motion_min_area=500, face_cascade_path='haarcascade_frontalface_default.xml'):
        self.motion_detector = MotionDetector(min_area=motion_min_area)
        self.face_detector = FaceDetector(cascade_path=face_cascade_path)

    def detect(self, frame, detect_motion=True, detect_faces=True, min_face_confidence=0.5):
        motion_detected = False
        face_detected = False
        
        if detect_motion:
            motion_detected, _ = self.motion_detector.detect(frame)
            
        if detect_faces:
            face_detected, _ = self.face_detector.detect(frame, min_confidence=min_face_confidence)
            
        return motion_detected, face_detected
