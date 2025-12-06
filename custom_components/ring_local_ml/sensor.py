"""Sensor platform for the Ring Local ML integration."""
import asyncio
from datetime import datetime
import json
import logging
import os
from typing import Dict, Tuple

import numpy as np
from PIL import Image
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
import homeassistant.components.mqtt as mqtt
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_MEDIA_DIR
from .recorder.recorder import Recorder
from .ml.detector import Detector
from .storage.db import record_event
from .storage.filesystem import create_media_paths, get_clip_path, get_snapshot_path
from .mqtt import parse_ring_topic, SUPPORTED_RING_CATEGORIES


PRE_EVENT_SECONDS = 5
POST_EVENT_SECONDS = 10
CLIP_FPS = 20


def _default_camera_name(camera_id: str) -> str:
    suffix = camera_id[-4:] if camera_id else ""
    if suffix:
        return f"Ring Camera {suffix}"
    return "Ring Camera"

DEFAULT_TOPIC_SUFFIXES = [
    "motion/state",
    "motion/attributes",
    "motion/last_motion",
    "motion/last_motion_time",
    "motion/person_detected",
    "motion/detection_enabled",
    "ding/state",
    "ding/attributes",
    "wireless/attributes",
    "wireless/network",
    "wireless/signal",
    "battery/attributes",
    "battery/level",
    "battery/life",
    "motion_detection/state",
    "motion_warning/state",
    "light/state",
    "siren/state",
    "info/state",
    "snapshot/attributes",
    "snapshot_interval/state",
    "stream/state",
    "stream/attributes",
    "event_stream/state",
    "event_stream/attributes",
    "event_select/state",
    "event_select/attributes",
    "motion_duration/state",
    "ding_duration/state",
]

TOPIC_LABELS = {
    "motion/state": "Motion",
    "motion/attributes": "Motion Attributes",
    "motion/last_motion": "Last Motion Timestamp",
    "motion/last_motion_time": "Last Motion Time",
    "motion/person_detected": "Person Detected",
    "motion/detection_enabled": "Motion Detection Enabled",
    "ding/state": "Doorbell",
    "ding/attributes": "Doorbell Attributes",
    "wireless/attributes": "Wireless Attributes",
    "wireless/network": "Wireless Network",
    "wireless/signal": "Wireless Signal",
    "battery/attributes": "Battery Attributes",
    "battery/level": "Battery Level",
    "battery/life": "Battery Life",
    "motion_detection/state": "Motion Detection",
    "motion_warning/state": "Motion Warning",
    "light/state": "Light State",
    "siren/state": "Siren State",
    "info/state": "Device Info",
    "snapshot/attributes": "Snapshot Attributes",
    "snapshot_interval/state": "Snapshot Interval",
    "stream/state": "Live Stream",
    "stream/attributes": "Stream Status",
    "event_stream/state": "Event Stream",
    "event_stream/attributes": "Event Stream Status",
    "event_select/state": "Event Selector",
    "event_select/attributes": "Event Metadata",
    "motion_duration/state": "Motion Duration",
    "ding_duration/state": "Ding Duration",
}

DEFAULT_SENSOR_STATE = "idle"
DEFAULT_TOPIC_STATE_OVERRIDES = {
    "motion/state": "idle",
    "ding/state": "idle",
    "motion/last_motion": 0,
    "motion/last_motion_time": "",
    "motion/person_detected": "off",
    "motion/detection_enabled": "off",
    "wireless/network": "",
    "wireless/signal": -100,
    "battery/level": 0,
    "battery/life": 0,
    "motion_detection/state": "off",
    "motion_warning/state": "off",
    "light/state": "off",
    "siren/state": "off",
    "stream/state": "inactive",
    "stream/attributes": "{}",
    "event_stream/state": "inactive",
    "event_stream/attributes": "{}",
    "event_select/state": "Motion 1",
    "event_select/attributes": "{}",
    "snapshot/attributes": "{}",
    "snapshot_interval/state": 0,
    "info/state": "{}",
    "motion/attributes": "{}",
    "ding/attributes": "{}",
    "motion_duration/state": 120,
    "ding_duration/state": 120,
}
DEFAULT_ENTITY_STATE_OVERRIDES = {
    "motion": "idle",
    "ding": "idle",
    "wireless": "",
    "battery": 0,
    "info": "{}",
    "snapshot": "{}",
    "snapshot_interval": 0,
    "stream": "inactive",
    "event_stream": "inactive",
    "event_select": "Motion 1",
    "motion_detection": "off",
    "motion_warning": "off",
    "light": "off",
    "siren": "off",
    "status": "offline",
    "attributes": "{}",
}

