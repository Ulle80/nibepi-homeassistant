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
        "mode": "R/W",
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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    return
