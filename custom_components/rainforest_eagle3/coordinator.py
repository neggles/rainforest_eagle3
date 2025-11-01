"""DataUpdateCoordinator for rainforest_eagle3."""

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

import async_timeout
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_CLOUD_ID, CONF_INSTALL_CODE, DEFAULT_SCAN_INTERVAL, DOMAIN
from .eagle import EagleDevice, EagleHub, ElectricityMeter

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import Eagle3ConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass
class Eagle3DeviceData:
    """Class to hold API response data."""

    cloud_id: str
    devices: list[EagleDevice]
    meters: dict[str, ElectricityMeter]


class Eagle3Coordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: "Eagle3ConfigEntry"
    data: Eagle3DeviceData

    def __init__(self, hass: "HomeAssistant", config_entry: "Eagle3ConfigEntry") -> None:
        """Initialize coordinator."""
        self.host = config_entry.data[CONF_HOST]
        self.cloud_id = config_entry.data[CONF_CLOUD_ID]
        self.install_code = config_entry.data[CONF_INSTALL_CODE]
        self.poll_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            config_entry=config_entry,
            update_interval=timedelta(seconds=self.poll_interval),
            update_method=self.async_update_data,
        )

        self.hub = EagleHub(
            hostname=self.host,
            cloud_id=self.cloud_id,
            install_code=self.install_code,
            session=async_get_clientsession(hass=hass),
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator by connecting to the hub."""
        try:
            async with async_timeout.timeout(10):
                await self.hub.async_refresh_devices()
        except Exception as e:
            msg = "Failed to connect to Eagle Hub"
            raise ConfigEntryAuthFailed(msg) from e

    async def async_update_data(self) -> Any:
        """Update data via library."""
        try:
            async with async_timeout.timeout(10):
                await self.hub.async_refresh_devices()
                devices = self.hub.devices
                meters = self.hub.meters
        except Exception as err:
            msg = "Error communicating with API"
            _LOGGER.exception(msg)
            raise UpdateFailed(msg) from err
        return Eagle3DeviceData(cloud_id=self.cloud_id, meters=meters, devices=devices)

    def get_device_by_hardware_address(self, hardware_address: str) -> EagleDevice | None:
        """Get device by hardware address."""
        for device in self.hub.devices:
            if device.HardwareAddress == hardware_address:
                return device
        return None