ATTRIBUTE_SPLITS = {
    "wireless/attributes": {
        "wirelessNetwork": {"suffix": "wireless/network"},
        "wirelessSignal": {"suffix": "wireless/signal"},
    },
    "battery/attributes": {
        "batteryLevel": {"suffix": "battery/level"},
        "batteryLife": {"suffix": "battery/life"},
    },
    "motion/attributes": {
        "lastMotion": {"suffix": "motion/last_motion"},
        "lastMotionTime": {"suffix": "motion/last_motion_time"},
        "personDetected": {"suffix": "motion/person_detected"},
        "motionDetectionEnabled": {"suffix": "motion/detection_enabled"},
    },
}

_LOGGER = logging.getLogger(__name__)

CAMERA_SCHEMA = vol.Schema(
    {
        vol.Required("id"): str,
        vol.Required("rtsp_url"): str,
    }
)


def _decode_payload(payload) -> str:
    """Return a safe string representation of an MQTT payload."""
    if isinstance(payload, bytes):
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("utf-8", "ignore")
    return str(payload)


def _camera_display_name(camera_id: str, camera_meta: Dict[str, Dict]) -> str:
    meta = camera_meta.get(camera_id) or {}
    for key in ("name", "label", "friendly_name"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _default_camera_name(camera_id)


def _topic_label(topic_suffix: str) -> str:
    if topic_suffix in TOPIC_LABELS:
        return TOPIC_LABELS[topic_suffix]
    cleaned = topic_suffix.replace("_", " ").replace("/", " ")
    return cleaned.title()


def _default_state_for_topic(topic_suffix: str):
    if topic_suffix in DEFAULT_TOPIC_STATE_OVERRIDES:
        return DEFAULT_TOPIC_STATE_OVERRIDES[topic_suffix]
    base = topic_suffix.split("/", 1)[0] if topic_suffix else ""
    return DEFAULT_ENTITY_STATE_OVERRIDES.get(base, DEFAULT_SENSOR_STATE)


def _split_attribute_payload(camera_id: str, topic_suffix: str, payload_text: str, entity_manager):
    mapping = ATTRIBUTE_SPLITS.get(topic_suffix)
    if not mapping or not payload_text:
        return

    try:
        parsed = json.loads(payload_text)
    except (json.JSONDecodeError, TypeError):
        return

    for key, spec in mapping.items():
        if key not in parsed:
            continue
        suffix = spec["suffix"]
        sensor = entity_manager.get_or_create(camera_id, suffix)
        try:
            child_payload = json.dumps({"state": parsed[key]}, ensure_ascii=False)
        except (TypeError, ValueError):
            child_payload = json.dumps({"state": str(parsed[key])})
        sensor.handle_payload(child_payload)


def _normalize_state(value):
    """Convert any payload-derived value into a sensor-friendly state."""
    if isinstance(value, (str, int, float)) or value is None:
        return value
    if isinstance(value, bool):
        return "on" if value else "off"
    return json.dumps(value, ensure_ascii=False)


def _extract_state_and_attrs(text):
    """Derive sensor state/attributes from MQTT payload text."""
    if text is None:
        return None, {}

    stripped = text.strip()
    if not stripped:
        return None, {}

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return stripped, {}

    if isinstance(parsed, dict):
        state = parsed.get("state")
        if state is None:
            for key in ("value", "status", "event", "level"):
                if parsed.get(key) is not None:
                    state = parsed[key]
                    break
        return state if state is not None else parsed, parsed

    if isinstance(parsed, list):
        return parsed, {"items": parsed}

    return parsed, {}


_NEGATIVE_STRINGS = {"false", "off", "idle", "inactive", "0", "standby", "clear"}


def _payload_is_active(text: str) -> bool:
    """Determine whether a payload signifies an active motion/ding event."""

    if text is None:
        return False

    stripped = text.strip()
    if not stripped:
        return False

    def _value_truthy(value):
        if isinstance(value, str):
            return value.strip().lower() not in _NEGATIVE_STRINGS
        return bool(value)

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return _value_truthy(stripped)

    if isinstance(parsed, dict):
        for key in ("state", "value", "event", "active", "level"):
            if key in parsed:
                return _value_truthy(parsed[key])
        return True

    return _value_truthy(parsed)


def _save_snapshot(path: str, frame):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rgb_frame = frame[:, :, ::-1]
    image = Image.fromarray(rgb_frame.astype(np.uint8))
    image.save(path)


class RingLocalMQTTSensor(SensorEntity):
    """Dynamic sensor that mirrors every MQTT topic exposed by Ring-MQTT."""

    _attr_should_poll = False

    def __init__(self, camera_id: str, topic_suffix: str, device_name: str):
        self._camera_id = camera_id
        self._topic_suffix = topic_suffix or "state"
        slug = self._topic_suffix.replace("/", "_")
        label = _topic_label(self._topic_suffix)
        self._friendly_name = f"{device_name} {label}".strip()
        self._attr_name = self._friendly_name
        self._attr_unique_id = f"ring_local_ml_{camera_id}_{slug}"
        self._attr_extra_state_attributes = {
            "camera_id": camera_id,
            "topic": self._topic_suffix,
        }
        self._attr_native_value = _default_state_for_topic(self._topic_suffix)
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, camera_id)},
            manufacturer="Ring",
            name=device_name,
        )

    @property
    def device_info(self):
        return self._device_info

    def handle_payload(self, payload_text: str):
        state, attrs = _extract_state_and_attrs(payload_text)
        state = _normalize_state(state)
        if state is None:
            state = _default_state_for_topic(self._topic_suffix)
        metadata = {
            "camera_id": self._camera_id,
            "topic": self._topic_suffix,
            "last_update": datetime.utcnow().isoformat(),
        }
        if attrs:
            # Merge parsed attributes with metadata for easier debugging.
            metadata.update({k: v for k, v in attrs.items() if k not in metadata})
        else:
            metadata["payload"] = payload_text

        self._attr_extra_state_attributes = metadata
        self._attr_native_value = state
        self.async_write_ha_state()


