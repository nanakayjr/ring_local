import cv2
import datetime
import threading
import time

from .buffer import CircularBuffer
from .ffmpeg_wrapper import save_clip as save_clip_ffmpeg

class Recorder(threading.Thread):
    def __init__(self, camera_id, rtsp_url, buffer_seconds):
        super().__init__()
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.buffer = CircularBuffer(buffer_seconds)
        self.running = False
        self.cap = None

    def run(self):
        self.running = True
        while self.running:
            if not self.cap:
                self.cap = cv2.VideoCapture(self.rtsp_url)
                if not self.cap.isOpened():
                    print(f"Error opening video stream for {self.camera_id}")
                    self.cap = None
                    time.sleep(5)
                    continue

            ret, frame = self.cap.read()
            if not ret:
                print(f"Error reading frame from {self.camera_id}")
                self.cap.release()
                self.cap = None
                time.sleep(5)
                continue

            now = datetime.datetime.now()
            self.buffer.add(frame, now)

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def save_clip(self, output_path, pre_event_seconds, post_event_seconds, fps):
        frames_with_ts = self.buffer.get_all()
        
        # This is a simplified version. We will need to handle post_event_seconds later
        frames = [frame for frame, ts in frames_with_ts]
        
        save_clip_ffmpeg(frames, output_path, fps)
