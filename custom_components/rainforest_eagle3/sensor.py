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
    ),
    SensorEntityDescription(
        key="zigbee:CurrentSummationDelivered",
        translation_key="total_energy_delivered",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="zigbee:CurrentSummationReceived",
        translation_key="total_energy_received",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
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
        self.entity_description = entity_description
        self.key = entity_description.key

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.cloud_id}-{self.meter.hardware_address}")}
        )

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.hub.online and self.meter.device.ConnectionStatus == "Connected"

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return slugify(f"{DOMAIN}-{self.coordinator.cloud_id}-{self.meter.hardware_address}-{self.key}")

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        variable = self.meter.get_variable(self.key)
        if variable.Value is not None:
            return float(variable.Value)
        return None
