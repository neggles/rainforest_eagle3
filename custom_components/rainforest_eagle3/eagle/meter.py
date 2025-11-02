"""Eagle API meter device."""

from enum import Enum
from typing import TYPE_CHECKING

from .model import Component, EagleDevice, Variable

if TYPE_CHECKING:
    from datetime import datetime

    from .hub import EagleHub


class MeterVariable(str, Enum):
    """Eagle API Meter Variables."""

    PowerDemand = "zigbee:InstantaneousDemand"
    EnergyDelivered = "zigbee:CurrentSummationDelivered"
    EnergyReceived = "zigbee:CurrentSummationReceived"


class ElectricityMeter:
    """Eagle API Electricity Meter device."""

    def __init__(
        self,
        hub: "EagleHub",
        address: str,
    ) -> None:
        """Initialize the ElectricityMeter."""
        self.hub = hub
        self.address = address

    @property
    def device(self) -> EagleDevice:
        """Return the underlying EagleDevice."""
        return self.hub.devices[self.address]

    @property
    def last_contact(self) -> "datetime | None":
        """Return the last contact time of the meter."""
        return self.device.LastContact

    @property
    def connection_status(self) -> str:
        """Return the connection status of the meter."""
        return self.device.ConnectionStatus or "Unknown"

    @property
    def components(self) -> list[Component]:
        """Return the components of the meter."""
        return self.device.Components or []

    async def refresh(self) -> None:
        """Refresh the meter data from the hub."""
        await self.hub.async_refresh_device(self.address)

    def get_variable(self, key: str) -> Variable:
        """Get a specific variable from the meter."""
        for component in self.components:
            for variable in component.Variables:
                if isinstance(variable, Variable) and variable.Name == key:
                    return variable
        msg = f"Variable {key} not found in meter {self.address}"
        raise KeyError(msg)

    def get_all_variables(self, include_null: bool = False) -> list[Variable]:
        """Get all variables from the meter."""
        variables: list[Variable] = []
        for component in self.components:
            variables.extend(
                [
                    x
                    for x in component.Variables
                    if isinstance(x, Variable) and (include_null or x.Value is not None)
                ]
            )
        return variables
