"""Sensor platform for rainforest_eagle3."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Eagle3ConfigEntry
from .const import DOMAIN
from .coordinator import Eagle3Coordinator

ENTITY_DESCRIPTIONS = {
    "energy": [
        SensorEntityDescription(
            # no name, to make it the primary sensor entity
            key="zigbee:InstantaneousDemand",
            translation_key="power_demand",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=3,
        ),
        SensorEntityDescription(
            name="Total Energy Delivered",
            key="zigbee:CurrentSummationDelivered",
            translation_key="total_energy_delivered",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            suggested_display_precision=2,
        ),
        SensorEntityDescription(
            name="Total Energy Received",
            key="zigbee:CurrentSummationReceived",
            translation_key="total_energy_received",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            suggested_display_precision=2,
        ),
    ],
    "device": [
        SensorEntityDescription(
            name="Last Contact",
            key="last_contact",
            translation_key="last_contact",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_visible_default=False,
        ),
    ],
}


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
                Eagle3EnergySensor(coordinator=coordinator, address=meter.address, entity_description=desc)
                for desc in ENTITY_DESCRIPTIONS["energy"]
            ]
        )
        sensors.extend(
            [
                Eagle3DeviceSensor(coordinator=coordinator, address=meter.address, entity_description=desc)
                for desc in ENTITY_DESCRIPTIONS["device"]
            ]
        )

    async_add_entities(sensors)


class Eagle3EnergySensor(CoordinatorEntity, SensorEntity):
    """Eagle3 energy meter sensor class."""

    coordinator: Eagle3Coordinator

    def __init__(
        self,
        coordinator: Eagle3Coordinator,
        address: str,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.meter = coordinator.data.meters[address]

    @property
    def key(self) -> str:
        """Return the key of the sensor."""
        return self.entity_description.key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.meter = self.coordinator.data.meters.get(self.meter.address, self.meter)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=self.meter.device.Name,
            identifiers={(DOMAIN, f"{self.meter.device.HardwareAddress}")},
            manufacturer=self.meter.device.Manufacturer,
            model_id=self.meter.device.ModelId,
        )

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.hub.online and self.meter.connection_status == "Connected"

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.meter.address}-{self.translation_key}".lower()

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        variable = self.meter.get_variable(self.key)
        if variable.Value is not None:
            return float(variable.Value)
        return None


class Eagle3DeviceSensor(CoordinatorEntity, SensorEntity):
    """Eagle3 generic sensor class."""

    coordinator: Eagle3Coordinator

    def __init__(
        self,
        coordinator: Eagle3Coordinator,
        address: str,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.meter = coordinator.data.meters[address]

    @property
    def key(self) -> str:
        """Return the key of the sensor."""
        return self.entity_description.key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        self.meter = self.coordinator.data.meters.get(self.meter.address, self.meter)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=self.meter.device.Name,
            identifiers={(DOMAIN, f"{self.meter.device.HardwareAddress}")},
            manufacturer=self.meter.device.Manufacturer,
            model_id=self.meter.device.ModelId,
        )

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.hub.online and self.meter.connection_status == "Connected"

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.meter.address}-{self.translation_key}".lower()

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return getattr(self.meter, self.key, None)
