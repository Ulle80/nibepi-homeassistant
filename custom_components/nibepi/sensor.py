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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NibePiConfigEntry
from .entity import NibePiEntity, async_setup_register_platform
from .hub import NibePiHub
from .models import NibeRegister, RegisterKind

# Push-based, nothing to parallelize.
PARALLEL_UPDATES = 0

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
    "days": (UnitOfTime.DAYS, SensorDeviceClass.DURATION),
    "d": (UnitOfTime.DAYS, SensorDeviceClass.DURATION),
    "l/m": (UnitOfVolumeFlowRate.LITERS_PER_MINUTE, SensorDeviceClass.VOLUME_FLOW_RATE),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NibePiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors for every read-only register NibePi announces."""
    async_setup_register_platform(
        hass, entry, async_add_entities, RegisterKind.SENSOR, NibePiSensor
    )


class NibePiSensor(NibePiEntity, SensorEntity):
    """A read-only view of a NibePi register."""

    def __init__(self, hub: NibePiHub, register: NibeRegister) -> None:
        """Initialize the sensor."""
        super().__init__(hub, register)
        if register.is_enum:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = self._label_options()
            return

        unit, device_class = UNIT_MAP.get(register.unit, (register.unit or None, None))
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_suggested_display_precision = register.decimals
        if device_class is SensorDeviceClass.ENERGY or register.is_counter:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> str | float | None:
        """Return the current value."""
        if self._register.is_enum:
            return self._current_label()
        try:
            return float(self._register.value)
        except (TypeError, ValueError):
            return None
