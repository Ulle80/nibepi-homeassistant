"""Config flow for NibePi."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo
import voluptuous as vol

from .const import (
    CONF_BASE_TOPIC,
    CONF_LWT_TOPIC,
    DEFAULT_BASE_TOPIC,
    DEFAULT_LWT_TOPIC,
    DOMAIN,
    TOPIC_SUFFIX_JSON,
)


def _normalize_base_topic(topic: str) -> str:
    topic = topic.strip()
    return topic if topic.endswith("/") else f"{topic}/"


class NibePiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NibePi."""

    VERSION = 1

    _discovered_base_topic: str | None = None

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery via a NibePi register topic (<base>/<reg>/json)."""
        topic = discovery_info.topic
        if not topic.endswith(TOPIC_SUFFIX_JSON):
            return self.async_abort(reason="invalid_discovery_info")
        # Strip "<register>/json" to get the base topic.
        base = topic[: -len(TOPIC_SUFFIX_JSON)].rsplit("/", 1)[0] + "/"

        await self.async_set_unique_id(base)
        self._abort_if_unique_id_configured()
        self._discovered_base_topic = base
        self.context["title_placeholders"] = {"base_topic": base}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered NibePi."""
        assert self._discovered_base_topic is not None
        if user_input is not None:
            return self.async_create_entry(
                title="NibePi",
                data={
                    CONF_BASE_TOPIC: self._discovered_base_topic,
                    CONF_LWT_TOPIC: DEFAULT_LWT_TOPIC,
                },
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"base_topic": self._discovered_base_topic},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            base = _normalize_base_topic(user_input[CONF_BASE_TOPIC])
            if base == "/" or "#" in base or "+" in base:
                errors[CONF_BASE_TOPIC] = "invalid_topic"
            else:
                await self.async_set_unique_id(base)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="NibePi",
                    data={
                        CONF_BASE_TOPIC: base,
                        CONF_LWT_TOPIC: user_input.get(CONF_LWT_TOPIC, "").strip(),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BASE_TOPIC, default=DEFAULT_BASE_TOPIC): str,
                    vol.Optional(CONF_LWT_TOPIC, default=DEFAULT_LWT_TOPIC): str,
                }
            ),
            errors=errors,
        )
