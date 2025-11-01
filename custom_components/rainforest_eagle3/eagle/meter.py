"""Eagle API meter device."""

from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING

from .model import DeviceQueryResponse, EagleDevice, Variable

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
        device: "EagleDevice",
    ) -> None:
        """Initialize the ElectricityMeter."""
        if device.ModelId != "electric_meter":
            msg = "EagleDevice is not an electricity meter"
            raise ValueError(msg)

        self.hub = hub
        self.device = device
        self.components = []

    @property
    def hardware_address(self) -> str:
        """Return the hardware address of the meter."""
        return self.device.HardwareAddress

    @property
    def last_contact(self) -> "datetime | None":
        """Return the last contact time of the meter."""
        return self.device.LastContact

    async def refresh(self) -> None:
        """Refresh the meter data from the Eagle."""
        response: DeviceQueryResponse = await self.hub.async_query_device(self.device)
        details = response.DeviceDetails
        # lastcontact and these other fields will be none for a DeviceDetails query,
        # but not a DeviceQuery one. for. some reason.
        if details.LastContact is not None:
            self.device.ConnectionStatus = details.ConnectionStatus
            self.device.LastContact = details.LastContact
            self.device.NetworkAddress = details.NetworkAddress

        if response.Components:
            self.components = response.Components

    def get_variable(self, key: str) -> Variable:
        """Get a specific variable from the meter."""
        for component in self.components:
            for variable in component.Variables:
                if isinstance(variable, Variable) and variable.Name == key:
                    return variable
        msg = f"Variable {key} not found in meter {self.hardware_address}"
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
