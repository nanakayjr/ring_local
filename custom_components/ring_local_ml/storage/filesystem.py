import os
import datetime

def create_media_paths(base_path, camera_name):
    """Creates the directory structure for storing media."""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(base_path, camera_name, today)
    os.makedirs(path, exist_ok=True)
    return path

def get_clip_path(media_path, event_type):
    """Generates a path for a new video clip."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{event_type}.mp4"
    return os.path.join(media_path, filename)

def get_snapshot_path(media_path, event_type):
    """Generates a path for a new snapshot."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{event_type}.jpg"
    return os.path.join(media_path, filename)
