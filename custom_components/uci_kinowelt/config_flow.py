"""Config flow for UCI Kinowelt."""

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN, DEFAULT_CINEMA_ID, DEFAULT_CINEMA_NAME


class UciKinoweltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UCI Kinowelt."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input["cinema_id"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input["cinema_name"],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("cinema_name", default=DEFAULT_CINEMA_NAME): str,
                    vol.Required("cinema_id", default=DEFAULT_CINEMA_ID): str,
                }
            ),
        )
