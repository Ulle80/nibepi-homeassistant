"""Diagnostics for NibePi."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import NibePiConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: NibePiConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Contains no secrets: MQTT credentials live in the MQTT integration, NibePi
    publishes no serial numbers, and the topics are needed to debug setups.
    """
    hub = entry.runtime_data
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": dict(entry.data),
        },
        "hub": {
            "available": hub.available,
            "register_count": len(hub.registers),
            "registers_without_value": sorted(
                address
                for address, register in hub.registers.items()
                if register.value is None
            ),
        },
        "registers": {
            address: register.as_definition()
            | {
                "kind": register.kind.value,
                "value": register.value,
                "raw_value": register.raw_value,
                "timestamp": register.timestamp,
            }
            for address, register in sorted(hub.registers.items())
        },
    }
