"""DataUpdateCoordinator for rainforest_eagle3."""

from dataclasses import dataclass
from datetime import timedelta
from functools import partial
import logging
from typing import TYPE_CHECKING, Any

import async_timeout
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_CLOUD_ID, CONF_INSTALL_CODE, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL
from .eagle import EagleDevice, EagleHub, ElectricityMeter

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import Eagle3ConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass
class Eagle3DeviceData:
    """Class to hold API response data."""

    cloud_id: str
    devices: dict[str, EagleDevice]
    meters: dict[str, ElectricityMeter]


class Eagle3Coordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: "Eagle3ConfigEntry"
    data: Eagle3DeviceData

    def __init__(
        self,
        hass: "HomeAssistant",
        config_entry: "Eagle3ConfigEntry",
    ) -> None:
        """Initialize coordinator."""
        self.host = config_entry.data[CONF_HOST]
        self.cloud_id = config_entry.data[CONF_CLOUD_ID]
        self.install_code = config_entry.data[CONF_INSTALL_CODE]
        self.poll_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_interval=timedelta(seconds=self.poll_interval),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=MIN_SCAN_INTERVAL, immediate=True),
            always_update=True,
        )

        session_callback = partial(async_create_clientsession, hass=hass)
        self.hub = EagleHub(
            session_callback=session_callback,
            hostname=self.host,
            cloud_id=self.cloud_id,
            install_code=self.install_code,
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator by connecting to the hub."""
        try:
            async with async_timeout.timeout(min(self.poll_interval - 1, 10)):
                await self.hub.async_refresh_devices()
        except Exception as e:
            msg = "Failed to connect to Eagle Hub"
            raise ConfigEntryAuthFailed(msg) from e

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            async with async_timeout.timeout(min(self.poll_interval - 1, 10)):
                await self.hub.async_refresh_devices()
        except Exception as err:
            msg = "Error communicating with API"
            _LOGGER.exception(msg)
            raise UpdateFailed(msg) from err
        return Eagle3DeviceData(cloud_id=self.cloud_id, meters=self.hub.meters, devices=self.hub.devices)
