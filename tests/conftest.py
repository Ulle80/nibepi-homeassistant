"""Fixtures for NibePi tests."""

from __future__ import annotations

from collections.abc import Generator
import json

from homeassistant.components.mqtt.models import DATA_MQTT
from homeassistant.core import HomeAssistant
import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]

# Verbatim structure of a NibePi /json payload (models/F750.json + runtime fields).
OUTDOOR_TEMP_PAYLOAD = json.dumps(
    {
        "register": "40004",
        "factor": 10,
        "size": "s16",
        "mode": "R",
        "titel": "BT1 Outdoor Temperature",
        "info": "Current outdoor temperature",
        "unit": "°C",
        "min": "-500",
        "max": "500",
        "data": -3.5,
        "raw_data": -35,
        "timestamp": 1732272000000,
    }
)

PRICE_LEVEL_PAYLOAD = json.dumps(
    {
        "register": "41929",
        "factor": 1,
        "size": "u8",
        "mode": "R",
        "titel": "Price level",
        "info": "",
        "unit": "",
        "min": "0",
        "max": "3",
        "map": [{"0": "UNKNOWN"}, {"1": "CHEAP"}, {"2": "NORMAL"}, {"3": "EXPENSIVE"}],
        "data": "CHEAP",
        "raw_data": 1,
    }
)

# Writable, factor 10 -> number entity with 0.1 steps.
ROOM_SETPOINT_PAYLOAD = json.dumps(
    {
        "register": "47398",
        "factor": 10,
        "size": "s16",
        "mode": "R/W",
        "titel": "Room sensor setpoint S1",
        "info": "",
        "unit": "°C",
        "min": "50",
        "max": "350",
        "data": 21.5,
        "raw_data": 215,
    }
)

# Writable, factor 1, range 0..1, no unit -> switch.
ADJUST_AFFECT_PAYLOAD = json.dumps(
    {
        "register": "40881",
        "factor": 1,
        "size": "u8",
        "mode": "R/W",
        "titel": "=+Adjust Affect system1",
        "info": "",
        "unit": "",
        "min": "0",
        "max": "1",
        "data": 0,
        "raw_data": 0,
    }
)

# Writable with value map -> select.
OPERATIONAL_MODE_PAYLOAD = json.dumps(
    {
        "register": "47137",
        "factor": 1,
        "size": "u8",
        "mode": "R/W",
        "titel": "Operational mode",
        "info": "",
        "unit": "",
        "min": "0",
        "max": "2",
        "map": [{"0": "Auto"}, {"1": "Manual"}, {"2": "Add. heat only"}],
        "data": "Auto",
        "raw_data": 0,
    }
)

# Writable, factor 100, max exactly 4.35 -> the max cannot be encoded exactly.
FLOW_LIMIT_PAYLOAD = json.dumps(
    {
        "register": "47500",
        "factor": 100,
        "size": "s16",
        "mode": "R/W",
        "titel": "Flow limit",
        "info": "",
        "unit": "",
        "min": "0",
        "max": "435",
        "data": 1.0,
        "raw_data": 100,
    }
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom_components in every test."""
    return


@pytest.fixture(autouse=True)
def cancel_mqtt_misc_timer(request: pytest.FixtureRequest) -> Generator[None]:
    """Cancel only HA's MQTT misc timer after tests that use the MQTT mock.

    The mocked paho client never closes a socket, so HA's MQTT client keeps its
    1 s misc timer scheduled. Cancelling exactly that timer keeps the
    lingering-timer check active for everything the integration schedules.
    """
    if "mqtt_mock" not in request.fixturenames:
        yield
        return
    hass: HomeAssistant = request.getfixturevalue("hass")
    yield
    if (mqtt_data := hass.data.get(DATA_MQTT)) and (
        timer := mqtt_data.client._misc_timer
    ):
        timer.cancel()
