"""Config flow for the Qubo integration."""

import logging
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import BASE_URL, CONF_PASSWORD, CONF_USERNAME, DOMAIN,LOGIN_DEVICE_NAME,DEVICE_ATTRIBUTE,APP_ID

_LOGGER = logging.getLogger(__name__)

# The form layout users will see in the UI
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    login_url = f"{BASE_URL}/sms/api/v4/sp/d10e4bfb0153496e8e8bb955f7ebe413/user/login"

    payload = {
        "accessToken": "",
        "deviceAttribute": DEVICE_ATTRIBUTE,
        "username": data[CONF_USERNAME],
        "password": data[CONF_PASSWORD],
    }

    # Generate a random 16-character hex string for this specific Home Assistant instance
    client_id = uuid.uuid4().hex[:16]

    headers = {
        "Content-Type": "application/json",
        "Host": "srvcapp.platform.quboworld.com",
        "User-Agent": "libcurl-agent restclient-cpp/2:1:1",
        "App-Id": APP_ID,
        "Login-Device-Name": LOGIN_DEVICE_NAME,  # Use the constant for the device name
        "Source": "ANDROID",
        "Source-Device-Id": client_id,
        "Token-Type": "USER",
    }
    params = {"system": "CS"}

    async with session.post(
        login_url, json=payload, headers=headers, params=params
    ) as response:
        if response.status in {401, 403}:
            raise InvalidAuth
        if response.status >= 400:
            raise CannotConnect

        # If we get here, credentials are valid!
        return {"title": data[CONF_USERNAME],"client_id": client_id}


class QuboConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Qubo."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Make sure the integration isn't already set up
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                info = await validate_input(self.hass, user_input)

                # Save the credentials AND the newly generated client ID
                data_to_save = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    "client_id": info["client_id"] # Save it here!
                }

                # Save the credentials and create the integration entry
                return self.async_create_entry(title=info["title"], data=data_to_save)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show the form to the user
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
