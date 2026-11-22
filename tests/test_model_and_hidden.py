"""Pump model on the device, and hiding sensors that are not connected."""

from __future__ import annotations

from datetime import timedelta
import json
from typing import Any

from homeassistant.config_entries import RELOAD_AFTER_UPDATE_DELAY
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.nibepi.const import (
    CONF_BASE_TOPIC,
    CONF_LANGUAGE,
    CONF_LWT_TOPIC,
    CONF_MODEL,
    DEFAULT_DEVICE_MODEL,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from custom_components.nibepi.diagnostics import async_get_config_entry_diagnostics
from custom_components.nibepi.models import NibeRegister

from .test_pump_models import F1145_LIVE

NOT_CONNECTED = -3276.8  # s16 minimum with factor 10
SUPPLY_S2 = "40007"
SUPPLY_S2_ID = "sensor.nibepi_supply_temp_40007"


def _payload(register: int | str, data: float, *, mode: str = "R") -> str:
    return json.dumps(
        {
            "register": str(register),
            "factor": 10,
            "size": "s16",
            "mode": mode,
            "titel": f"Supply temp {register}",
            "info": "",
            "unit": "°C",
            "min": "0",
            "max": "0",
            "data": data,
        }
    )


def _send(hass: HomeAssistant, register: int | str, data: float) -> None:
    async_fire_mqtt_message(
        hass, f"nibe/modbus/{register}/json", _payload(register, data)
    )


def _entry(options: dict[str, str] | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
        options=options or {},
    )


async def _setup(
    hass: HomeAssistant, options: dict[str, str] | None = None
) -> MockConfigEntry:
    entry = _entry(options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _device_model(hass: HomeAssistant, entry: MockConfigEntry) -> str | None:
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    return devices[0].model


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_model_detected_once_unambiguous(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """The device shows the model as soon as only one model file fits."""
    entry = await _setup(hass)
    for register in F1145_LIVE:
        _send(hass, register, 20.0)
    await hass.async_block_till_done()
    # F1145/F1245 and F1355 both still fit.
    assert entry.runtime_data.detected_model is None
    assert _device_model(hass, entry) == DEFAULT_DEVICE_MODEL

    _send(hass, 40074, 20.0)
    await hass.async_block_till_done()
    assert _device_model(hass, entry) == "F1145 / F1245"

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["model"] == {
        "configured": None,
        "detected": "F1145 / F1245",
        "candidates": ["F1145 / F1245"],
    }
    await _unload(hass, entry)


async def test_configured_model_wins(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """A model chosen in the options is shown instead of the detected one."""
    entry = await _setup(hass, {CONF_MODEL: "F1245"})
    for register in [*F1145_LIVE, 40074]:
        _send(hass, register, 20.0)
    await hass.async_block_till_done()
    assert entry.runtime_data.detected_model == "F1145 / F1245"
    assert _device_model(hass, entry) == "F1245"
    await _unload(hass, entry)


async def test_options_flow_sets_model(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """The model can be chosen next to the language; auto is the default."""
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"] == {"detected_model": "-"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_LANGUAGE: "auto", CONF_MODEL: "F1145"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.options == {CONF_LANGUAGE: "auto", CONF_MODEL: "F1145"}
    assert entry.runtime_data.configured_model == "F1145"
    await _unload(hass, entry)


async def test_new_sensor_not_connected_starts_disabled(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, hass_storage: dict[str, Any]
) -> None:
    """A sensor that is first seen as "not connected" is created disabled."""
    entry = await _setup(hass)
    _send(hass, SUPPLY_S2, NOT_CONNECTED)
    await hass.async_block_till_done()

    registry_entry = er.async_get(hass).async_get(SUPPLY_S2_ID)
    assert registry_entry is not None
    assert registry_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(SUPPLY_S2_ID) is None

    await _unload(hass, entry)
    stored = hass_storage[STORAGE_KEY.format(entry_id=entry.entry_id)]["data"]
    assert stored["hidden_not_connected"] == [SUPPLY_S2]
    assert stored["connected"] == []


async def test_existing_sensor_hidden_and_shown_again(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, hass_storage: dict[str, Any]
) -> None:
    """A restored sensor is disabled when not connected, enabled once it is."""
    entry = _entry()
    hass_storage[STORAGE_KEY.format(entry_id=entry.entry_id)] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": STORAGE_KEY.format(entry_id=entry.entry_id),
        "data": {
            "registers": [
                NibeRegister.from_payload(_payload(SUPPLY_S2, 0)).as_definition()
            ]
        },
    }
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    assert registry.async_get(SUPPLY_S2_ID).disabled_by is None
    assert hass.states.get(SUPPLY_S2_ID).state == STATE_UNAVAILABLE

    _send(hass, SUPPLY_S2, NOT_CONNECTED)
    await hass.async_block_till_done()
    assert (
        registry.async_get(SUPPLY_S2_ID).disabled_by
        is er.RegistryEntryDisabler.INTEGRATION
    )
    assert hass.states.get(SUPPLY_S2_ID) is None

    # Sensor installed later: it delivers values and comes back.
    _send(hass, SUPPLY_S2, 31.5)
    await hass.async_block_till_done()
    assert registry.async_get(SUPPLY_S2_ID).disabled_by is None
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=RELOAD_AFTER_UPDATE_DELAY + 1)
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.runtime_data.connected == {SUPPLY_S2}
    await _unload(hass, entry)


async def test_working_sensor_is_never_hidden(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """A sensor that delivered values once stays visible when it fails."""
    entry = await _setup(hass)
    _send(hass, SUPPLY_S2, 30.0)
    await hass.async_block_till_done()
    _send(hass, SUPPLY_S2, NOT_CONNECTED)
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get(SUPPLY_S2_ID).disabled_by is None
    assert hass.states.get(SUPPLY_S2_ID).state == STATE_UNAVAILABLE
    await _unload(hass, entry)


async def test_user_enabled_sensor_stays_enabled(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """A hidden sensor the user enables again is not hidden a second time."""
    entry = await _setup(hass)
    _send(hass, SUPPLY_S2, NOT_CONNECTED)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    registry.async_update_entity(SUPPLY_S2_ID, disabled_by=None)
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=RELOAD_AFTER_UPDATE_DELAY + 1)
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    _send(hass, SUPPLY_S2, NOT_CONNECTED)
    await hass.async_block_till_done()
    assert registry.async_get(SUPPLY_S2_ID).disabled_by is None
    assert hass.states.get(SUPPLY_S2_ID).state == STATE_UNAVAILABLE
    await _unload(hass, entry)


async def test_user_disabled_sensor_is_not_enabled(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Values arriving never re-enable a sensor the user disabled."""
    entry = await _setup(hass)
    _send(hass, SUPPLY_S2, NOT_CONNECTED)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    registry.async_update_entity(
        SUPPLY_S2_ID, disabled_by=er.RegistryEntryDisabler.USER
    )
    _send(hass, SUPPLY_S2, 30.0)
    await hass.async_block_till_done()
    assert registry.async_get(SUPPLY_S2_ID).disabled_by is er.RegistryEntryDisabler.USER
    await _unload(hass, entry)


async def test_writable_registers_are_not_hidden(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Only sensors are hidden; settings are never "not connected" sensors."""
    entry = await _setup(hass)
    async_fire_mqtt_message(
        hass, "nibe/modbus/47398/json", _payload(47398, NOT_CONNECTED, mode="R/W")
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.hidden_not_connected == set()
    await _unload(hass, entry)
