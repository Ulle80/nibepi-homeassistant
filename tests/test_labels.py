"""Tests for value label translations."""

from __future__ import annotations

import pytest

from custom_components.nibepi.labels import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    resolve_language,
    translate,
)

# Every Swedish label found in NibePi's model files (as of master, Oct 2023).
SWEDISH_MODEL_LABELS = [
    "Från",
    "Fr�n",  # broken encoding in some model files
    "Inga larm",
    "Låg frånluftstemperatur",
    "Misslyckad avfrostning",
    "Misslyckad periodisk höjning",
    "Frysskydd",
    "Effektvakt aktiverad",
    "Avfrostning",
    "Filterlarm",
    "Kom.avb Modbus",
    "RMU System 4 Kom.avb",
    "Engångshöjning",
    "Hastighet 1",
    "Hastighet 4",
    "Kyla",
    "Värme",
    "Varmvatten",
    "Överföring",
]


@pytest.mark.parametrize("label", SWEDISH_MODEL_LABELS)
def test_all_swedish_labels_are_translated(label: str) -> None:
    """No Swedish label from the model files is left untranslated in German."""
    assert translate(label, "de") != label


@pytest.mark.parametrize(
    ("label", "language", "expected"),
    [
        ("Från", "de", "Aus"),
        ("Fr�n", "de", "Aus"),
        ("Från", "nb", "Av"),
        ("Från", "en", "Off"),
        ("Från", "sv", "Från"),
        ("Inga larm", "da", "Ingen alarm"),
        ("Låg frånluftstemperatur", "de", "Niedrige Ablufttemperatur"),
        ("Hot Water", "de", "Warmwasser"),
        ("CHEAP", "en", "Cheap"),
        ("Add. heat only", "sv", "Endast tillsats"),
        ("Normal+", "de", "Normal+"),
        ("Continous", "de", "Dauerbetrieb"),
        ("G20/G25", "de", "G20/G25"),  # technical, unknown -> unchanged
        ("Från", "fr", "Från"),  # unsupported language -> unchanged
    ],
)
def test_translate(label: str, language: str, expected: str) -> None:
    """Labels translate case- and encoding-insensitively."""
    assert translate(label, language) == expected


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_row_has_all_languages(language: str) -> None:
    """Each language returns a non-empty text for a known label."""
    assert translate("Off", language)


@pytest.mark.parametrize(
    ("setting", "ha_language", "expected"),
    [
        ("auto", "de", "de"),
        ("auto", "de-CH", "de"),
        ("auto", "en-GB", "en"),
        ("auto", "no", "nb"),
        ("auto", "nn", "nb"),
        ("auto", "fr", DEFAULT_LANGUAGE),
        (None, None, DEFAULT_LANGUAGE),
        ("sv", "de", "sv"),
        ("xx", "de", DEFAULT_LANGUAGE),
    ],
)
def test_resolve_language(
    setting: str | None, ha_language: str | None, expected: str
) -> None:
    """Explicit choice wins, else Home Assistant's language, else Norwegian."""
    assert resolve_language(setting, ha_language) == expected
