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
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, "sensor")
        )
    except Exception:
        _LOGGER.exception("Failed to forward entry setup to sensor platform for %s", entry.entry_id)
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    try:
        # Forward the unload to the sensor platform
        return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    except Exception:
        _LOGGER.exception("Failed to unload entry %s", entry.entry_id)
        return False
