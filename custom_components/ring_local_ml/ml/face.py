import cv2

class FaceDetector:
    def __init__(self, cascade_path='haarcascade_frontalface_default.xml'):
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect(self, frame, min_confidence=0.5):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        face_detected = False
        if len(faces) > 0:
            face_detected = True
            
        return face_detected, faces