class RingMQTTSensorManager:
    """Ensure one HA sensor per MQTT topic."""

    def __init__(self, async_add_entities, camera_meta):
        self._async_add_entities = async_add_entities
        self._entities: Dict[Tuple[str, str], RingLocalMQTTSensor] = {}
        self._camera_meta = camera_meta

    def update_camera_meta(self, camera_id: str, meta: Dict):
        self._camera_meta[camera_id] = meta

    def get_or_create(self, camera_id: str, topic_suffix: str) -> RingLocalMQTTSensor:
        normalized = topic_suffix or "state"
        key = (camera_id, normalized)
        if key not in self._entities:
            name = _camera_display_name(camera_id, self._camera_meta)
            entity = RingLocalMQTTSensor(camera_id, normalized, name)
            self._entities[key] = entity
            self._async_add_entities([entity])
        return self._entities[key]

    def prime_camera_topics(self, camera_id: str):
        for suffix in DEFAULT_TOPIC_SUFFIXES:
            self.get_or_create(camera_id, suffix)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""

    media_dir = entry.data[CONF_MEDIA_DIR]
    media_db = os.path.join(media_dir, "media.db")
    cameras = [c for c in entry.options.get("cameras", []) if c.get("id")]
    camera_meta: Dict[str, Dict] = {c["id"]: c for c in cameras}

    recorders = {}
    for camera in cameras:
        camera_id = camera["id"]
        rtsp_url = camera.get("rtsp_url")
        if not rtsp_url:
            _LOGGER.debug("Camera %s has no RTSP URL; skipping recorder", camera_id)
            continue

        buffer_window = PRE_EVENT_SECONDS + POST_EVENT_SECONDS + 5
        recorder = Recorder(
            camera_id,
            rtsp_url,
            buffer_window,
            fps=CLIP_FPS,
        )
        recorders[camera_id] = recorder
        await hass.async_add_executor_job(recorder.start)

    detector = Detector()
    entity_manager = RingMQTTSensorManager(async_add_entities, camera_meta)

    event_entities = []
    event_entity_index: Dict[str, RingLocalMLEventSensor] = {}
    for camera in cameras:
        camera_id = camera["id"]
        device_name = _camera_display_name(camera_id, camera_meta)
        event_sensor = RingLocalMLEventSensor(camera_id, device_name)
        event_entities.append(event_sensor)
        event_entity_index[camera_id] = event_sensor
        entity_manager.prime_camera_topics(camera_id)

    if event_entities:
        async_add_entities(event_entities)

    @callback
    def message_received(msg):
        """Handle new MQTT messages from the Ring-MQTT addon."""
        topic = parse_ring_topic(msg.topic)
        if not topic or topic.category not in SUPPORTED_RING_CATEGORIES:
            return

        if topic.topic_suffix.endswith("image"):
            return

        last_segment = topic.topic_suffix.split("/")[-1] if topic.topic_suffix else ""
        if last_segment.endswith("command"):
            return

        topic_suffix = topic.topic_suffix or "state"
        payload_text = _decode_payload(msg.payload)
        "wireless/attributes": {
            "wirelessNetwork": {"suffix": "wireless/network"},
            "wirelessSignal": {"suffix": "wireless/signal"},
        },
        "battery/attributes": {
            "batteryLevel": {"suffix": "battery/level"},
            "batteryLife": {"suffix": "battery/life"},
        },
                entity_manager.update_camera_meta(camera_id, meta)
                if topic.location_id in event_entity_index and camera_id not in event_entity_index:
                    event_entity_index[camera_id] = event_entity_index[topic.location_id]
                if topic.location_id in recorders and camera_id not in recorders:
                    recorders[camera_id] = recorders[topic.location_id]
            else:
                meta = {
                    "id": camera_id,
                    "name": _default_camera_name(camera_id),
                    "location_id": topic.location_id,
                }
                camera_meta[camera_id] = meta
                entity_manager.update_camera_meta(camera_id, meta)
                entity_manager.prime_camera_topics(camera_id)
                device_name = _camera_display_name(camera_id, camera_meta)
                event_sensor = RingLocalMLEventSensor(camera_id, device_name)
                event_entity_index[camera_id] = event_sensor
                async_add_entities([event_sensor])

        meta.setdefault("location_id", topic.location_id)
        meta.setdefault("category", topic.category)

        sensor_entity = entity_manager.get_or_create(camera_id, topic_suffix)
        sensor_entity.handle_payload(payload_text)
        _split_attribute_payload(camera_id, topic_suffix, payload_text, entity_manager)

        base_event = topic.entity or topic_suffix.split("/", 1)[0]
        if topic_suffix.endswith("/state") and base_event in {"motion", "ding"} and _payload_is_active(payload_text):
            event_sensor = event_entity_index.get(camera_id)
            if event_sensor:
                event_sensor.handle_event(base_event, payload_text)
            hass.async_create_task(
                handle_mqtt_message(
                    hass,
                    camera_id,
                    base_event,
                    recorders,
                    detector,
                    media_dir,
                    media_db,
                )
            )

    unsub = await mqtt.async_subscribe(
        hass,
        "ring/#",
        message_received,
        1,
    )
    entry.async_on_unload(unsub)

    entry.add_update_listener(async_reload_entry)


