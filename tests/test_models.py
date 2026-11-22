"""Tests for the pure-Python register model."""

from __future__ import annotations

import json

import pytest

from custom_components.nibepi.models import (
    InvalidRegisterPayloadError,
    NibeRegister,
    RegisterKind,
    UnencodableValueError,
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


def test_encode_value_stays_within_range() -> None:
    """Near a limit the payload must not overshoot max (NibePi drops it)."""
    reg = NibeRegister(register="1", title="x", factor=100, min=0, max=1000)
    payload = reg.encode_value(4.35)
    product = float(payload) * 100
    assert int(product) == 435
    assert product <= 1000


def test_encode_value_refuses_impossible_limit() -> None:
    """4.35 at max 435 / factor 100 has no exact encoding - refuse it."""
    reg = NibeRegister(register="1", title="x", factor=100, min=0, max=435)
    with pytest.raises(UnencodableValueError):
        reg.encode_value(4.35)
    assert reg.encode_value(4.34) == "4.34"


@pytest.mark.parametrize(("mode", "writable"), [("R/W", True), ("r/w", False)])
def test_writable_requires_exact_mode(mode: str, writable: bool) -> None:
    """Only exactly 'R/W' is writable, like NibePi's own check."""
    payload = json.loads(ROOM_SETPOINT_PAYLOAD) | {"mode": mode}
    assert NibeRegister.from_payload(json.dumps(payload)).writable is writable


def _payload(**fields: object) -> str:
    base = {"register": "1", "factor": 1, "size": "u8", "mode": "R", "titel": "x"}
    return json.dumps(base | fields)


@pytest.mark.parametrize(
    ("info", "mode", "low", "high", "data", "mapping", "label"),
    [
        (  # F1145 47137, writable, range fully described -> select
            "The operational mode of the heat pump 0=Auto 1=Manual 2=Add. heat only",
            "R/W", "0", "2", 1,
            {"0": "Auto", "1": "Manual", "2": "Add. heat only"}, "Manual",
        ),
        (  # 43427, comma separated with spaces around "="
            "20 = Stopped, 40 = Starting, 60 = Running, 100 = Stopping",
            "R", "0", "0", 60,
            {"20": "Stopped", "40": "Starting", "60": "Running", "100": "Stopping"},
            "Running",
        ),
        (  # 43431, label containing digits and a dash
            "10=off,15=starting,20=on,40=10-day mode,80=calibration",
            "R", "0", "0", 40,
            {"10": "off", "15": "starting", "20": "on", "40": "10-day mode",
             "80": "calibration"},
            "10-day mode",
        ),
        (  # 47377, only examples for a 0..48 setting -> stays a number
            " 12=12 Hours 24=24 Hours", "R/W", "0", "48", 34, {}, None,
        ),
        ("Current outdoor temperature", "R", "-500", "500", 3, {}, None),
    ],
)  # fmt: skip
def test_mapping_from_info(
    info: str,
    mode: str,
    low: str,
    high: str,
    data: int,
    mapping: dict[str, str],
    label: str | None,
) -> None:
    """Value maps described only in 'info' are used when they are complete."""
    reg = NibeRegister.from_payload(
        _payload(info=info, mode=mode, min=low, max=high, data=data)
    )
    assert reg.mapping == mapping
    assert reg.current_label == label


def test_disconnected_sensor_has_no_value() -> None:
    """NibePi's 0x8000 placeholder (-3276.8 at factor 10) means no sensor."""
    reg = NibeRegister.from_payload(
        _payload(register="40007", factor=10, size="s16", data=-3276.8)
    )
    assert reg.value is None
    # A real -3276.7 is kept; unsigned registers are never placeholders.
    assert NibeRegister.from_payload(
        _payload(factor=10, size="s16", data=-3276.7)
    ).value == pytest.approx(-3276.7)
    assert NibeRegister.from_payload(_payload(size="u8", data=0)).value == 0


@pytest.mark.parametrize(
    ("fields", "counter"),
    [
        ({"size": "s32", "min": "0", "max": "9999999", "unit": ""}, True),  # starts
        ({"size": "s32", "min": "0", "max": "1000000", "unit": "h"}, True),  # hours
        ({"size": "u32", "unit": "kWh", "factor": 10}, True),  # heat meter
        ({"size": "s32", "min": "-30000", "max": "30000"}, False),  # degree min.
        ({"size": "s16", "unit": "h"}, False),
        ({"size": "s32", "min": "0", "max": "100", "mode": "R/W"}, False),
    ],
)
def test_is_counter(fields: dict[str, object], counter: bool) -> None:
    """Read-only, non-negative 32-bit registers are ever-increasing counters."""
    assert NibeRegister.from_payload(_payload(**fields)).is_counter is counter


@pytest.mark.parametrize(("factor", "decimals"), [(1, 0), (10, 1), (100, 2)])
def test_decimals(factor: int, decimals: int) -> None:
    """Display precision follows the factor."""
    assert NibeRegister(register="1", title="x", factor=factor).decimals == decimals


def test_raw_value_is_not_truncated() -> None:
    """raw_value is passed through as published."""
    reg = NibeRegister.from_payload(_payload(factor=10, data=24.5, raw_data=24.5))
    assert reg.raw_value == 24.5


@pytest.mark.parametrize(
    "info",
    [
        # F1145 43514: relay bit field
        "Indicates active relays on the PCA Base card. Please refer to the wiring "
        "diagram for relay description. Binary encoded. 1=on, 0=off. "
        "Bit0=K4,Bit1=K3,Bit2=K2,Bit3=K1",
        # F750 40370
        "0=Off, 1=On. b0:EM1-GP4, b1:Cool need, b2:QN32, b3:QN11 close",
    ],
)
def test_bitfields_are_not_value_maps(info: str) -> None:
    """Bit field descriptions do not become selects/enums."""
    assert NibeRegister.from_payload(_payload(info=info)).mapping == {}


def test_label_punctuation_is_cleaned() -> None:
    """Sentence punctuation and unbalanced brackets are stripped from labels."""
    reg = NibeRegister.from_payload(
        _payload(
            info="Ground water pump control signal (0 = 0V-10V; 1= 10V-0V)",
            mode="R",
        )
    )
    assert reg.mapping == {"0": "0V-10V", "1": "10V-0V"}
    reg = NibeRegister.from_payload(
        _payload(info="0 = fixed price. 1 = tariff. 2= spot price.")
    )
    assert reg.mapping == {"0": "fixed price", "1": "tariff", "2": "spot price"}


@pytest.mark.parametrize(
    ("info", "kind"),
    [
        ("Activates the climate system 2 accessory 0=Off 1=On", RegisterKind.SWITCH),
        ("0=not activated, 1=activated", RegisterKind.SWITCH),
        ("0=not affecting, 1=affecting", RegisterKind.SWITCH),
        ("Binary or linear stepping method. 0=Linear 1=Binary", RegisterKind.SELECT),
    ],
)
def test_on_off_maps_are_switches(info: str, kind: RegisterKind) -> None:
    """A writable 0/1 register with on/off-like labels stays a switch."""
    reg = NibeRegister.from_payload(
        _payload(info=info, mode="R/W", min="0", max="1", data=1)
    )
    assert reg.kind is kind
    if kind is RegisterKind.SWITCH:
        assert reg.is_on is True


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
