"""MQTT hub for NibePi: subscribes to topics and dispatches register updates."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
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
from .labels import DEFAULT_LANGUAGE
from .models import InvalidRegisterPayloadError, NibeRegister

_LOGGER = logging.getLogger(__name__)


@callback
def async_get_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Return the store holding the known register definitions of an entry."""
    return Store(hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry_id))


class NibePiHub:
    """Keeps the known registers of one NibePi and talks MQTT."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        base_topic: str,
        lwt_topic: str,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.entry_id = entry_id
        self.base_topic = base_topic
        self.lwt_topic = lwt_topic
        self.language = language
        self.registers: dict[str, NibeRegister] = {}
        self.available = True
        self._unsubscribers: list[Callable[[], None]] = []
        self._store = async_get_store(hass, entry_id)
        self._tasks: set[asyncio.Task[None]] = set()
        self._reload_scheduled = False

    async def async_start(self) -> None:
        """Restore known registers, subscribe, then request current values."""
        await self._async_restore_registers()
        await self.async_subscribe()
        if self.registers:
            self._start_task(
                self._async_request_values(list(self.registers)), "refresh"
            )

    async def async_subscribe(self) -> None:
        """Subscribe to the register and last-will topics."""
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
        """Stop receiving messages and cancel pending requests."""
        while self._unsubscribers:
            self._unsubscribers.pop()()
        while self._tasks:
            self._tasks.pop().cancel()

    async def async_save(self) -> None:
        """Persist the known register definitions now."""
        if self.registers:
            await self._store.async_save(self._data_to_store())

    @callback
    def _start_task(self, coro: Any, name: str) -> None:
        task = self.hass.async_create_background_task(
            coro, name=f"nibepi {name} {self.entry_id}"
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

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

    async def _async_request_values(
        self, registers: list[str], *, only_missing: bool = True
    ) -> None:
        """Ask NibePi to read registers; it answers on the normal topics.

        Requests are spaced out because each one becomes an RS485 read. A failed
        publish (e.g. broker flapping right after start) skips that register
        instead of aborting the whole run.
        """
        for address in registers:
            register = self.registers.get(address)
            if register is None or (only_missing and register.value is not None):
                continue
            try:
                await mqtt.async_publish(
                    self.hass, f"{self.base_topic}{address}{TOPIC_SUFFIX_GET}", ""
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Could not request register %s: %s", address, err)
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
        known = self.registers.get(register.register)
        if known is None:
            self.registers[register.register] = register
            self._store.async_delay_save(self._data_to_store, STORAGE_SAVE_DELAY)
            async_dispatcher_send(
                self.hass,
                SIGNAL_NEW_REGISTER.format(entry_id=self.entry_id),
                register,
            )
            return

        if known.as_definition() != register.as_definition():
            # Metadata changed (e.g. other pump model / NibePi update). Entities
            # derive limits, units and type from it, so rebuild them once.
            _LOGGER.info("Definition of register %s changed", register.register)
            if known.kind is not register.kind:
                self._remove_entity(known)
            self.registers[register.register] = register
            self._store.async_delay_save(self._data_to_store, STORAGE_SAVE_DELAY)
            if not self._reload_scheduled:
                self._reload_scheduled = True
                self.hass.config_entries.async_schedule_reload(self.entry_id)
            return

        known.update_from(register)
        async_dispatcher_send(
            self.hass,
            SIGNAL_REGISTER_UPDATE.format(
                entry_id=self.entry_id, register=register.register
            ),
        )

    @callback
    def _remove_entity(self, register: NibeRegister) -> None:
        """Drop the entity of a register whose type changed (e.g. number->select).

        The replacement lives in another domain with the same unique ID, so the
        old registry entry would otherwise stay behind as unavailable.
        """
        registry = er.async_get(self.hass)
        if entity_id := registry.async_get_entity_id(
            register.kind.value, DOMAIN, f"{self.entry_id}_{register.register}"
        ):
            _LOGGER.info("Removing %s, register type changed", entity_id)
            registry.async_remove(entity_id)

    @callback
    def _handle_lwt_message(self, msg: mqtt.ReceiveMessage) -> None:
        payload = str(msg.payload).strip()
        if not payload.endswith(LWT_DISCONNECTED_SUFFIX):
            return
        self._set_available(False)
        # NibePi's last-will topic is hardcoded and shared by every NibePi on the
        # broker, so the will may belong to another device. Probe ours: if it
        # is alive it answers and becomes available again right away.
        if probe := next(iter(self.registers), None):
            self._start_task(
                self._async_request_values([probe], only_missing=False), "probe"
            )

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
