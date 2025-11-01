"""Eagle API models."""

from collections.abc import Sequence
from contextlib import suppress
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, field_validator, model_validator

from .util import get_ensure_list


class EagleApiCommand(str, Enum):
    """Known Eagle local API commands."""

    DEVICE_LIST = "device_list"
    DEVICE_DETAILS = "device_details"
    DEVICE_QUERY = "device_query"


class Variable(BaseModel):
    """Eagle API device variable model."""

    Name: str
    Value: int | float | str | None = None
    Description: str | None = None
    Units: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_value(cls, values: dict) -> dict:
        """Validate the Value field."""
        value = values.get("Value")
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            with suppress(ValueError, TypeError):
                value = bool(value)
        if isinstance(value, str):
            with suppress(ValueError, TypeError):
                value = int(value)
        if isinstance(value, str):
            with suppress(ValueError, TypeError):
                value = float(value)
        values["Value"] = value
        return values


class Component(BaseModel):
    """Eagle API device component model."""

    Name: str
    FixedId: str
    Variables: list[Variable | str]

    @model_validator(mode="before")
    @classmethod
    def unwrap_outer_dict(cls, data: dict) -> dict:
        """Unwrap outer dict if present."""
        return data.get("Component", data)

    @field_validator("Variables", mode="before")
    @classmethod
    def ensure_variables_list(cls, value: dict | list) -> Sequence[Variable | str]:
        """Ensure Variables is a list."""
        if isinstance(value, list):
            return value
        return get_ensure_list(value, "Variable")


class EagleDevice(BaseModel):
    """Eagle API EagleDevice model."""

    Name: str
    HardwareAddress: str
    Manufacturer: str
    ModelId: str
    Protocol: str
    LastContact: datetime | None = None
    ConnectionStatus: str | None = None
    NetworkAddress: str | None = None

    @model_validator(mode="before")
    @classmethod
    def unwrap_outer_dict(cls, data: dict) -> dict:
        """Unwrap outer dict if present."""
        return data.get("Device", data)

    @field_validator("LastContact", mode="before")
    @classmethod
    def parse_last_contact(cls, value: str | None) -> datetime | None:
        """Parse LastContact from hex timestamp to datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            timestamp = int(value, 16)
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (ValueError, TypeError):
            return None


class DeviceDetailsResponse(BaseModel):
    """Eagle API Device Details model."""

    DeviceDetails: EagleDevice
    Components: list[Component]

    @field_validator("Components", mode="before")
    @classmethod
    def ensure_components_list(cls, value: dict | list) -> list[Component]:
        """Ensure Components is a list."""
        if isinstance(value, list):
            return value
        if isinstance(value, dict) and "Component" in value:
            value = value["Component"]
        return value if isinstance(value, list) else [value]  # pyright: ignore[reportReturnType] #


class DeviceQueryResponse(BaseModel):
    """Eagle API Devices Query model."""

    DeviceDetails: EagleDevice
    Components: list[Component]

    @field_validator("Components", mode="before")
    @classmethod
    def ensure_components_list(cls, value: dict | list) -> list[Component]:
        """Ensure Components is a list."""
        if isinstance(value, list):
            return value
        if isinstance(value, dict) and "Component" in value:
            value = value["Component"]
        return value if isinstance(value, list) else [value]  # pyright: ignore[reportReturnType] #


class DeviceResponse(EagleDevice):
    """Eagle API Device Query response model."""

    Components: list[Component] | None = None

    @field_validator("Components", mode="before")
    @classmethod
    def ensure_components_list(cls, value: dict | list) -> list[Component]:
        """Ensure Components is a list."""
        if isinstance(value, list):
            return value
        if isinstance(value, dict) and "Component" in value:
            value = value["Component"]
        return value if isinstance(value, list) else [value]  # pyright: ignore[reportReturnType] #
