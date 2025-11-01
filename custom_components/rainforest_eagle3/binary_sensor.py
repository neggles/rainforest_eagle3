"""Binary sensor platform for rainforest_eagle3."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from slugify import slugify

from . import Eagle3ConfigEntry, Eagle3Coordinator
from .const import DOMAIN
from .eagle import ElectricityMeter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: Eagle3ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: Eagle3Coordinator = entry.runtime_data.coordinator

    async_add_entities(
        EagleDeviceConnectivitySensor(coordinator=coordinator, meter=meter)
        for meter in coordinator.data.meters.values()
    )


class EagleDeviceConnectivitySensor(CoordinatorEntity, BinarySensorEntity):
    """rainforest_eagle3 binary_sensor class."""

    coordinator: Eagle3Coordinator
    meter: ElectricityMeter

    def __init__(
        self,
        coordinator: Eagle3Coordinator,
        meter: ElectricityMeter,
    ) -> None:
        """Initialize the device connectivity sensor."""
        super().__init__(coordinator)
        self.meter = meter
        self.device = meter.device
        self.entity_description = BinarySensorEntityDescription(
            key="connectivity", translation_key="device_connectivity"
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.meter = self.coordinator.hub.meters.get(self.meter.hardware_address, self.meter)
        self.device = self.meter.device
        self.async_write_ha_state()

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the device class."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=self.meter.device.Name,
            identifiers={(DOMAIN, f"{self.meter.hardware_address}")},
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.meter.device.Name + " " + slugify(self.device_class, separator=" ").title()

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.hub.online and self.meter in self.coordinator.data.meters.values()

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.hub.online and self.meter.device.ConnectionStatus == "Connected"

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        # All entities must have a unique id.  Think carefully what you want this to be as
        # changing it later will cause HA to create new entities.
        return f"{self.meter.hardware_address}-{slugify(self.device_class)}"

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return the state attributes."""
        last_contact = (
            self.meter.device.LastContact.strftime("%Y-%m-%d %H:%M:%S")
            if self.meter.device.LastContact
            else None
        )
        return {
            "hardware_address": self.meter.hardware_address,
            "last_contact": last_contact,
            "connection_status": self.meter.device.ConnectionStatus,
            "network_address": self.meter.device.NetworkAddress,
        }
