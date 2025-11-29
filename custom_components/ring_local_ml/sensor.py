"""Sensor platform for the Ring Local ML integration."""
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
import homeassistant.components.mqtt as mqtt
from .const import DOMAIN, CONF_MQTT_HOST, CONF_MQTT_PORT, CONF_MEDIA_DIR
from .recorder.recorder import Recorder
from .ml.detector import Detector
from .storage.db import get_session, Event
from .storage.filesystem import create_media_paths, get_clip_path, get_snapshot_path
import cv2

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    
    media_dir = entry.data[CONF_MEDIA_DIR]
    
    recorders = {}
    # The cameras should be configured in another way, for example through the options flow
    # For now, we will assume a dummy camera
    cameras = [{"id": "dummy_camera", "rtsp_url": "", "enabled": False}] 

    for camera in cameras:
        if camera['enabled']:
            # Instantiate the recorder in the executor (it may allocate heavy resources)
            recorder = await hass.async_add_executor_job(Recorder, camera['id'], camera['rtsp_url'], 5)
            # Starting a thread is quick/non-blocking; do it directly rather than scheduling
            # it through the executor. The recorder's run loop will execute in its own thread.
            try:
                recorder.start()
            except RuntimeError:
                # If starting fails for any reason, log and continue
                import logging
                _LOGGER = logging.getLogger(__name__)
                _LOGGER.exception("Failed to start recorder thread for %s", camera['id'])
            recorders[camera['id']] = recorder

    detector = await hass.async_add_executor_job(Detector)

    @callback
    def message_received(msg):
        """Handle new MQTT messages."""
        hass.async_create_task(handle_mqtt_message(hass, msg, recorders, detector, media_dir))

    for camera in cameras:
        if camera['enabled']:
            await mqtt.async_subscribe(
                hass,
                f"ring/{camera['id']}/motion",
                message_received,
                1,
            )
            await mqtt.async_subscribe(
                hass,
                f"ring/{camera['id']}/ding",
                message_received,
                1,
            )
    
    async_add_entities([RingLocalMLEventSensor(camera["id"]) for camera in cameras if camera["enabled"]])

async def handle_mqtt_message(hass, msg, recorders, detector, media_dir):
    """Handle the MQTT message."""
    topic_parts = msg.topic.split('/')
    camera_id = topic_parts[1]
    event_type = topic_parts[2]

    recorder = recorders.get(camera_id)
    if not recorder:
        return
    
    def _save_and_detect():
        media_path = create_media_paths(media_dir, camera_id)
        clip_path = get_clip_path(media_path, event_type)
        recorder.save_clip(clip_path, 5, 10, 20)

        frames = recorder.buffer.get_all()
        face_detected = False
        snapshot_path = None
        for frame, ts in frames:
            motion, face = detector.detect(frame, detect_motion=False, detect_faces=True)
            if face:
                face_detected = True
                snapshot_path = get_snapshot_path(media_path, f"{event_type}_face")
                cv2.imwrite(snapshot_path, frame)
                break
        
        session = get_session(f"sqlite:///{media_dir}/media.db")
        event = Event(
            camera_id=camera_id,
            event_type=event_type,
            clip_path=clip_path,
            snapshot_path=snapshot_path,
            face_detected=face_detected,
            duration=15
        )
        session.add(event)
        session.commit()

    await hass.async_add_executor_job(_save_and_detect)

class RingLocalMLEventSensor(Entity):
    """Representation of a Ring Local ML Event Sensor."""

    def __init__(self, camera_id):
        """Initialize the sensor."""
        self._camera_id = camera_id
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Ring Local ML Event ({self._camera_id})"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"ring_local_ml_event_{self._camera_id}"
