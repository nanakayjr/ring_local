"""The Ring Local ML integration."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .mqtt import parse_ring_topic, SUPPORTED_RING_CATEGORIES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Ring Local ML from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Forward the setup to the sensor platform. Wrap in try/except so errors
    # are logged and do not raise uncaught exceptions that surface as 500.
    try:
        # Await the forward setup so the integration setup lock remains held
        # until the platforms are fully set up. Scheduling the call as a
        # background task releases the lock early and will stop working in
        # newer Home Assistant versions.
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    except Exception:
        _LOGGER.exception("Failed to forward entry setup to sensor platform for %s", entry.entry_id)
        return False

    # Best-effort: automatically discover Ring-MQTT cameras by listening to
    # MQTT topics under `ring/+/+`. When a camera id is observed we append it
    # to the config entry options so the integration can manage recorders.
    try:
        import homeassistant.components.mqtt as mqtt
        from homeassistant.core import callback
        import json
        import re

        @callback
        def _on_mqtt_message(msg):
            try:
                topic = parse_ring_topic(msg.topic)
                if not topic or topic.category not in SUPPORTED_RING_CATEGORIES:
                    return

                if topic.topic_suffix.endswith("image"):
                    return

                last_segment = topic.topic_suffix.split("/")[-1] if topic.topic_suffix else ""
                if last_segment.endswith("command"):
                    return

                device_id = topic.device_id
                location_id = topic.location_id
                if not device_id:
                    return

                # Decode payload
                payload = msg.payload
                if isinstance(payload, bytes):
                    try:
                        payload_text = payload.decode("utf-8")
                    except Exception:
                        payload_text = str(payload)
                else:
                    payload_text = str(payload)

                # Try JSON first for RTSP hints
                rtsp_url = None
                try:
                    parsed = json.loads(payload_text)
                    for key in ("rtsp", "rtsp_url", "stream", "path", "url"):
                        value = parsed.get(key)
                        if isinstance(value, str) and value.startswith("rtsp"):
                            rtsp_url = value
                            break
                except Exception:
                    m = re.search(r"rtsp://[\w:@\-\._~%/]+", payload_text)
                    if m:
                        rtsp_url = m.group(0)

                options = dict(entry.options)
                cameras = options.setdefault("cameras", [])
                if any(c.get("id") == device_id for c in cameras):
                    return

                legacy_camera = next((c for c in cameras if c.get("id") == location_id), None)
                if legacy_camera:
                    legacy_camera["id"] = device_id
                    legacy_camera.setdefault("location_id", location_id)
                    legacy_camera.setdefault("category", topic.category)
                    if rtsp_url and not legacy_camera.get("rtsp_url"):
                        legacy_camera["rtsp_url"] = rtsp_url
                    hass.config_entries.async_update_entry(entry, options=options)
                    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
                    _LOGGER.info(
                        "Updated Ring camera '%s' to device id %s",
                        legacy_camera.get("name", device_id),
                        device_id,
                    )
                    return

                suffix = device_id[-4:] if device_id else ""
                candidate = {
                    "id": device_id,
                    "name": f"Ring Camera {suffix}" if suffix else f"Ring Camera {device_id}",
                    "rtsp_url": rtsp_url or "",
                    "location_id": location_id,
                    "category": topic.category,
                }

                cameras.append(candidate)
                hass.config_entries.async_update_entry(entry, options=options)
                hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
                _LOGGER.info("Discovered Ring camera '%s' via MQTT; added to options", device_id)
            except Exception:
                _LOGGER.debug("Error handling MQTT discovery message", exc_info=True)

        # Subscribe to ring topics for this entry. Keep the returned unsubscribe
        # callable so we can remove the subscription on unload.
        unsub = await mqtt.async_subscribe(hass, "ring/#", _on_mqtt_message, 1)
        hass.data[DOMAIN].setdefault(entry.entry_id, {})["mqtt_unsub"] = unsub
    except Exception:
        _LOGGER.debug("MQTT discovery unavailable; skipping auto-discovery of Ring cameras")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    try:
        # Remove MQTT discovery subscription if present
        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        unsub = entry_data.get("mqtt_unsub")
        try:
            if callable(unsub):
                unsub()
        except Exception:
            _LOGGER.debug("Failed to unsubscribe MQTT discovery", exc_info=True)

        # Forward the unload to the sensor platform
        return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    except Exception:
        _LOGGER.exception("Failed to unload entry %s", entry.entry_id)
        return False
