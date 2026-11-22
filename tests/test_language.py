"""Label language: options flow and translated entity states."""

from __future__ import annotations

from collections.abc import Generator
import json
from unittest.mock import patch

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.nibepi.const import (
    CONF_BASE_TOPIC,
    CONF_LANGUAGE,
    CONF_LWT_TOPIC,
    DOMAIN,
)

# RMU40 register with Swedish labels, as published by NibePi.
TEMPORARY_LUX = {
    "register": "10020",
    "factor": 1,
    "size": "u8",
    "mode": "R/W",
    "titel": "Temporary Lux",
    "info": "",
    "unit": "",
    "min": "0",
    "max": "4",
    "map": [{"0": "Från"}, {"1": "3h"}, {"2": "6h"}, {"3": "12h"},
            {"4": "Engångshöjning"}],
    "data": "Från",
}  # fmt: skip
ALARM = {
    "register": "10001",
    "factor": 1,
    "size": "u8",
    "mode": "R",
    "titel": "A-larm",
    "info": "",
    "unit": "",
    "map": [{"0": "Inga larm"}, {"184": "Filterlarm"}],
    "data": "Inga larm",
}
SELECT_ID = "select.nibepi_temporary_lux"
ALARM_ID = "sensor.nibepi_a_larm"


@pytest.fixture(autouse=True)
def enable_temporary_lux() -> Generator[None]:
    """10020 is a comfort register anyway; keep the test independent of that."""
    with patch(
        "custom_components.nibepi.entity.COMFORT_REGISTERS", frozenset({"10020"})
    ):
        yield


async def _setup(hass: HomeAssistant, options: dict[str, str]) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
        options=options,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for payload in (TEMPORARY_LUX, ALARM):
        async_fire_mqtt_message(
            hass, f"nibe/modbus/{payload['register']}/json", json.dumps(payload)
        )
    await hass.async_block_till_done()
    return entry


async def test_german_labels_and_write_back(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Swedish labels show in German; choosing one writes NibePi's key."""
    entry = await _setup(hass, {CONF_LANGUAGE: "de"})

    select = hass.states.get(SELECT_ID)
    assert select.state == "Aus"
    assert select.attributes["options"] == [
        "Aus", "3h", "6h", "12h", "Einmalige Erhöhung",
    ]  # fmt: skip
    assert hass.states.get(ALARM_ID).state == "Kein Alarm"

    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: SELECT_ID, "option": "Einmalige Erhöhung"},
        blocking=True,
    )
    assert mqtt_mock.async_publish.call_args.args[:2] == ("nibe/modbus/10020/set", "4")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_auto_falls_back_to_norwegian(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """With an unsupported HA language, labels default to Norwegian."""
    hass.config.language = "fr"
    entry = await _setup(hass, {})
    assert hass.states.get(SELECT_ID).state == "Av"
    assert hass.states.get(ALARM_ID).state == "Ingen alarm"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_options_flow_changes_language(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Choosing a language in the options reloads with translated labels."""
    entry = await _setup(hass, {CONF_LANGUAGE: "de"})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_LANGUAGE: "da"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.options == {CONF_LANGUAGE: "da"}

    # After the reload NibePi publishes again; labels are now Danish.
    for payload in (TEMPORARY_LUX, ALARM):
        async_fire_mqtt_message(
            hass, f"nibe/modbus/{payload['register']}/json", json.dumps(payload)
        )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SELECT_ID).state == "Fra"
    assert hass.states.get(ALARM_ID).state == "Ingen alarm"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
