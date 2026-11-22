"""End-to-end test: MQTT message -> sensor entity."""

from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.nibepi.const import CONF_BASE_TOPIC, CONF_LWT_TOPIC, DOMAIN

from .conftest import OUTDOOR_TEMP_PAYLOAD, PRICE_LEVEL_PAYLOAD


async def test_real_world_registers(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    entity_registry: er.EntityRegistry,
) -> None:
    """Payloads modelled on a real F1145: counters, placeholders, info maps."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    base = {"factor": 1, "size": "u8", "mode": "R", "info": "", "unit": ""}
    payloads = {
        "43416": base
        | {"titel": "Compressor starts EB100-EP14", "size": "s32", "min": "0",
           "max": "9999999", "data": 42217},
        "40007": base
        | {"titel": "EP21-BT2 Supply temp S2", "factor": 10, "size": "s16",
           "unit": "°C", "data": -3276.8},
        "43086": base
        | {"titel": "Prio", "data": 30,
           "info": "10=Off 20=Hot Water 30=Heat 40=Pool 41=Pool 2 50=Transfer"},
    }  # fmt: skip
    for register, payload in payloads.items():
        async_fire_mqtt_message(
            hass,
            f"nibe/modbus/{register}/json",
            json.dumps(payload | {"register": register}),
        )
    await hass.async_block_till_done()

    starts = hass.states.get("sensor.nibepi_compressor_starts_eb100_ep14")
    assert starts.state == "42217.0"
    assert starts.attributes["state_class"] == "total_increasing"
    options = entity_registry.async_get(starts.entity_id).options
    assert options["sensor"]["suggested_display_precision"] == 0

    assert hass.states.get("sensor.nibepi_ep21_bt2_supply_temp_s2").state == (
        "unavailable"
    )
    prio = hass.states.get("sensor.nibepi_prio")
    assert prio.state == "Heat"
    assert prio.attributes["device_class"] == "enum"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_sensors_created_from_mqtt(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Registers announced via /json become sensors and follow LWT."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    async_fire_mqtt_message(hass, "nibe/modbus/40004/json", OUTDOOR_TEMP_PAYLOAD)
    async_fire_mqtt_message(hass, "nibe/modbus/41929/json", PRICE_LEVEL_PAYLOAD)
    await hass.async_block_till_done()

    temp = hass.states.get("sensor.nibepi_bt1_outdoor_temperature")
    assert temp is not None
    assert temp.state == "-3.5"
    assert temp.attributes["unit_of_measurement"] == "°C"

    price = hass.states.get("sensor.nibepi_price_level")
    assert price is not None
    assert price.state == "Cheap"  # translated to the HA language (en in tests)

    async_fire_mqtt_message(hass, "nibe", "nibe_1234abcd disconnected")
    await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.nibepi_bt1_outdoor_temperature").state == "unavailable"
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
