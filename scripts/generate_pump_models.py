"""Generate custom_components/nibepi/pump_model_data.py from NibePi model files.

Usage: python scripts/generate_pump_models.py <dir with nibepi models/*.json>
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

OUTPUT = Path(__file__).parent.parent / "custom_components/nibepi/pump_model_data.py"


def load(path: Path) -> set[int]:
    """Return the register numbers of one model file (some are cp1252)."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    return {int(item["register"]) for item in json.loads(text)}


def sort_key(name: str) -> tuple[str, int]:
    """Sort F370 before F1145."""
    match = re.match(r"([A-Z]+)(\d+)", name)
    assert match
    return match.group(1), int(match.group(2))


def ranges(numbers: set[int]) -> str:
    """Compress numbers to '1-3,7'."""
    parts: list[str] = []
    ordered = sorted(numbers)
    start = prev = ordered[0]
    for number in [*ordered[1:], None]:
        if number is not None and number == prev + 1:
            prev = number
            continue
        parts.append(f"{start}-{prev}" if prev != start else f"{start}")
        if number is not None:
            start = prev = number
    return ",".join(parts)


def wrapped(text: str, indent: int) -> str:
    """Split a long string into implicitly concatenated lines."""
    width = 80 - indent - 2
    return "\n".join(
        " " * indent + f'"{text[i : i + width]}"' for i in range(0, len(text), width)
    )


def main(model_dir: Path) -> None:
    """Write the data module."""
    models = {
        path.stem: load(path)
        for path in sorted(model_dir.glob("*.json"))
        if not path.stem.startswith("_")
    }
    rmu = set().union(
        *(regs for name, regs in models.items() if name.startswith("RMU"))
    )
    groups: dict[frozenset[int], list[str]] = {}
    for name, regs in models.items():
        if not name.startswith("RMU"):
            groups.setdefault(frozenset(regs - rmu), []).append(name)
    items = sorted(
        ((sorted(names, key=sort_key), regs) for regs, names in groups.items()),
        key=lambda item: sort_key(item[0][0]),
    )
    lines = [
        '"""Register numbers per NibePi model file (generated, do not edit).',
        "",
        "Source: anerdins/nibepi models/*.json (MIT licence). Models with identical",
        "files share one entry. Registers of the RMU40 room units are listed",
        "separately, because they appear next to any pump model.",
        "Regenerate with scripts/generate_pump_models.py.",
        '"""',
        "",
        "# fmt: off",
        "RMU_REGISTERS = (",
        wrapped(ranges(rmu), 4),
        ")",
        "",
        "MODEL_REGISTERS: dict[tuple[str, ...], str] = {",
    ]
    for names, regs in items:
        key = (
            "("
            + ", ".join(f'"{n}"' for n in names)
            + ("," if len(names) == 1 else "")
            + ")"
        )
        lines += [f"    {key}: (", wrapped(ranges(set(regs)), 8), "    ),"]
    lines += ["}", "# fmt: on", ""]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
    print(f"Wrote {OUTPUT}")
