"""Config flow for Ring Local ML integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_MQTT_HOST, CONF_MQTT_PORT, CONF_MEDIA_DIR

_LOGGER = logging.getLogger(__name__)


class RingLocalMLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ring Local ML."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            try:
                return self.async_create_entry(title="Ring Local ML", data=user_input)
            except Exception:  # Guard: don't expose raw exception text (may contain HTML)
                _LOGGER.exception("Failed to create config entry from user input")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MQTT_HOST, default="localhost"): str,
                    vol.Required(CONF_MQTT_PORT, default=1883): int,
                    vol.Required(CONF_MEDIA_DIR, default="/media/ring_local_ml"): str,
                }
            ),
            errors=errors,
        )