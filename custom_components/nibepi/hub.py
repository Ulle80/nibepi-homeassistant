"""MQTT hub for NibePi: subscribes to topics and dispatches register updates."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    LWT_DISCONNECTED_SUFFIX,
    REFRESH_REQUEST_DELAY,
    SIGNAL_AVAILABILITY,
    SIGNAL_NEW_REGISTER,
    SIGNAL_REGISTER_UPDATE,
    STORAGE_KEY,
    STORAGE_SAVE_DELAY,
    STORAGE_VERSION,
    TOPIC_SUFFIX_GET,
    TOPIC_SUFFIX_JSON,
    TOPIC_SUFFIX_SET,
)
from .models import InvalidRegisterPayloadError, NibeRegister

_LOGGER = logging.getLogger(__name__)


@callback
def async_get_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Return the store holding the known register definitions of an entry."""
    return Store(hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry_id))


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
        self._store = async_get_store(hass, entry_id)
        self._refresh_task: asyncio.Task[None] | None = None

    async def async_start(self) -> None:
        """Restore known registers, subscribe, then request current values."""
        await self._async_restore_registers()
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
        if self.registers:
            self._refresh_task = self.hass.async_create_background_task(
                self._async_request_missing_values(list(self.registers)),
                name=f"nibepi refresh {self.entry_id}",
            )

    async def async_shutdown(self) -> None:
        """Unsubscribe, stop requesting values and persist known registers."""
        while self._unsubscribers:
            self._unsubscribers.pop()()
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            self._refresh_task = None
        if self.registers:
            await self._store.async_save(self._data_to_store())

    async def _async_restore_registers(self) -> None:
        """Recreate entities for registers seen before the last restart."""
        data = await self._store.async_load() or {}
        for definition in data.get("registers", []):
            try:
                register = NibeRegister.from_definition(definition)
            except (InvalidRegisterPayloadError, TypeError) as err:
                _LOGGER.debug("Skipping stored register %s: %s", definition, err)
                continue
            self.registers[register.register] = register
            async_dispatcher_send(
                self.hass,
                SIGNAL_NEW_REGISTER.format(entry_id=self.entry_id),
                register,
            )
        _LOGGER.debug("Restored %s registers", len(self.registers))

    async def _async_request_missing_values(self, registers: list[str]) -> None:
        """Ask NibePi for every restored register that has no value yet.

        NibePi reads the register and publishes it on the normal topics.
        Requests are spaced out because each one becomes an RS485 read.
        """
        for address in registers:
            register = self.registers.get(address)
            if register is None or register.value is not None:
                continue
            await mqtt.async_publish(
                self.hass, f"{self.base_topic}{address}{TOPIC_SUFFIX_GET}", ""
            )
            await asyncio.sleep(REFRESH_REQUEST_DELAY)

    @callback
    def _data_to_store(self) -> dict[str, Any]:
        return {
            "registers": [
                register.as_definition() for register in self.registers.values()
            ]
        }

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
            self._store.async_delay_save(self._data_to_store, STORAGE_SAVE_DELAY)
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

    async def async_write(self, register: str, payload: str) -> None:
        """Send an already encoded value to a register.

        NibePi gives no feedback on MQTT; on success it reads the register back
        and publishes the new value, which updates the entity.
        """
        await mqtt.async_publish(
            self.hass, f"{self.base_topic}{register}{TOPIC_SUFFIX_SET}", payload
        )
