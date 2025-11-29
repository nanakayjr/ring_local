import os
import time
import logging

_LOGGER = logging.getLogger(__name__)


def enforce_retention(media_path, retention_days):
    """Deletes media files older than the retention period.

    This runs synchronously and should be invoked from an executor job
    if called from an async context.
    """
    now = time.time()
    retention_seconds = retention_days * 24 * 60 * 60

    for dirpath, _, filenames in os.walk(media_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                if (now - os.path.getmtime(file_path)) > retention_seconds:
                    _LOGGER.info("Deleting old file: %s", file_path)
                    os.remove(file_path)
            except Exception:
                _LOGGER.exception("Failed processing retention for %s", file_path)
