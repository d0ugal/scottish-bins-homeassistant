"""The East Dunbartonshire integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EastDunbartonshireCoordinator
from .road_works import RoadWorksCoordinator
from .school_holidays import SchoolHolidaysCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})

    # Bins coordinator — per config entry (per address)
    bins_coordinator = EastDunbartonshireCoordinator(hass, entry)
    await bins_coordinator.async_config_entry_first_refresh()
    domain_data[entry.entry_id] = bins_coordinator

    # School holidays and road works coordinators — shared across all entries, set up once
    if "school_holidays" not in domain_data:
        school_coordinator = SchoolHolidaysCoordinator(hass)
        await school_coordinator.async_config_entry_first_refresh()
        domain_data["school_holidays"] = school_coordinator

    if "road_works" not in domain_data:
        road_works_coordinator = RoadWorksCoordinator(hass)
        await road_works_coordinator.async_config_entry_first_refresh()
        domain_data["road_works"] = road_works_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        domain_data = hass.data[DOMAIN]
        domain_data.pop(entry.entry_id)
        # Remove shared coordinators only when the last entry is removed
        if not any(k for k in domain_data if k not in ("school_holidays", "road_works")):
            domain_data.pop("school_holidays", None)
            domain_data.pop("road_works", None)
    return unload_ok
