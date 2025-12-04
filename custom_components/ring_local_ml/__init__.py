"""The Ring Local ML integration."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

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
                topic_parts = msg.topic.split("/")
                if len(topic_parts) < 2:
                    return
                camera_id = topic_parts[1]

                # Decode payload
                payload = msg.payload
                if isinstance(payload, bytes):
                    try:
                        payload_text = payload.decode("utf-8")
                    except Exception:
                        payload_text = str(payload)
                else:
                    payload_text = str(payload)

                # Try JSON first
                rtsp_url = None
                try:
                    parsed = json.loads(payload_text)
                    for key in ("rtsp", "rtsp_url", "stream", "path", "url"):
                        if key in parsed and isinstance(parsed[key], str) and parsed[key].startswith("rtsp"):
                            rtsp_url = parsed[key]
                            break
                except Exception:
                    # Not JSON — fall back to searching for an rtsp substring
                    m = re.search(r"rtsp://[\w:@\-\._~%/]+", payload_text)
                    if m:
                        rtsp_url = m.group(0)

                # Update the config entry options (if camera not already present)
                options = dict(entry.options)
                cameras = options.setdefault("cameras", [])
                if any(c.get("id") == camera_id for c in cameras):
                    return

                suffix = camera_id[-4:] if camera_id else ""
                candidate = {
                    "id": camera_id,
                    "name": f"Ring Camera {suffix}" if suffix else f"Ring Camera {camera_id}",
                }
                if rtsp_url:
                    candidate["rtsp_url"] = rtsp_url
                else:
                    # leave rtsp_url empty so user can fill it in; we still
                    # add the camera id so the MQTT sensors get created.
                    candidate["rtsp_url"] = ""

                cameras.append(candidate)
                hass.config_entries.async_update_entry(entry, options=options)
                _LOGGER.info("Discovered Ring camera '%s' via MQTT; added to options", camera_id)
            except Exception:
                _LOGGER.debug("Error handling MQTT discovery message", exc_info=True)

        # Subscribe to ring topics for this entry. Keep the returned unsubscribe
        # callable so we can remove the subscription on unload.
        unsub = await mqtt.async_subscribe(hass, "ring/+/+", _on_mqtt_message, 1)
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
