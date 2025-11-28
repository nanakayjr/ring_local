import collections
import datetime

class CircularBuffer:
    def __init__(self, size_seconds):
        self.size_seconds = size_seconds
        self.buffer = collections.deque()

    def add(self, frame, timestamp):
        self.buffer.append((frame, timestamp))
        self.trim()

    def trim(self):
        now = datetime.datetime.now()
        while self.buffer:
            frame, timestamp = self.buffer[0]
            if (now - timestamp).total_seconds() > self.size_seconds:
                self.buffer.popleft()
            else:
                break

    def get_all(self):
        return list(self.buffer)
