"""Restart behaviour: NibePi does not retain, so registers are stored and polled."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.nibepi.const import (
    CONF_BASE_TOPIC,
    CONF_LWT_TOPIC,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from custom_components.nibepi.models import NibeRegister

from .conftest import OUTDOOR_TEMP_PAYLOAD, ROOM_SETPOINT_PAYLOAD

TEMP_ID = "sensor.nibepi_bt1_outdoor_temperature"
SETPOINT_ID = "number.nibepi_room_sensor_setpoint_s1"


@pytest.fixture(autouse=True)
def no_refresh_delay():
    """Do not wait between /get requests in tests."""
    with patch("custom_components.nibepi.hub.REFRESH_REQUEST_DELAY", 0):
        yield


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a NibePi config entry added to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
    )
    entry.add_to_hass(hass)
    return entry


def _get_requests(mqtt_mock: MqttMockHAClient) -> list[str]:
    return [
        call.args[0]
        for call in mqtt_mock.async_publish.call_args_list
        if call.args[0].endswith("/get")
    ]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_restored_registers_are_requested(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    hass_storage: dict[str, Any],
    entry: MockConfigEntry,
) -> None:
    """Stored registers come back as entities and their values are requested."""
    hass_storage[STORAGE_KEY.format(entry_id=entry.entry_id)] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": STORAGE_KEY.format(entry_id=entry.entry_id),
        "data": {
            "registers": [
                NibeRegister.from_payload(OUTDOOR_TEMP_PAYLOAD).as_definition(),
                NibeRegister.from_payload(ROOM_SETPOINT_PAYLOAD).as_definition(),
                {"garbage": True},
            ]
        },
    }

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Entities exist right away, but without a value they are unavailable.
    assert hass.states.get(TEMP_ID).state == "unavailable"
    assert hass.states.get(SETPOINT_ID).state == "unavailable"
    assert sorted(_get_requests(mqtt_mock)) == [
        "nibe/modbus/40004/get",
        "nibe/modbus/47398/get",
    ]

    # NibePi answers the /get with the regular publish.
    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    await hass.async_block_till_done()
    assert hass.states.get(TEMP_ID).state == "-3.5"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_registers_survive_reload(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    hass_storage: dict[str, Any],
    entry: MockConfigEntry,
) -> None:
    """Registers seen once are persisted on unload and restored on next setup."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert _get_requests(mqtt_mock) == []  # nothing known yet, nothing to ask

    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    stored = hass_storage[STORAGE_KEY.format(entry_id=entry.entry_id)]["data"]
    assert [r["register"] for r in stored["registers"]] == ["40004"]
    assert "value" not in stored["registers"][0]  # no stale runtime values

    mqtt_mock.async_publish.reset_mock()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(TEMP_ID).state == "unavailable"
    assert _get_requests(mqtt_mock) == ["nibe/modbus/40004/get"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_remove_entry_deletes_store(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    hass_storage: dict[str, Any],
    entry: MockConfigEntry,
) -> None:
    """Removing the integration also removes its stored registers."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert STORAGE_KEY.format(entry_id=entry.entry_id) not in hass_storage
