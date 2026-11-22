"""Switch platform for writable 0/1 NibePi registers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NibePiConfigEntry
from .entity import NibePiWritableEntity, async_setup_register_platform
from .models import RegisterKind

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NibePiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add switches for writable on/off registers."""
    async_setup_register_platform(
        hass, entry, async_add_entities, RegisterKind.SWITCH, NibePiSwitch
    )


class NibePiSwitch(NibePiWritableEntity, SwitchEntity):
    """A writable register with range 0..1."""

    @property
    def is_on(self) -> bool | None:
        """Return True if the register is 1."""
        return self._register.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Write 1 (NibePi only accepts numbers, not 'on'/'true')."""
        await self._async_write("1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Write 0."""
        await self._async_write("0")
