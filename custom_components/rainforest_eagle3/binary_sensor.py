"""Binary sensor platform for rainforest_eagle3."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Eagle3ConfigEntry, Eagle3Coordinator
from .const import DOMAIN
from .eagle import ElectricityMeter

ENTITY_DESCRIPTIONS = [
    BinarySensorEntityDescription(
        key="connectivity",
        translation_key="device_connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: Eagle3ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: Eagle3Coordinator = entry.runtime_data.coordinator
    sensors = []
    for meter in coordinator.data.meters.values():
        sensors.extend(
            [
                Eagle3DeviceBinarySensor(
                    coordinator=coordinator, address=meter.address, entity_description=desc
                )
                for desc in ENTITY_DESCRIPTIONS
            ]
        )

    async_add_entities(sensors)


class Eagle3DeviceBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """rainforest_eagle3 binary_sensor class."""

    coordinator: Eagle3Coordinator
    meter: ElectricityMeter

    def __init__(
        self,
        coordinator: Eagle3Coordinator,
        address: str,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the device connectivity sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.device = coordinator.data.devices[address]

    @property
    def key(self) -> str:
        """Return the key of the sensor."""
        return self.entity_description.key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self.device = self.coordinator.data.devices[self.device.HardwareAddress]
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
            identifiers={(DOMAIN, f"{self.meter.address}")},
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Connectivity"

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.hub.online and self.device in self.coordinator.data.devices.values()

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.device.HardwareAddress}-{self.translation_key}".lower()

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        if self.key == "connectivity":
            return self.device.ConnectionStatus == "Connected"
        return False
