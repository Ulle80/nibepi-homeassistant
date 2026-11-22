"""Data models for NibePi registers.

Pure Python, no Home Assistant imports - keeps parsing unit-testable and makes a
later split into a standalone PyPI library (required for HA core) trivial.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


class InvalidRegisterPayloadError(ValueError):
    """Raised when a /json payload cannot be parsed into a register."""


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
    def scaled_min(self) -> float | None:
        """Lower limit in display units (NibePi stores min/max unscaled)."""
        return None if self.min is None else self.min / self.factor

    @property
    def scaled_max(self) -> float | None:
        """Upper limit in display units."""
        return None if self.max is None else self.max / self.factor

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
            writable=str(data.get("mode", "R")).upper() == "R/W",
            min=min_,
            max=max_,
            mapping=mapping,
            value=data.get("data"),
            raw_value=int(raw) if isinstance(raw, (int, float)) else None,
            timestamp=data.get("timestamp"),
        )

    def update_from(self, other: NibeRegister) -> None:
        """Take over the runtime values of a newer payload."""
        self.value = other.value
        self.raw_value = other.raw_value
        self.timestamp = other.timestamp
