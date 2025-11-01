"""Adds config flow for Eagle3."""

import logging
from typing import Any

from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_POLL,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from slugify import slugify
import voluptuous as vol

from rainforest_eagle3.eagle.hub import EagleHub

from .const import CONF_CLOUD_ID, CONF_INSTALL_CODE, DOMAIN, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, description="Hostname or IP address"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_CLOUD_ID, description="Cloud ID"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_INSTALL_CODE, description="Install Code"): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    },
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL, max=60, step=1, unit_of_measurement="seconds"
            )
        ),
    }
)


async def validate_input(
    hass: HomeAssistant,
    hostname: str,
    cloud_id: str,
    install_code: str,
) -> dict[str, str]:
    """Validate credentials."""
    client = EagleHub(
        hostname=hostname,
        cloud_id=cloud_id,
        install_code=install_code,
        session=async_get_clientsession(hass),
    )
    await client.async_refresh_devices()
    title = f"{hostname.split('.')[0]} ({cloud_id})"
    return {"title": title, "unique_id": slugify(title)}


class Eagle3ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Eagle3."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL
    _input_data: dict[str, Any]

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,  # noqa: ARG004
    ) -> OptionsFlowWithReload:
        """Get the options flow for this handler."""
        return Eagle3OptionsFlowHandler()

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        _errors = {}
        if user_input is not None:
            try:
                info = await validate_input(
                    hass=self.hass,
                    hostname=user_input[CONF_HOST],
                    cloud_id=user_input[CONF_CLOUD_ID],
                    install_code=user_input[CONF_INSTALL_CODE],
                )
            except Exception:
                _LOGGER.exception("Failed to connect to Eagle Hub")
                _errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(unique_id=info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=_errors)


class Eagle3OptionsFlowHandler(OptionsFlowWithReload):
    """Config flow to handle options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the Eagle3 options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.config_entry.options),
        )
