"""Base entity for NibePi."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_AVAILABILITY, SIGNAL_REGISTER_UPDATE
from .hub import NibePiHub
from .models import NibeRegister


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
