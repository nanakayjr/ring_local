class MotionDetector:
    def __init__(self, min_area=500):
        self.min_area = min_area
        self.background_subtractor = None

    def detect(self, frame):
        # Lazy-initialize OpenCV objects to avoid heavy imports at module load time
        if self.background_subtractor is None:
            try:
                import cv2
            except Exception:
                # OpenCV unavailable: return no motion and an empty mask
                return False, None
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2()

        import cv2

        fg_mask = self.background_subtractor.apply(frame)
        
        # Basic noise reduction
        fg_mask = cv2.GaussianBlur(fg_mask, (21, 21), 0)
        fg_mask = cv2.threshold(fg_mask, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area:
                motion_detected = True
                break
        
        return motion_detected, fg_mask
