"""Adds config flow for Eagle3."""

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import CONN_CLASS_LOCAL_POLL, ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
    SchemaOptionsFlowHandlerWithReload,
)
import voluptuous as vol

from .const import CONF_CLOUD_ID, CONF_INSTALL_CODE, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL
from .eagle.hub import EagleHub

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
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL, max=60, step=1, unit_of_measurement="seconds"
            )
        ),
    }
)
OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}


async def validate_input(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    hostname: str,
    cloud_id: str,
    install_code: str,
) -> dict[str, str]:
    """Validate credentials."""
    # make client
    hub = EagleHub(hostname=hostname, cloud_id=cloud_id, install_code=install_code)
    # refresh devices
    await hub.async_refresh_devices()
    # check online
    if not hub.online:
        msg = "Unable to connect to Eagle Hub"
        raise ConnectionError(msg)
    await hub.session.close()
    return {
        "title": f"{hostname.split('.')[0]} ({cloud_id})",
        "unique_id": f"{cloud_id.lower()}-{install_code[-4:]}",
    }


class Eagle3ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Eagle3."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL
    _input_data: dict[str, Any]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
                _LOGGER.debug("Successfully connected to Eagle Hub at %s", user_input[CONF_HOST])
                await asyncio.sleep(1)  # or the hub gets angry
            except ConnectionError:
                _LOGGER.exception("Failed to connect to Eagle Hub")
                _errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(unique_id=info["unique_id"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(data_schema=STEP_USER_DATA_SCHEMA, errors=_errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,  # noqa: ARG004
    ) -> SchemaOptionsFlowHandlerWithReload:
        """Get the options flow for this handler."""
        return SchemaOptionsFlowHandlerWithReload(config_entry, OPTIONS_FLOW)
