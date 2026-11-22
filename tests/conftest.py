"""Fixtures for NibePi tests."""

from __future__ import annotations

import json

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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    return
