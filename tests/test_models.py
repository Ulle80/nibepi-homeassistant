"""Tests for the pure-Python register model."""

from __future__ import annotations

import pytest

from custom_components.nibepi.models import InvalidRegisterPayloadError, NibeRegister

from .conftest import OUTDOOR_TEMP_PAYLOAD, PRICE_LEVEL_PAYLOAD


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
    """A register with a value map is an enum and writable."""
    reg = NibeRegister.from_payload(PRICE_LEVEL_PAYLOAD)
    assert reg.is_enum
    assert reg.writable
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
