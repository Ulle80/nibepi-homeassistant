"""Tests for NibePi diagnostics."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
    MqttMockHAClient,
)

from custom_components.nibepi.const import (
    CONF_BASE_TOPIC,
    CONF_LWT_TOPIC,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from custom_components.nibepi.models import NibeRegister

from .conftest import OPERATIONAL_MODE_PAYLOAD, OUTDOOR_TEMP_PAYLOAD


@pytest.fixture(autouse=True)
def no_refresh_delay() -> Generator[None]:
    """Do not wait between /get requests in tests."""
    with patch("custom_components.nibepi.hub.REFRESH_REQUEST_DELAY", 0):
        yield


async def test_config_entry_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_storage: dict[str, Any],
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Diagnostics show config, availability and every known register."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
    )
    entry.add_to_hass(hass)
    # One register restored from storage that has not answered yet.
    key = STORAGE_KEY.format(entry_id=entry.entry_id)
    hass_storage[key] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": key,
        "data": {
            "registers": [
                NibeRegister.from_payload(OPERATIONAL_MODE_PAYLOAD).as_definition()
            ]
        },
    }
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"]["data"] == {
        CONF_BASE_TOPIC: "nibe/modbus/",
        CONF_LWT_TOPIC: "nibe",
    }
    assert diagnostics["hub"] == {
        "available": True,
        "hidden_not_connected": [],
        "register_count": 2,
        "registers_without_value": ["47137"],
    }
    temp = diagnostics["registers"]["40004"]
    assert temp["kind"] == "sensor"
    assert temp["title"] == "BT1 Outdoor Temperature"
    assert temp["value"] == -3.5
    assert temp["raw_value"] == -35
    mode = diagnostics["registers"]["47137"]
    assert mode["kind"] == "select"
    assert mode["mapping"] == {"0": "Auto", "1": "Manual", "2": "Add. heat only"}
    assert mode["value"] is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
