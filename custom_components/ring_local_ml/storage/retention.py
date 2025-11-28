import os
import datetime
import time

def enforce_retention(media_path, retention_days):
    """Deletes media files older than the retention period."""
    now = time.time()
    retention_seconds = retention_days * 24 * 60 * 60
    
    for dirpath, _, filenames in os.walk(media_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if (now - os.path.getmtime(file_path)) > retention_seconds:
                print(f"Deleting old file: {file_path}")
                os.remove(file_path)
