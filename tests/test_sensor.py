"""End-to-end test: MQTT message -> sensor entity."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.nibepi.const import CONF_BASE_TOPIC, CONF_LWT_TOPIC, DOMAIN

from .conftest import OUTDOOR_TEMP_PAYLOAD, PRICE_LEVEL_PAYLOAD


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
    assert price.state == "CHEAP"

    async_fire_mqtt_message(hass, "nibe", "nibe_1234abcd disconnected")
    await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.nibepi_bt1_outdoor_temperature").state == "unavailable"
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
