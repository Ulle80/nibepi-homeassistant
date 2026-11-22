"""Guess the pump model from the registers NibePi publishes.

NibePi does not publish its configured model over MQTT. It only publishes
registers from its model file, so the model must be one whose file contains
every register seen. Some models share a file and cannot be told apart.
Pure Python, no Home Assistant imports.
"""

from __future__ import annotations

from collections.abc import Iterable

from .pump_model_data import MODEL_REGISTERS, RMU_REGISTERS

# Below this, almost every model still fits (all share the basic registers).
MIN_REGISTERS_FOR_DETECTION = 10


def _parse_ranges(text: str) -> frozenset[int]:
    numbers: set[int] = set()
    for part in text.split(","):
        start, _, end = part.partition("-")
        numbers.update(range(int(start), int(end or start) + 1))
    return frozenset(numbers)


_RMU = _parse_ranges(RMU_REGISTERS)
_GROUPS: dict[tuple[str, ...], frozenset[int]] = {
    names: _parse_ranges(text) for names, text in MODEL_REGISTERS.items()
}

# Single model names, for choosing the model manually.
MODELS: tuple[str, ...] = tuple(
    sorted(
        (name for names in _GROUPS for name in names),
        key=lambda name: (name.rstrip("0123456789"), len(name), name),
    )
)


def model_label(names: Iterable[str]) -> str:
    """Return the display name of models sharing one file, e.g. 'F1145 / F1245'."""
    return " / ".join(names)


def candidate_models(registers: Iterable[str | int]) -> list[tuple[str, ...]]:
    """Return the model groups whose files contain every register seen.

    Room unit (RMU40) registers are ignored, they exist next to any model. An
    empty list means too few registers so far, or none of the known models fits.
    """
    seen: set[int] = set()
    for register in registers:
        try:
            seen.add(int(register))
        except ValueError:
            continue
    seen -= _RMU
    if len(seen) < MIN_REGISTERS_FOR_DETECTION:
        return []
    return [names for names, known in _GROUPS.items() if seen <= known]


def detect_model(registers: Iterable[str | int]) -> str | None:
    """Return the model if exactly one model file fits, else None."""
    candidates = candidate_models(registers)
    return model_label(candidates[0]) if len(candidates) == 1 else None
