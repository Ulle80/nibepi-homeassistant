"""Sensor platform for NibePi."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NibePiConfigEntry
from .const import SIGNAL_NEW_REGISTER
from .entity import NibePiEntity
from .hub import NibePiHub
from .models import NibeRegister

# NibePi unit string -> (HA unit, device class)
UNIT_MAP: dict[str, tuple[str | None, SensorDeviceClass | None]] = {
    "°C": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    "A": (UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT),
    "kW": (UnitOfPower.KILO_WATT, SensorDeviceClass.POWER),
    "W": (UnitOfPower.WATT, SensorDeviceClass.POWER),
    "kWh": (UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    "Hz": (UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY),
    "%": (PERCENTAGE, None),
    "h": (UnitOfTime.HOURS, SensorDeviceClass.DURATION),
    "min": (UnitOfTime.MINUTES, SensorDeviceClass.DURATION),
    "s": (UnitOfTime.SECONDS, SensorDeviceClass.DURATION),
    "l/m": (UnitOfVolumeFlowRate.LITERS_PER_MINUTE, SensorDeviceClass.VOLUME_FLOW_RATE),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NibePiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors for every register NibePi announces."""
    hub = entry.runtime_data

    @callback
    def _async_new_register(register: NibeRegister) -> None:
        async_add_entities([NibePiSensor(hub, register)])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_NEW_REGISTER.format(entry_id=entry.entry_id),
            _async_new_register,
        )
    )


class NibePiSensor(NibePiEntity, SensorEntity):
    """A read-only view of a NibePi register."""

    def __init__(self, hub: NibePiHub, register: NibeRegister) -> None:
        """Initialize the sensor."""
        super().__init__(hub, register)
        if register.is_enum:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(dict.fromkeys(register.mapping.values()))
            return

        unit, device_class = UNIT_MAP.get(register.unit, (register.unit or None, None))
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if device_class is SensorDeviceClass.ENERGY:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> str | float | None:
        """Return the current value."""
        value = self._register.value
        if self._register.is_enum:
            return str(value) if value in self._attr_options else None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
