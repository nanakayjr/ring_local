import datetime as dt
import logging
import threading
import time
from typing import Optional

import ffmpeg
import numpy as np

from .buffer import CircularBuffer
from .ffmpeg_wrapper import save_clip as save_clip_ffmpeg

_LOGGER = logging.getLogger(__name__)


class Recorder(threading.Thread):
    """Background RTSP reader that maintains a rolling frame buffer."""

    def __init__(
        self,
        camera_id: str,
        rtsp_url: str,
        buffer_seconds: int,
        *,
        width: int = 640,
        height: int = 360,
        fps: int = 10,
    ):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.buffer = CircularBuffer(buffer_seconds)
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self._process = None

    def start(self):
        self.running = True
        super().start()

    def run(self):
        while self.running:
            try:
                self._process = (
                    ffmpeg
                    .input(self.rtsp_url, rtsp_transport="tcp")
                    .output(
                        "pipe:",
                        format="rawvideo",
                        pix_fmt="rgb24",
                        s=f"{self.width}x{self.height}",
                        r=self.fps,
                    )
                    .run_async(pipe_stdout=True, pipe_stderr=True)
                )
            except ffmpeg.Error as err:
                _LOGGER.error("FFmpeg failed to open %s: %s", self.camera_id, err)
                time.sleep(5)
                continue

            frame_size = self.width * self.height * 3

            while self.running:
                in_bytes = self._process.stdout.read(frame_size)
                if not in_bytes or len(in_bytes) < frame_size:
                    break

                frame = (
                    np
                    .frombuffer(in_bytes, np.uint8)
                    .reshape((self.height, self.width, 3))
                )
                # Convert RGB to BGR to stay compatible with legacy consumers.
                frame_bgr = frame[:, :, ::-1]
                self.buffer.add(frame_bgr, dt.datetime.now())

            self._close_process()
            time.sleep(2)

    def _close_process(self):
        if self._process:
            try:
                self._process.stdout.close()
            except Exception:
                pass
            self._process.wait(timeout=1)
            self._process = None

    def stop(self):
        self.running = False
        self._close_process()

    def save_clip(self, output_path, pre_event_seconds, post_event_seconds, fps):
        frames_with_ts = self.buffer.get_all()
        cutoff = dt.datetime.now() - dt.timedelta(seconds=pre_event_seconds + post_event_seconds)
        frames = [frame for frame, ts in frames_with_ts if ts >= cutoff]
        save_clip_ffmpeg(frames, output_path, fps)
