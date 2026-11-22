"""Tests for the NibePi config flow."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_MQTT, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from custom_components.nibepi.const import CONF_BASE_TOPIC, CONF_LWT_TOPIC, DOMAIN

from .conftest import OUTDOOR_TEMP_PAYLOAD


async def test_user_flow(hass: HomeAssistant) -> None:
    """Manual setup creates an entry and normalizes the topic."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_BASE_TOPIC: "heatpump", CONF_LWT_TOPIC: "nibe"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_BASE_TOPIC: "heatpump/", CONF_LWT_TOPIC: "nibe"}


async def test_user_flow_rejects_wildcards(hass: HomeAssistant) -> None:
    """Wildcards in the base topic are rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_BASE_TOPIC: "nibe/#", CONF_LWT_TOPIC: "nibe"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE_TOPIC: "invalid_topic"}


async def test_mqtt_discovery_invalid_topic(hass: HomeAssistant) -> None:
    """Discovery on a topic that is not a /json register topic aborts."""
    info = MqttServiceInfo(
        topic="nibe/modbus/40004",
        payload="-3.5",
        qos=0,
        retain=False,
        subscribed_topic="nibe/modbus/+/json",
        timestamp=None,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_MQTT}, data=info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_discovery_info"


async def test_mqtt_discovery(hass: HomeAssistant) -> None:
    """Discovery derives the base topic from a register topic."""
    info = MqttServiceInfo(
        topic="nibe/modbus/40004/json",
        payload=OUTDOOR_TEMP_PAYLOAD,
        qos=0,
        retain=False,
        subscribed_topic="nibe/modbus/+/json",
        timestamp=None,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_MQTT}, data=info
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BASE_TOPIC] == "nibe/modbus/"
