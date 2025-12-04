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

    MENU_ADD = "add_camera"
    MENU_EDIT = "edit_camera"
    MENU_FINISH = "finish"

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        # Do NOT overwrite the base class' `config_entry` property; store
        # the passed entry in a private attribute instead.
        self._config_entry = config_entry
        self.options = dict(self._config_entry.options)
        self.options.setdefault("cameras", [])
        self._editing_index = None

    def _suggest_name(self, camera_id: str) -> str:
        if not camera_id:
            return ""
        suffix = camera_id[-4:]
        return f"Ring Camera {suffix}" if suffix else f"Ring Camera {camera_id}"

    async def async_step_init(self, user_input=None):
        """Handle the initial step."""
        return await self.async_step_camera()

    async def async_step_camera(self, user_input=None):
        """Handle the camera configuration step."""
        errors = {}
        defaults = user_input or {}
        suggested = defaults.get("name") or self._suggest_name(defaults.get("id", ""))
        schema = vol.Schema(
            {
                vol.Required("id", default=defaults.get("id", "")): str,
                vol.Optional("name", default=suggested): str,
                vol.Required("rtsp_url", default=defaults.get("rtsp_url", "")): str,
            }
        )

        if user_input is not None:
            camera_id = user_input["id"].strip()
            if not camera_id:
                errors["id"] = "required"
            elif any(c.get("id") == camera_id for c in self.options["cameras"]):
                errors["base"] = "duplicate_id"
            else:
                name = user_input.get("name") or self._suggest_name(camera_id)
                camera = {
                    "id": camera_id,
                    "name": name.strip(),
                    "rtsp_url": user_input.get("rtsp_url", "").strip(),
                }
                self.options["cameras"].append(camera)
                return await self.async_step_camera_menu()

        return self.async_show_form(
            step_id="camera",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_camera_menu(self, user_input=None):
        """Let the user choose to add another camera or finish."""
        if user_input is not None:
            action = user_input.get("action")
            if action == self.MENU_ADD:
                return await self.async_step_camera()
            if action == self.MENU_EDIT:
                if not self.options["cameras"]:
                    errors = {"base": "no_cameras"}
                else:
                    return await self.async_step_select_camera()
            if action == self.MENU_FINISH:
                return await self.async_step_finish()

        choices = {
            self.MENU_ADD: "Add another camera",
            self.MENU_EDIT: "Edit existing camera",
            self.MENU_FINISH: "Save cameras",
        }

        if not self.options["cameras"]:
            choices.pop(self.MENU_EDIT)

        return self.async_show_form(
            step_id="camera_menu",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default=self.MENU_FINISH): vol.In(choices)
                }
            ),
            description_placeholders={
                "count": str(len(self.options.get("cameras", [])))
            },
        )

    async def async_step_select_camera(self, user_input=None):
        cameras = self.options.get("cameras", [])
        choices = {cam["id"]: cam.get("name", cam["id"]) for cam in cameras}
        if not choices:
            return await self.async_step_camera_menu()

        if user_input is not None:
            camera_id = user_input.get("camera_id")
            for index, camera in enumerate(cameras):
                if camera["id"] == camera_id:
                    self._editing_index = index
                    return await self.async_step_edit_camera()
            errors = {"camera_id": "not_found"}
        else:
            errors = {}

        return self.async_show_form(
            step_id="select_camera",
            data_schema=vol.Schema(
                {vol.Required("camera_id"): vol.In(choices)}
            ),
            errors=errors,
        )

    async def async_step_edit_camera(self, user_input=None):
        if self._editing_index is None:
            return await self.async_step_camera_menu()

        camera = self.options["cameras"][self._editing_index]
        defaults = {
            "name": camera.get("name", self._suggest_name(camera["id"])),
            "rtsp_url": camera.get("rtsp_url", ""),
        }
        schema = vol.Schema(
            {
                vol.Optional("name", default=defaults["name"]): str,
                vol.Required("rtsp_url", default=defaults["rtsp_url"]): str,
            }
        )

        if user_input is not None:
            camera["name"] = user_input.get("name") or self._suggest_name(camera["id"])
            camera["rtsp_url"] = user_input.get("rtsp_url", "")
            self.options["cameras"][self._editing_index] = camera
            self._editing_index = None
            return await self.async_step_camera_menu()

        return self.async_show_form(
            step_id="edit_camera",
            data_schema=schema,
        )
    
    async def async_step_finish(self, user_input=None):
        """Handle the finish step."""
        # Provide a meaningful title so the options-flow finish dialog shows
        # readable text instead of an empty popup.
        title = "Ring Local ML Cameras"
        return self.async_create_entry(title=title, data=self.options)
