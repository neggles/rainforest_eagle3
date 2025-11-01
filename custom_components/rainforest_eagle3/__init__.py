"""
Custom integration to integrate rainforest_eagle3 with Home Assistant.

For more details about this integration, please refer to
https://github.com/neggles/rainforest_eagle3
"""

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import Eagle3Coordinator

type Eagle3ConfigEntry = ConfigEntry[Eagle3ApiData]


_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


@dataclass
class Eagle3ApiData:
    """Data for the Eagle3 integration."""

    coordinator: Eagle3Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Eagle3ConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = Eagle3Coordinator(hass=hass, config_entry=entry)

    await coordinator.async_config_entry_first_refresh()
    if not coordinator.hub.online:
        raise ConfigEntryNotReady

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: Eagle3ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: Eagle3ConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