async def async_reload_entry(hass, entry):
    """Reload the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def handle_mqtt_message(hass, camera_id, event_type, recorders, detector, media_dir, media_db):
    """Handle motion/ding MQTT messages that trigger recording and ML."""

    recorder = recorders.get(camera_id)
    if not recorder:
        return

    await asyncio.sleep(POST_EVENT_SECONDS)
    
    def _save_and_detect():
        try:
            media_path = create_media_paths(media_dir, camera_id)
            clip_path = get_clip_path(media_path, event_type)
            recorder.save_clip(clip_path, PRE_EVENT_SECONDS, POST_EVENT_SECONDS, CLIP_FPS)

            frames = recorder.buffer.get_all()
            face_detected = False
            snapshot_path = None
            for frame, ts in frames:
                _, face = detector.detect(frame, detect_motion=False, detect_faces=True)
                if face:
                    face_detected = True
                    snapshot_path = get_snapshot_path(media_path, f"{event_type}_face")
                    _save_snapshot(snapshot_path, frame)
                    break

            record_event(
                media_db,
                camera_id=camera_id,
                event_type=event_type,
                clip_path=clip_path,
                snapshot_path=snapshot_path,
                face_detected=face_detected,
                duration=PRE_EVENT_SECONDS + POST_EVENT_SECONDS,
            )
        except Exception as e:
            _LOGGER.exception("Error during save and detect: %s", e)


    await hass.async_add_executor_job(_save_and_detect)

class RingLocalMLEventSensor(SensorEntity):
    """Tracks the latest high-level event (motion/ding) per camera."""

    _attr_should_poll = False

    def __init__(self, camera_id, device_name):
        self._camera_id = camera_id
        self._attr_name = f"{device_name} Events"
        self._attr_unique_id = f"ring_local_ml_event_{camera_id}"
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {
            "camera_id": camera_id,
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, camera_id)},
            manufacturer="Ring",
            name=device_name,
        )

    def handle_event(self, event_type: str, payload: str):
        """Update the sensor state when motion or ding events arrive."""
        self._attr_native_value = event_type
        self._attr_extra_state_attributes = {
            "camera_id": self._camera_id,
            "payload": payload,
            "last_update": datetime.utcnow().isoformat(),
        }
        self.async_write_ha_state()