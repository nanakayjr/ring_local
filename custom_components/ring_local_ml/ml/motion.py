import numpy as np


class MotionDetector:
    """Simple frame differencing detector implemented with NumPy only."""

    def __init__(self, min_area=500, decay=0.9, threshold=20):
        self.min_area = min_area
        self.decay = decay
        self.threshold = threshold
        self._background = None

    def detect(self, frame):
        if frame is None:
            return False, None

        gray = frame.mean(axis=2).astype(np.float32)
        if self._background is None:
            self._background = gray
            return False, np.zeros_like(gray, dtype=np.uint8)

        diff = np.abs(gray - self._background)
        self._background = self.decay * self._background + (1 - self.decay) * gray

        mask = (diff > self.threshold).astype(np.uint8)
        motion_pixels = int(mask.sum())
        return motion_pixels > self.min_area, mask
