"""Base entity for NibePi."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_AVAILABILITY,
    SIGNAL_NEW_REGISTER,
    SIGNAL_REGISTER_UPDATE,
)
from .hub import NibePiHub
from .models import NibeRegister, RegisterKind

if TYPE_CHECKING:
    from . import NibePiConfigEntry


@callback
def async_setup_register_platform(
    hass: HomeAssistant,
    entry: NibePiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    kind: RegisterKind,
    factory: Callable[[NibePiHub, NibeRegister], Entity],
) -> None:
    """Create an entity whenever NibePi announces a register of ``kind``."""
    hub = entry.runtime_data

    @callback
    def _async_new_register(register: NibeRegister) -> None:
        if register.kind is kind:
            async_add_entities([factory(hub, register)])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_NEW_REGISTER.format(entry_id=entry.entry_id),
            _async_new_register,
        )
    )


class NibePiEntity(Entity):
    """Entity bound to one NibePi register."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: NibePiHub, register: NibeRegister) -> None:
        """Initialize the entity."""
        self._hub = hub
        self._register = register
        # Register titles come from the pump's model file and are not translatable.
        self._attr_name = register.title
        self._attr_unique_id = f"{hub.entry_id}_{register.register}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.entry_id)},
            manufacturer="NIBE",
            model="Heat pump (via NibePi)",
            name="NibePi",
        )

    @property
    def available(self) -> bool:
        """Return if the NibePi is reachable."""
        return self._hub.available and self._register.value is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to register and availability updates."""
        entry_id = self._hub.entry_id
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_REGISTER_UPDATE.format(
                    entry_id=entry_id, register=self._register.register
                ),
                self._handle_update,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_AVAILABILITY.format(entry_id=entry_id),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class NibePiWritableEntity(NibePiEntity):
    """Entity for an R/W register (number, select, switch)."""

    _attr_entity_category = EntityCategory.CONFIG

    async def _async_write(self, payload: str) -> None:
        await self._hub.async_write(self._register.register, payload)
