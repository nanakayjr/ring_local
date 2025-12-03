"""Config flow for Ring Local ML integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_MQTT_HOST, CONF_MQTT_PORT, CONF_MEDIA_DIR

class RingLocalMLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ring Local ML."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Ring Local ML", data=user_input)

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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RingLocalMLOptionsFlowHandler(config_entry)


class RingLocalMLOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Ring Local ML."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Handle the initial step."""
        return await self.async_step_camera()

    async def async_step_camera(self, user_input=None):
        """Handle the camera configuration step."""
        errors = {}
        if user_input is not None:
            self.options.setdefault("cameras", []).append(user_input)
            return await self.async_step_camera_menu()

        return self.async_show_form(
            step_id="camera",
            data_schema=vol.Schema(
                {
                    vol.Required("id"): str,
                    vol.Required("rtsp_url"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_camera_menu(self, user_input=None):
        """Handle the camera menu step."""
        return self.async_show_menu(
            step_id="camera_menu",
            menu_options=["camera", "finish"],
        )
    
    async def async_step_finish(self, user_input=None):
        """Handle the finish step."""
        return self.async_create_entry(title="", data=self.options)
