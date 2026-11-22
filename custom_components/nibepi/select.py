"""Select platform for writable NibePi registers with a value map."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NibePiConfigEntry
from .entity import NibePiWritableEntity, async_setup_register_platform
from .hub import NibePiHub
from .models import NibeRegister, RegisterKind

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NibePiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add select entities for writable mapped registers."""
    async_setup_register_platform(
        hass, entry, async_add_entities, RegisterKind.SELECT, NibePiSelect
    )


class NibePiSelect(NibePiWritableEntity, SelectEntity):
    """A writable register whose values are labels."""

    def __init__(self, hub: NibePiHub, register: NibeRegister) -> None:
        """Initialize the select."""
        super().__init__(hub, register)
        self._attr_options = list(dict.fromkeys(register.mapping.values()))

    @property
    def current_option(self) -> str | None:
        """Return the active label."""
        return self._register.current_label

    async def async_select_option(self, option: str) -> None:
        """Write the numeric key for the chosen label (NibePi rejects labels)."""
        await self._async_write(self._register.key_for_label(option))
