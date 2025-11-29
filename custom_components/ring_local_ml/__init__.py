"""The Ring Local ML integration."""
import asyncio
import paho.mqtt.client as mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_MQTT_HOST, CONF_MQTT_PORT, CONF_MEDIA_DIR
from .recorder.recorder import Recorder
from .ml.detector import Detector
from .storage.db import get_session, Event
from .storage.filesystem import create_media_paths, get_clip_path, get_snapshot_path
import cv2

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Ring Local ML component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Ring Local ML from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    mqtt_host = entry.data[CONF_MQTT_HOST]
    mqtt_port = entry.data[CONF_MQTT_PORT]
    media_dir = entry.data[CONF_MEDIA_DIR]

    recorders = {}
    # The cameras should be configured in another way, for example through the options flow
    # For now, we will assume a dummy camera
    cameras = [{"id": "dummy_camera", "rtsp_url": "", "enabled": False}] 

    for camera in cameras:
        if camera['enabled']:
            recorder = Recorder(camera['id'], camera['rtsp_url'], 5) # 5 seconds pre-buffer
            recorder.start()
            recorders[camera['id']] = recorder

    detector = Detector()

    def on_connect(client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        for camera in cameras:
            if camera['enabled']:
                client.subscribe(f"ring/{camera['id']}/motion")
                client.subscribe(f"ring/{camera['id']}/ding")

    def on_message(client, userdata, msg):
        print(f"Message received on topic {msg.topic}")
        
        topic_parts = msg.topic.split('/')
        camera_id = topic_parts[1]
        event_type = topic_parts[2]

        recorder = recorders.get(camera_id)
        if not recorder:
            return

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

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_host, mqtt_port, 60)
    client.loop_start()

    hass.data[DOMAIN][entry.entry_id] = client

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    client = hass.data[DOMAIN].pop(entry.entry_id)
    client.loop_stop()
    return True