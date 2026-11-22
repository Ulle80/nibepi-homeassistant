"""Data models for NibePi registers.

Pure Python, no Home Assistant imports - keeps parsing unit-testable and makes a
later split into a standalone PyPI library (required for HA core) trivial.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
import math
from typing import Any


class InvalidRegisterPayloadError(ValueError):
    """Raised when a /json payload cannot be parsed into a register."""


class UnencodableValueError(ValueError):
    """Raised when NibePi's float truncation cannot produce the wanted value."""


class RegisterKind(StrEnum):
    """Which Home Assistant entity type represents a register."""

    SENSOR = "sensor"
    NUMBER = "number"
    SELECT = "select"
    SWITCH = "switch"


# Raw value range per NibePi register size.
SIZE_LIMITS: dict[str, tuple[int, int]] = {
    "s8": (-(2**7), 2**7 - 1),
    "u8": (0, 2**8 - 1),
    "s16": (-(2**15), 2**15 - 1),
    "u16": (0, 2**16 - 1),
    "s32": (-(2**31), 2**31 - 1),
    "u32": (0, 2**32 - 1),
}

# Static register metadata that survives a restart (runtime values do not).
DEFINITION_FIELDS: tuple[str, ...] = (
    "register",
    "title",
    "unit",
    "info",
    "factor",
    "size",
    "writable",
    "min",
    "max",
    "mapping",
)


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class NibeRegister:
    """A single heat pump register as published by NibePi on <base><reg>/json."""

    register: str
    title: str
    unit: str = ""
    info: str = ""
    factor: float = 1
    size: str = "s16"
    writable: bool = False
    min: float | None = None
    max: float | None = None
    mapping: dict[str, str] = field(default_factory=dict)
    value: Any = None
    raw_value: int | None = None
    timestamp: Any = None

    @property
    def is_enum(self) -> bool:
        """Return True if the register value is a mapped label."""
        return bool(self.mapping)

    @property
    def kind(self) -> RegisterKind:
        """Return the entity type that fits this register."""
        if not self.writable:
            return RegisterKind.SENSOR
        if self.is_enum:
            return RegisterKind.SELECT
        if self.factor == 1 and self.min == 0 and self.max == 1 and not self.unit:
            return RegisterKind.SWITCH
        return RegisterKind.NUMBER

    @property
    def scaled_min(self) -> float | None:
        """Lower limit in display units (NibePi stores min/max unscaled)."""
        return None if self.min is None else self.min / self.factor

    @property
    def scaled_max(self) -> float | None:
        """Upper limit in display units."""
        return None if self.max is None else self.max / self.factor

    @property
    def limits(self) -> tuple[float, float]:
        """Writable range in display units; falls back to the register size."""
        size_min, size_max = SIZE_LIMITS.get(self.size, SIZE_LIMITS["s16"])
        low = self.min if self.min is not None else size_min
        high = self.max if self.max is not None else size_max
        return low / self.factor, high / self.factor

    @property
    def step(self) -> float:
        """Smallest settable increment in display units."""
        return 1 / self.factor

    def key_for_label(self, label: str) -> str:
        """Return the numeric key NibePi expects for a mapped label."""
        for key, value in self.mapping.items():
            if value == label:
                return key
        raise ValueError(f"Unknown option {label!r} for register {self.register}")

    def encode_value(self, value: float) -> str:
        """Format a display value so NibePi writes exactly the intended raw value.

        NibePi computes ``payload * factor`` in JavaScript and truncates the
        result to an integer (no rounding). With binary floats, e.g. ``4.35 * 100``
        is ``434.99999999999994`` and would be written as 434. Python floats are
        the same IEEE 754 doubles, so we can check candidates exactly.

        NibePi also drops (not clamps-and-sends) any value whose product exceeds
        the raw min/max, so a candidate must stay inside that range: at the
        limit only a product of exactly ``raw`` is acceptable.
        """
        raw = round(value * self.factor)
        if self.factor == 1:
            return str(raw)
        low = self.min if self.min is not None else -math.inf
        high = self.max if self.max is not None else math.inf

        def accepted(text: str) -> bool:
            product = float(text) * self.factor
            return int(product) == raw and low <= product <= high

        decimals = max(0, math.ceil(math.log10(self.factor)))
        text = f"{raw / self.factor:.{decimals}f}"
        if accepted(text):
            return text
        # Walk to neighbouring doubles away from zero: the first one whose
        # product reaches raw is the smallest possible overshoot.
        direction = math.copysign(math.inf, raw)
        candidate = raw / self.factor
        for _ in range(8):
            candidate = math.nextafter(candidate, direction)
            if accepted(text := repr(candidate)):
                return text
        # E.g. 4.35 with factor 100 and max 435: every double either truncates
        # to 434 or exceeds max. Refuse instead of writing something else.
        raise UnencodableValueError(
            f"{value} cannot be written exactly to register {self.register}"
        )

    @classmethod
    def from_payload(cls, payload: str | bytes) -> NibeRegister:
        """Parse a NibePi /json payload."""
        try:
            data = json.loads(payload)
        except (TypeError, ValueError) as err:
            raise InvalidRegisterPayloadError(f"Not valid JSON: {err}") from err
        if not isinstance(data, dict) or "register" not in data:
            raise InvalidRegisterPayloadError("Missing 'register' key")

        mapping: dict[str, str] = {}
        for item in data.get("map") or []:
            if isinstance(item, dict):
                mapping.update({str(k): str(v) for k, v in item.items()})

        factor = _to_float(data.get("factor")) or 1
        min_ = _to_float(data.get("min"))
        max_ = _to_float(data.get("max"))
        # NibePi uses 0/0 to mean "no range".
        if min_ == 0 and max_ == 0:
            min_ = max_ = None

        raw = data.get("raw_data")
        return cls(
            register=str(data["register"]),
            title=str(data.get("titel") or data.get("title") or data["register"]),
            unit=str(data.get("unit") or ""),
            info=str(data.get("info") or ""),
            factor=factor,
            size=str(data.get("size") or "s16"),
            # NibePi's setDataValue only writes for exactly "R/W".
            writable=data.get("mode") == "R/W",
            min=min_,
            max=max_,
            mapping=mapping,
            value=data.get("data"),
            raw_value=int(raw) if isinstance(raw, (int, float)) else None,
            timestamp=data.get("timestamp"),
        )

    def as_definition(self) -> dict[str, Any]:
        """Return the static metadata (no runtime values) for persisting."""
        return {name: getattr(self, name) for name in DEFINITION_FIELDS}

    @classmethod
    def from_definition(cls, definition: dict[str, Any]) -> NibeRegister:
        """Recreate a register from ``as_definition`` output (value unknown)."""
        if not isinstance(definition, dict) or "register" not in definition:
            raise InvalidRegisterPayloadError("Invalid stored register definition")
        return cls(
            **{
                name: definition[name]
                for name in DEFINITION_FIELDS
                if name in definition
            }
        )

    def update_from(self, other: NibeRegister) -> None:
        """Take over the runtime values of a newer payload."""
        self.value = other.value
        self.raw_value = other.raw_value
        self.timestamp = other.timestamp
