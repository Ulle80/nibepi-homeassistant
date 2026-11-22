"""MQTT hub for NibePi: subscribes to topics and dispatches register updates."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    LWT_DISCONNECTED_SUFFIX,
    SIGNAL_AVAILABILITY,
    SIGNAL_NEW_REGISTER,
    SIGNAL_REGISTER_UPDATE,
    TOPIC_SUFFIX_JSON,
    TOPIC_SUFFIX_SET,
)
from .models import InvalidRegisterPayloadError, NibeRegister

_LOGGER = logging.getLogger(__name__)


class NibePiHub:
    """Keeps the known registers of one NibePi and talks MQTT."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, base_topic: str, lwt_topic: str
    ) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.entry_id = entry_id
        self.base_topic = base_topic
        self.lwt_topic = lwt_topic
        self.registers: dict[str, NibeRegister] = {}
        self.available = True
        self._unsubscribers: list[Callable[[], None]] = []

    async def async_start(self) -> None:
        """Subscribe to the NibePi topics."""
        self._unsubscribers.append(
            await mqtt.async_subscribe(
                self.hass,
                f"{self.base_topic}+{TOPIC_SUFFIX_JSON}",
                self._handle_register_message,
            )
        )
        if self.lwt_topic:
            self._unsubscribers.append(
                await mqtt.async_subscribe(
                    self.hass, self.lwt_topic, self._handle_lwt_message
                )
            )

    @callback
    def async_stop(self) -> None:
        """Unsubscribe from all topics."""
        while self._unsubscribers:
            self._unsubscribers.pop()()

    @callback
    def _handle_register_message(self, msg: mqtt.ReceiveMessage) -> None:
        try:
            register = NibeRegister.from_payload(msg.payload)
        except InvalidRegisterPayloadError as err:
            _LOGGER.debug("Ignoring payload on %s: %s", msg.topic, err)
            return

        self._set_available(True)
        if (known := self.registers.get(register.register)) is None:
            self.registers[register.register] = register
            async_dispatcher_send(
                self.hass,
                SIGNAL_NEW_REGISTER.format(entry_id=self.entry_id),
                register,
            )
            return

        known.update_from(register)
        async_dispatcher_send(
            self.hass,
            SIGNAL_REGISTER_UPDATE.format(
                entry_id=self.entry_id, register=register.register
            ),
        )

    @callback
    def _handle_lwt_message(self, msg: mqtt.ReceiveMessage) -> None:
        payload = str(msg.payload).strip()
        if payload.endswith(LWT_DISCONNECTED_SUFFIX):
            self._set_available(False)

    @callback
    def _set_available(self, available: bool) -> None:
        if self.available == available:
            return
        self.available = available
        async_dispatcher_send(
            self.hass, SIGNAL_AVAILABILITY.format(entry_id=self.entry_id)
        )

    async def async_write(self, register: str, value: float | int | str) -> None:
        """Write a value (in display units) to a register."""
        await mqtt.async_publish(
            self.hass, f"{self.base_topic}{register}{TOPIC_SUFFIX_SET}", str(value)
        )
