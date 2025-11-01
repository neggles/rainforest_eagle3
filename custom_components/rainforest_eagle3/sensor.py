"""Sensor platform for rainforest_eagle3."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from slugify import slugify

from . import Eagle3ConfigEntry
from .const import DOMAIN
from .coordinator import Eagle3Coordinator
from .eagle import EagleDevice, ElectricityMeter

_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="zigbee:InstantaneousDemand",
        translation_key="power_demand",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="zigbee:CurrentSummationDelivered",
        translation_key="total_energy_delivered",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="zigbee:CurrentSummationReceived",
        translation_key="total_energy_received",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    config_entry: Eagle3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator: Eagle3Coordinator = config_entry.runtime_data.coordinator

    sensors = []
    for meter in coordinator.data.meters.values():
        sensors.extend(
            [
                RainforestEagle3Sensor(
                    coordinator=coordinator, meter=meter, entity_description=entity_description
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ]
        )

    async_add_entities(sensors)


class RainforestEagle3Sensor(CoordinatorEntity, SensorEntity):
    """Eagle3 power meter sensor class."""

    coordinator: Eagle3Coordinator

    def __init__(
        self,
        coordinator: Eagle3Coordinator,
        meter: ElectricityMeter,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.meter = meter
        self.device = meter.device  # type: EagleDevice
        self.entity_description = entity_description
        self.key = entity_description.key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.meter = self.coordinator.data.meters.get(self.meter.hardware_address, self.meter)
        self.device = self.meter.device
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=self.meter.device.Name,
            identifiers={(DOMAIN, f"{self.meter.hardware_address}")},
            manufacturer=self.device.Manufacturer,
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.meter.device.Name + " " + self.translation_key.replace("_", " ").title()  # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.hub.online and self.device.ConnectionStatus == "Connected"

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.meter.hardware_address}-{self.translation_key}".lower()

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        variable = self.meter.get_variable(self.key)
        if variable.Value is not None:
            return float(variable.Value)
        return None
