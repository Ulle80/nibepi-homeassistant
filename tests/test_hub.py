"""Hub behaviour: metadata changes, LWT probing, failures, setup and unload."""

from __future__ import annotations

from collections.abc import Generator
import json
import logging
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
def no_refresh_delay() -> Generator[None]:
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


def _published_topics(mqtt_mock: MqttMockHAClient) -> list[str]:
    return [call.args[0] for call in mqtt_mock.async_publish.call_args_list]


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_changed_definition_rebuilds_entities(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, entry: MockConfigEntry
) -> None:
    """New metadata for a known register replaces the stale definition."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    async_fire_mqtt_message(hass, "nibe/modbus/47398/json", ROOM_SETPOINT_PAYLOAD)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SETPOINT_ID).attributes["max"] == 35.0

    changed = json.loads(ROOM_SETPOINT_PAYLOAD) | {"max": "300"}
    async_fire_mqtt_message(hass, "nibe/modbus/47398/json", json.dumps(changed))
    await hass.async_block_till_done(wait_background_tasks=True)

    # The entry reloaded with the new definition; the entity has the new limit.
    assert entry.state is ConfigEntryState.LOADED
    async_fire_mqtt_message(hass, "nibe/modbus/47398/json", json.dumps(changed))
    await hass.async_block_till_done(wait_background_tasks=True)
    state = hass.states.get(SETPOINT_ID)
    assert state.attributes["max"] == 30.0
    assert state.state == "21.5"
    await _unload(hass, entry)


async def test_lwt_probes_own_device(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, entry: MockConfigEntry
) -> None:
    """A last will (possibly from another NibePi) triggers a probe of ours."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    await hass.async_block_till_done(wait_background_tasks=True)
    mqtt_mock.async_publish.reset_mock()

    async_fire_mqtt_message(hass, "nibe", "nibe_ab12cd34 disconnected")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(TEMP_ID).state == "unavailable"
    assert _published_topics(mqtt_mock) == ["nibe/modbus/40004/get"]

    # Our NibePi is alive and answers the probe.
    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(TEMP_ID).state == "-3.5"

    # Unrelated payloads on the LWT topic are ignored.
    async_fire_mqtt_message(hass, "nibe", "hello")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(TEMP_ID).state == "-3.5"
    await _unload(hass, entry)


async def test_refresh_survives_publish_errors(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    hass_storage: dict[str, Any],
    entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failing /get does not stop requests for the remaining registers."""
    key = STORAGE_KEY.format(entry_id=entry.entry_id)
    hass_storage[key] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": key,
        "data": {
            "registers": [
                NibeRegister.from_payload(OUTDOOR_TEMP_PAYLOAD).as_definition(),
                NibeRegister.from_payload(ROOM_SETPOINT_PAYLOAD).as_definition(),
            ]
        },
    }
    publish = AsyncMock(side_effect=[HomeAssistantError("broker gone"), None])
    with (
        patch("custom_components.nibepi.hub.mqtt.async_publish", publish),
        caplog.at_level(logging.WARNING),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert [call.args[1] for call in publish.call_args_list] == [
        "nibe/modbus/40004/get",
        "nibe/modbus/47398/get",
    ]
    assert "Could not request register 40004" in caplog.text
    await _unload(hass, entry)


async def test_setup_failure_rolls_back_platforms(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, entry: MockConfigEntry
) -> None:
    """If the hub cannot start, platforms are unloaded and setup is retried."""
    with patch(
        "custom_components.nibepi.hub.mqtt.async_subscribe",
        side_effect=HomeAssistantError("not connected"),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.SETUP_RETRY

    # A clean retry works (would fail with "already set up" without rollback).
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    await _unload(hass, entry)


async def test_unload_stops_messages_before_platforms(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, entry: MockConfigEntry
) -> None:
    """MQTT is unsubscribed before platforms unload, so nothing races in."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    hub = entry.runtime_data
    original = hass.config_entries.async_unload_platforms
    subscribed_during_unload: list[bool] = []

    async def _unload_platforms(*args: Any, **kwargs: Any) -> bool:
        subscribed_during_unload.append(bool(hub._unsubscribers))
        return await original(*args, **kwargs)

    with patch.object(hass.config_entries, "async_unload_platforms", _unload_platforms):
        await _unload(hass, entry)
    assert subscribed_during_unload == [False]


async def test_failed_platform_unload_resubscribes(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, entry: MockConfigEntry
) -> None:
    """If platforms refuse to unload, the hub keeps listening."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    hub = entry.runtime_data
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert not await hass.config_entries.async_unload(entry.entry_id)
    assert hub._unsubscribers
    entry.mock_state(hass, ConfigEntryState.LOADED)
    await _unload(hass, entry)
