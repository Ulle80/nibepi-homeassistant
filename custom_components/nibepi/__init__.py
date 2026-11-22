"""The NibePi integration."""

from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_BASE_TOPIC, CONF_LWT_TOPIC, DEFAULT_LWT_TOPIC
from .hub import NibePiHub, async_get_store

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type NibePiConfigEntry = ConfigEntry[NibePiHub]


async def async_setup_entry(hass: HomeAssistant, entry: NibePiConfigEntry) -> bool:
    """Set up NibePi from a config entry."""
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("MQTT integration is not available")

    hub = NibePiHub(
        hass,
        entry.entry_id,
        entry.data[CONF_BASE_TOPIC],
        entry.data.get(CONF_LWT_TOPIC, DEFAULT_LWT_TOPIC),
    )
    entry.runtime_data = hub

    # Platforms first, so their dispatcher listeners exist before the hub
    # restores stored registers or messages arrive.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await hub.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NibePiConfigEntry) -> bool:
    """Unload a config entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: NibePiConfigEntry) -> None:
    """Delete the stored register definitions when the entry is removed."""
    await async_get_store(hass, entry.entry_id).async_remove()
