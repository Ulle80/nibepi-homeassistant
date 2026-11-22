"""Model detection from the registers NibePi publishes (pure Python)."""

from __future__ import annotations

from custom_components.nibepi.pump_models import (
    MIN_REGISTERS_FOR_DETECTION,
    MODELS,
    candidate_models,
    detect_model,
    model_label,
)

# Registers of the enabled entities of the first tester's F1145 (incl. RMU40).
F1145_LIVE = [
    47007, 47011, 47398, 47041, 10020, 48132, 10001, 45001, 40072, 43433, 40067,
    40185, 42100, 40004, 40008, 40033, 40014, 40013, 43009, 43416, 43427, 43435,
    40015, 40016, 40017, 40018, 40019, 40022, 40012, 42403, 42183, 42178, 42170,
    42176, 42168, 43439, 40007, 10011, 10012, 43065, 43064, 42439, 42447, 42437,
    42445, 10021, 10022, 43084, 43086, 44878, 44879, 44896, 41929, 44874, 44908,
    43437, 43431, 43239, 43424, 43081, 43420, 42101,
]  # fmt: skip


def test_identical_model_files_cannot_be_told_apart() -> None:
    """F1145 and F1245 share one file; F1355 also contains these registers."""
    assert candidate_models(F1145_LIVE) == [("F1145", "F1245"), ("F1355",)]
    assert detect_model(F1145_LIVE) is None


def test_one_more_register_decides() -> None:
    """40074 exists for F1145/F1245, not for F1355."""
    assert detect_model([*F1145_LIVE, 40074]) == "F1145 / F1245"
    assert detect_model([str(r) for r in [*F1145_LIVE, 40074]]) == "F1145 / F1245"


def test_too_few_registers() -> None:
    """With only shared basics every model would fit, so nothing is guessed."""
    few = [40008, 40012, 40014, 40015, 40016, 40017, 40018, 40019, 40022]
    assert len(few) < MIN_REGISTERS_FOR_DETECTION
    assert candidate_models(few) == []
    # RMU40 registers do not count.
    assert candidate_models([*few, 10001, 10011, 10012, 40004, 40013]) == []


def test_unknown_register_matches_nothing() -> None:
    """A register no model file has (e.g. a newer NibePi) gives no guess."""
    assert candidate_models([*F1145_LIVE, 99999]) == []
    assert detect_model([*F1145_LIVE, "not-a-number"]) is None


def test_model_list() -> None:
    """All pump models are selectable, small series first."""
    assert {"F1145", "F1245", "F1155", "F1255", "F750", "SMO40", "VVM500"} <= set(
        MODELS
    )
    assert not any(model.startswith("RMU") for model in MODELS)
    assert MODELS.index("F370") < MODELS.index("F1145") < MODELS.index("F1155")
    assert model_label(("VVM225", "VVM320")) == "VVM225 / VVM320"
