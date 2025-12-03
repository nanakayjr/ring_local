import logging
import os

_LOGGER = logging.getLogger(__name__)


class FaceDetector:
    def __init__(self, cascade_path='haarcascade_frontalface_default.xml'):
        # Allow absolute or packaged relative paths; warn if cascade fails to load
        if not os.path.isabs(cascade_path):
            # try relative to integration root first (best-effort)
            here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            local_path = os.path.join(here, cascade_path)
            if os.path.exists(local_path):
                cascade_path = local_path

        try:
            import cv2
        except Exception:
            _LOGGER.exception("OpenCV not available; face detection disabled")
            self.face_cascade = None
            return

        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade is None or getattr(self.face_cascade, 'empty', lambda: False)():
            _LOGGER.warning(
                "Failed to load face cascade from path '%s' — face detection will be disabled",
                cascade_path,
            )

    def detect(self, frame, min_confidence=0.5):
        if not self.face_cascade:
            return False, []

        try:
            import cv2
        except Exception:
            _LOGGER.exception("OpenCV not available at detect time; skipping face detection")
            return False, []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

        face_detected = len(faces) > 0
        return face_detected, faces
