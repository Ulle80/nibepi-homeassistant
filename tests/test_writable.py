"""Writable registers: number, select and switch entities."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from unittest.mock import patch

from homeassistant.const import ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.nibepi.const import CONF_BASE_TOPIC, CONF_LWT_TOPIC, DOMAIN

from .conftest import (
    ADJUST_AFFECT_PAYLOAD,
    FLOW_LIMIT_PAYLOAD,
    OPERATIONAL_MODE_PAYLOAD,
    ROOM_SETPOINT_PAYLOAD,
)

NUMBER_ID = "number.nibepi_room_sensor_setpoint_s1"
SWITCH_ID = "switch.nibepi_adjust_affect_system1"
SELECT_ID = "select.nibepi_operational_mode"


def assert_published(mqtt_mock: MqttMockHAClient, topic: str, payload: str) -> None:
    """Assert exactly one publish of payload on topic (ignores extra kwargs)."""
    mqtt_mock.async_publish.assert_called_once()
    assert mqtt_mock.async_publish.call_args.args[:2] == (topic, payload)


@pytest.fixture
def enable_test_registers() -> Generator[None]:
    """Treat the test registers as comfort settings so they are enabled."""
    with patch(
        "custom_components.nibepi.entity.COMFORT_REGISTERS",
        frozenset({"47398", "40881", "47137", "47500"}),
    ):
        yield


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_only_comfort_settings_enabled_by_default(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    entity_registry: er.EntityRegistry,
) -> None:
    """Writable registers start disabled unless they are comfort settings."""
    entry = await _setup_entry(hass)
    async_fire_mqtt_message(hass, "nibe/modbus/47398/json", ROOM_SETPOINT_PAYLOAD)
    async_fire_mqtt_message(hass, "nibe/modbus/40881/json", ADJUST_AFFECT_PAYLOAD)
    await hass.async_block_till_done()

    setpoint = entity_registry.async_get(NUMBER_ID)
    assert setpoint.disabled_by is None
    assert hass.states.get(NUMBER_ID).state == "21.5"
    adjust = entity_registry.async_get(SWITCH_ID)
    assert adjust.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(SWITCH_ID) is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
async def setup_writable(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, enable_test_registers: None
) -> AsyncGenerator[None]:
    """Set up NibePi and announce the three writable registers."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="nibe/modbus/",
        data={CONF_BASE_TOPIC: "nibe/modbus/", CONF_LWT_TOPIC: "nibe"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for register, payload in (
        ("47398", ROOM_SETPOINT_PAYLOAD),
        ("40881", ADJUST_AFFECT_PAYLOAD),
        ("47137", OPERATIONAL_MODE_PAYLOAD),
    ):
        async_fire_mqtt_message(hass, f"nibe/modbus/{register}/json", payload)
    await hass.async_block_till_done()
    mqtt_mock.async_publish.reset_mock()
    yield
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("setup_writable")
async def test_entities_created(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Writable registers become config entities, not sensors."""
    number = hass.states.get(NUMBER_ID)
    assert number is not None
    assert number.state == "21.5"
    assert number.attributes["min"] == 5.0
    assert number.attributes["max"] == 35.0
    assert number.attributes["step"] == 0.1
    assert number.attributes["unit_of_measurement"] == "°C"

    assert hass.states.get(SWITCH_ID).state == "off"

    select = hass.states.get(SELECT_ID)
    assert select.state == "Auto"
    assert select.attributes["options"] == ["Auto", "Manual", "Add. heat only"]

    for entity_id in (NUMBER_ID, SWITCH_ID, SELECT_ID):
        assert entity_registry.async_get(entity_id).entity_category is (
            EntityCategory.CONFIG
        )
    # No duplicate read-only sensor for writable registers.
    assert hass.states.get("sensor.nibepi_room_sensor_setpoint_s1") is None


@pytest.mark.usefixtures("setup_writable")
async def test_number_writes_encoded_value(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Setting a number publishes the display value to <base><reg>/set."""
    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: NUMBER_ID, "value": 22.5},
        blocking=True,
    )
    assert_published(mqtt_mock, "nibe/modbus/47398/set", "22.5")


@pytest.mark.usefixtures("setup_writable")
async def test_switch_writes_numbers(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Switches write 1/0, never 'on'/'off'."""
    await hass.services.async_call(
        "switch", "turn_on", {ATTR_ENTITY_ID: SWITCH_ID}, blocking=True
    )
    assert_published(mqtt_mock, "nibe/modbus/40881/set", "1")
    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        "switch", "turn_off", {ATTR_ENTITY_ID: SWITCH_ID}, blocking=True
    )
    assert_published(mqtt_mock, "nibe/modbus/40881/set", "0")


@pytest.mark.usefixtures("setup_writable")
async def test_select_writes_key(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """Selecting a label writes its numeric key."""
    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: SELECT_ID, "option": "Manual"},
        blocking=True,
    )
    assert_published(mqtt_mock, "nibe/modbus/47137/set", "1")


@pytest.mark.usefixtures("setup_writable")
async def test_state_follows_readback(hass: HomeAssistant) -> None:
    """After a write NibePi re-publishes the register; the entity follows."""
    async_fire_mqtt_message(
        hass,
        "nibe/modbus/40881/json",
        ADJUST_AFFECT_PAYLOAD.replace('"data": 0', '"data": 1'),
    )
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH_ID).state == "on"


@pytest.mark.usefixtures("setup_writable")
async def test_unencodable_value_is_refused(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient
) -> None:
    """A value NibePi cannot store exactly is refused, nothing is published."""
    async_fire_mqtt_message(hass, "nibe/modbus/47500/json", FLOW_LIMIT_PAYLOAD)
    await hass.async_block_till_done()
    mqtt_mock.async_publish.reset_mock()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            "number",
            "set_value",
            {ATTR_ENTITY_ID: "number.nibepi_flow_limit", "value": 4.35},
            blocking=True,
        )
    assert exc_info.value.translation_key == "value_not_writable"
    mqtt_mock.async_publish.assert_not_called()

    # One step below the limit is fine.
    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: "number.nibepi_flow_limit", "value": 4.34},
        blocking=True,
    )
    assert_published(mqtt_mock, "nibe/modbus/47500/set", "4.34")
