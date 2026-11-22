"""Number platform for writable numeric NibePi registers."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NibePiConfigEntry
from .entity import NibePiWritableEntity, async_setup_register_platform
from .hub import NibePiHub
from .models import NibeRegister, RegisterKind
from .sensor import UNIT_MAP

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NibePiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add number entities for writable numeric registers."""
    async_setup_register_platform(
        hass, entry, async_add_entities, RegisterKind.NUMBER, NibePiNumber
    )


class NibePiNumber(NibePiWritableEntity, NumberEntity):
    """A writable numeric register."""

    _attr_mode = NumberMode.BOX

    def __init__(self, hub: NibePiHub, register: NibeRegister) -> None:
        """Initialize the number."""
        super().__init__(hub, register)
        self._attr_native_min_value, self._attr_native_max_value = register.limits
        self._attr_native_step = register.step
        unit, device_class = UNIT_MAP.get(register.unit, (register.unit or None, None))
        self._attr_native_unit_of_measurement = unit
        # Sensor and number device classes share their string values.
        if device_class is not None:
            try:
                self._attr_device_class = NumberDeviceClass(device_class.value)
            except ValueError:
                self._attr_device_class = None

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        try:
            return float(self._register.value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value."""
        await self._async_write(self._register.encode_value(value))
