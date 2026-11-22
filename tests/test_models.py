"""Tests for the pure-Python register model."""

from __future__ import annotations

import pytest

from custom_components.nibepi.models import (
    InvalidRegisterPayloadError,
    NibeRegister,
    RegisterKind,
)

from .conftest import (
    ADJUST_AFFECT_PAYLOAD,
    OPERATIONAL_MODE_PAYLOAD,
    OUTDOOR_TEMP_PAYLOAD,
    PRICE_LEVEL_PAYLOAD,
    ROOM_SETPOINT_PAYLOAD,
)


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        (OUTDOOR_TEMP_PAYLOAD, RegisterKind.SENSOR),
        (PRICE_LEVEL_PAYLOAD, RegisterKind.SENSOR),
        (ROOM_SETPOINT_PAYLOAD, RegisterKind.NUMBER),
        (ADJUST_AFFECT_PAYLOAD, RegisterKind.SWITCH),
        (OPERATIONAL_MODE_PAYLOAD, RegisterKind.SELECT),
    ],
)
def test_kind(payload: str, kind: RegisterKind) -> None:
    """Registers map to the right entity type."""
    assert NibeRegister.from_payload(payload).kind is kind


def test_number_limits_and_step() -> None:
    """Limits are scaled; step follows the factor."""
    reg = NibeRegister.from_payload(ROOM_SETPOINT_PAYLOAD)
    assert reg.limits == (5.0, 35.0)
    assert reg.step == 0.1


def test_limits_fall_back_to_size() -> None:
    """Without min/max (0/0) the register size defines the range."""
    reg = NibeRegister(register="1", title="x", factor=10, size="s16")
    assert reg.limits == (-3276.8, 3276.7)


@pytest.mark.parametrize(
    ("factor", "value", "expected_raw"),
    [
        (1, 3, 3),
        (10, 21.5, 215),
        (10, -3.3, -33),
        (100, 4.35, 435),  # 4.35 * 100 == 434.99999999999994 in IEEE 754
        (100, -4.35, -435),
        (10, 0, 0),
    ],
)
def test_encode_value_survives_truncation(
    factor: int, value: float, expected_raw: int
) -> None:
    """NibePi truncates payload*factor; the encoded payload must still hit raw."""
    reg = NibeRegister(register="1", title="x", factor=factor)
    payload = reg.encode_value(value)
    # Emulate NibePi: JS Number(payload) * factor, then int32 truncation.
    assert int(float(payload) * factor) == expected_raw


def test_definition_roundtrip() -> None:
    """Stored definitions recreate the register without its runtime value."""
    original = NibeRegister.from_payload(OPERATIONAL_MODE_PAYLOAD)
    restored = NibeRegister.from_definition(original.as_definition())
    assert restored.kind is RegisterKind.SELECT
    assert restored.mapping == original.mapping
    assert restored.limits == original.limits
    assert restored.value is None


@pytest.mark.parametrize("definition", [None, [], {"title": "no register"}])
def test_invalid_definition(definition: object) -> None:
    """Broken stored data is rejected."""
    with pytest.raises(InvalidRegisterPayloadError):
        NibeRegister.from_definition(definition)  # type: ignore[arg-type]


def test_key_for_label() -> None:
    """Labels translate back to the numeric key NibePi expects."""
    reg = NibeRegister.from_payload(OPERATIONAL_MODE_PAYLOAD)
    assert reg.key_for_label("Manual") == "1"
    with pytest.raises(ValueError, match="Unknown option"):
        reg.key_for_label("Turbo")


def test_parse_temperature() -> None:
    """A scaled read-only temperature register parses correctly."""
    reg = NibeRegister.from_payload(OUTDOOR_TEMP_PAYLOAD)
    assert reg.register == "40004"
    assert reg.title == "BT1 Outdoor Temperature"
    assert reg.unit == "°C"
    assert reg.value == -3.5
    assert reg.raw_value == -35
    assert not reg.writable
    assert not reg.is_enum
    assert reg.scaled_min == -50
    assert reg.scaled_max == 50


def test_parse_mapped_register() -> None:
    """A read-only register with a value map is an enum sensor."""
    reg = NibeRegister.from_payload(PRICE_LEVEL_PAYLOAD)
    assert reg.is_enum
    assert not reg.writable
    assert reg.kind is RegisterKind.SENSOR
    assert reg.mapping == {
        "0": "UNKNOWN",
        "1": "CHEAP",
        "2": "NORMAL",
        "3": "EXPENSIVE",
    }
    assert reg.value == "CHEAP"


@pytest.mark.parametrize("payload", ["not json", "[]", '{"data": 1}'])
def test_invalid_payload(payload: str) -> None:
    """Garbage is rejected."""
    with pytest.raises(InvalidRegisterPayloadError):
        NibeRegister.from_payload(payload)
