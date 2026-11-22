"""Translations for NibePi value labels.

NibePi's model files label values in Swedish (alarms, "Från", fan speeds) or
English (descriptions like "0=Auto 1=Manual"). Home Assistant's translation
files cannot cover them because the labels come from the device at runtime, so
they are translated here. Pure Python, no Home Assistant imports.

Lookup is by a normalized key: casefolded, with every non-ASCII character
replaced by "?". Some model files contain broken umlauts ("Fr�n"), which
then still match the proper spelling ("Från").
"""

from __future__ import annotations

LANGUAGES: tuple[str, ...] = ("en", "de", "sv", "da", "nb")
DEFAULT_LANGUAGE = "nb"
LANGUAGE_AUTO = "auto"

# normalized key: (en, de, sv, da, nb)
_ROWS: dict[str, tuple[str, str, str, str, str]] = {
    # --- states ---
    "off": ("Off", "Aus", "Från", "Fra", "Av"),
    "on": ("On", "Ein", "Till", "Til", "På"),
    "yes": ("Yes", "Ja", "Ja", "Ja", "Ja"),
    "no": ("No", "Nein", "Nej", "Nej", "Nei"),
    "active": ("Active", "Aktiv", "Aktiv", "Aktiv", "Aktiv"),
    "inactive": ("Inactive", "Inaktiv", "Inaktiv", "Inaktiv", "Inaktiv"),
    "activated": ("Activated", "Aktiviert", "Aktiverad", "Aktiveret", "Aktivert"),
    "not activated": ("Not activated", "Nicht aktiviert", "Ej aktiverad",
                      "Ikke aktiveret", "Ikke aktivert"),
    "deactivated": ("Deactivated", "Deaktiviert", "Avaktiverad", "Deaktiveret",
                    "Deaktivert"),
    "affecting": ("Affecting", "Wirksam", "Påverkar", "Påvirker", "Påvirker"),
    "not affecting": ("Not affecting", "Nicht wirksam", "Påverkar inte",
                      "Påvirker ikke", "Påvirker ikke"),
    "active wait": ("Active, waiting", "Aktiv, wartend", "Aktiv, väntar",
                    "Aktiv, venter", "Aktiv, venter"),
    "blocked": ("Blocked", "Gesperrt", "Blockerad", "Blokeret", "Blokkert"),
    "unblocked": ("Unblocked", "Freigegeben", "Ej blockerad", "Ikke blokeret",
                  "Ikke blokkert"),
    "open": ("Open", "Offen", "Öppen", "Åben", "Åpen"),
    "closed": ("Closed", "Geschlossen", "Stängd", "Lukket", "Lukket"),
    "running": ("Running", "In Betrieb", "I drift", "I drift", "I drift"),
    "starting": ("Starting", "Startet", "Startar", "Starter", "Starter"),
    "stopping": ("Stopping", "Stoppt", "Stoppar", "Stopper", "Stopper"),
    "stopped": ("Stopped", "Gestoppt", "Stoppad", "Stoppet", "Stoppet"),
    "passive": ("Passive", "Passiv", "Passiv", "Passiv", "Passiv"),
    "unknown": ("Unknown", "Unbekannt", "Okänd", "Ukendt", "Ukjent"),
    "calibration": ("Calibration", "Kalibrierung", "Kalibrering", "Kalibrering",
                    "Kalibrering"),
    "10-day mode": ("10-day mode", "10-Tage-Modus", "10-dagarsläge",
                    "10-dages tilstand", "10-dagersmodus"),
    # --- operating modes ---
    "auto": ("Auto", "Auto", "Auto", "Auto", "Auto"),
    "manual": ("Manual", "Manuell", "Manuell", "Manuel", "Manuell"),
    "manual setting": ("Manual setting", "Manuelle Einstellung",
                       "Manuell inställning", "Manuel indstilling",
                       "Manuell innstilling"),
    "add. heat only": ("Add. heat only", "Nur Zusatzheizung", "Endast tillsats",
                       "Kun tilskud", "Kun tilskudd"),
    "auto controlled": ("Auto controlled", "Automatisch geregelt",
                        "Automatiskt styrd", "Automatisk styret",
                        "Automatisk styrt"),
    "fixed delta controlled": ("Fixed delta controlled", "Feste Spreizung",
                               "Fast delta-styrd", "Fast delta-styret",
                               "Fast delta-styrt"),
    "intermittent": ("Intermittent", "Intervallbetrieb", "Intermittent",
                     "Intermitterende", "Intermitterende"),
    "continuous": ("Continuous", "Dauerbetrieb", "Kontinuerlig", "Kontinuerlig",
                   "Kontinuerlig"),
    "economy": ("Economy", "Sparbetrieb", "Ekonomi", "Økonomi", "Økonomi"),
    "eco": ("Eco", "Eco", "Eco", "Eco", "Eco"),
    "normal": ("Normal", "Normal", "Normal", "Normal", "Normal"),
    "luxury": ("Luxury", "Luxus", "Lyx", "Luksus", "Luksus"),
    "smart control": ("Smart Control", "Smart Control", "Smart Control",
                      "Smart Control", "Smart Control"),
    "default": ("Default", "Standard", "Standard", "Standard", "Standard"),
    "away from home": ("Away from home", "Abwesend", "Borta", "Ikke hjemme",
                       "Borte"),
    "vacation": ("Vacation", "Urlaub", "Semester", "Ferie", "Ferie"),
    "one time increase": ("One time increase", "Einmalige Erhöhung",
                          "Engångshöjning", "Engangsforøgelse", "Engangsøkning"),
    "linear": ("Linear", "Linear", "Linjär", "Lineær", "Lineær"),
    "binary": ("Binary", "Binär", "Binär", "Binær", "Binær"),
    # --- what the pump is doing ---
    "heat": ("Heat", "Heizung", "Värme", "Varme", "Varme"),
    "heating": ("Heating", "Heizen", "Uppvärmning", "Opvarmning", "Oppvarming"),
    "hot water": ("Hot water", "Warmwasser", "Varmvatten", "Varmt vand",
                  "Varmtvann"),
    "cooling": ("Cooling", "Kühlung", "Kyla", "Køling", "Kjøling"),
    "pool": ("Pool", "Pool", "Pool", "Pool", "Basseng"),
    "pool 1": ("Pool 1", "Pool 1", "Pool 1", "Pool 1", "Basseng 1"),
    "pool 2": ("Pool 2", "Pool 2", "Pool 2", "Pool 2", "Basseng 2"),
    "transfer": ("Transfer", "Übertragung", "Överföring", "Overførsel",
                 "Overføring"),
    "external request": ("External request", "Externe Anforderung",
                         "Extern begäran", "Ekstern anmodning",
                         "Ekstern forespørsel"),
    "compressor": ("Compressor", "Verdichter", "Kompressor", "Kompressor",
                   "Kompressor"),
    "internal addition": ("Internal addition", "Interne Zusatzheizung",
                          "Intern tillsats", "Intern tilskud", "Intern tilskudd"),
    "no defrost": ("No defrost", "Keine Abtauung", "Ingen avfrostning",
                   "Ingen afrimning", "Ingen avriming"),
    "passive defrost": ("Passive defrost", "Passive Abtauung",
                        "Passiv avfrostning", "Passiv afrimning",
                        "Passiv avriming"),
    "active defrost": ("Active defrost", "Aktive Abtauung", "Aktiv avfrostning",
                       "Aktiv afrimning", "Aktiv avriming"),
    "defrosting": ("Defrosting", "Abtauung", "Avfrostning", "Afrimning",
                   "Avriming"),
    "shunt off": ("Mixing valve off", "Mischer aus", "Shunt från", "Shunt fra",
                  "Shunt av"),
    "shunt open": ("Mixing valve opening", "Mischer öffnet", "Shunt öppnar",
                   "Shunt åbner", "Shunt åpner"),
    "shunt closed": ("Mixing valve closing", "Mischer schließt", "Shunt stänger",
                     "Shunt lukker", "Shunt lukker"),
    "radiator": ("Radiator", "Heizkörper", "Radiator", "Radiator", "Radiator"),
    "floor heating": ("Floor heating", "Fußbodenheizung", "Golvvärme",
                      "Gulvvarme", "Gulvvarme"),
    "radiator + floor heating": ("Radiator + floor heating",
                                 "Heizkörper + Fußbodenheizung",
                                 "Radiator + golvvärme", "Radiator + gulvvarme",
                                 "Radiator + gulvvarme"),
    "speed 1": ("Speed 1", "Stufe 1", "Hastighet 1", "Hastighed 1", "Hastighet 1"),
    "speed 2": ("Speed 2", "Stufe 2", "Hastighet 2", "Hastighed 2", "Hastighet 2"),
    "speed 3": ("Speed 3", "Stufe 3", "Hastighet 3", "Hastighed 3", "Hastighet 3"),
    "speed 4": ("Speed 4", "Stufe 4", "Hastighet 4", "Hastighed 4", "Hastighet 4"),
    "12 hours": ("12 hours", "12 Stunden", "12 timmar", "12 timer", "12 timer"),
    "24 hours": ("24 hours", "24 Stunden", "24 timmar", "24 timer", "24 timer"),
    # --- electricity price ---
    "cheap": ("Cheap", "Günstig", "Billigt", "Billig", "Billig"),
    "expensive": ("Expensive", "Teuer", "Dyrt", "Dyr", "Dyr"),
    "price": ("Price", "Preis", "Pris", "Pris", "Pris"),
    "fixed price": ("Fixed price", "Festpreis", "Fast pris", "Fast pris",
                    "Fast pris"),
    "spot price": ("Spot price", "Spotpreis", "Spotpris", "Spotpris", "Spotpris"),
    "tariff": ("Tariff", "Tarif", "Tariff", "Tarif", "Tariff"),
    "primary factor": ("Primary energy factor", "Primärenergiefaktor",
                       "Primärenergifaktor", "Primærenergifaktor",
                       "Primærenergifaktor"),
    # --- alarms (Swedish in the model files) ---
    "no alarm": ("No alarm", "Kein Alarm", "Inga larm", "Ingen alarm",
                 "Ingen alarm"),
    "low exhaust air temperature": ("Low exhaust air temperature",
                                    "Niedrige Ablufttemperatur",
                                    "Låg frånluftstemperatur",
                                    "Lav afkasttemperatur",
                                    "Lav avtrekkstemperatur"),
    "failed defrost": ("Defrosting failed", "Abtauung fehlgeschlagen",
                       "Misslyckad avfrostning", "Mislykket afrimning",
                       "Mislykket avriming"),
    "failed periodic increase": ("Periodic increase failed",
                                 "Periodische Erhöhung fehlgeschlagen",
                                 "Misslyckad periodisk höjning",
                                 "Mislykket periodisk forøgelse",
                                 "Mislykket periodisk økning"),
    "frost protection": ("Frost protection", "Frostschutz", "Frysskydd",
                         "Frostbeskyttelse", "Frostbeskyttelse"),
    "power limiter activated": ("Power limiter activated",
                                "Leistungswächter aktiv", "Effektvakt aktiverad",
                                "Effektvagt aktiveret", "Effektvakt aktivert"),
    "filter alarm": ("Filter alarm", "Filteralarm", "Filterlarm", "Filteralarm",
                     "Filteralarm"),
    "modbus communication error": ("Modbus communication error",
                                   "Modbus-Kommunikationsfehler",
                                   "Kom.avb Modbus",
                                   "Modbus-kommunikationsfejl",
                                   "Modbus-kommunikasjonsfeil"),
    "rmu system 4 communication error": ("RMU system 4 communication error",
                                         "RMU System 4 Kommunikationsfehler",
                                         "RMU System 4 Kom.avb",
                                         "RMU system 4 kommunikationsfejl",
                                         "RMU system 4 kommunikasjonsfeil"),
    # --- misc settings ---
    "use log.set": ("Use LOG.SET", "LOG.SET verwenden", "Använd LOG.SET",
                    "Brug LOG.SET", "Bruk LOG.SET"),
    "ignore log.set": ("Ignore LOG.SET", "LOG.SET ignorieren", "Ignorera LOG.SET",
                       "Ignorer LOG.SET", "Ignorer LOG.SET"),
}  # fmt: skip

# Other spellings found in the model files -> key in _ROWS.
_ALIASES: dict[str, str] = {
    "fr?n": "off",
    "continous": "continuous",
    "normal+": "normal",
    "pool2": "pool 2",
    "?verf?ring": "transfer",
    "v?rme": "heat",
    "varmvatten": "hot water",
    "kyla": "cooling",
    "avfrostning": "defrosting",
    "eng?ngsh?jning": "one time increase",
    "hastighet 1": "speed 1",
    "hastighet 2": "speed 2",
    "hastighet 3": "speed 3",
    "hastighet 4": "speed 4",
    "inga larm": "no alarm",
    "l?g fr?nluftstemperatur": "low exhaust air temperature",
    "misslyckad avfrostning": "failed defrost",
    "misslyckad periodisk h?jning": "failed periodic increase",
    "frysskydd": "frost protection",
    "effektvakt aktiverad": "power limiter activated",
    "filterlarm": "filter alarm",
    "kom.avb modbus": "modbus communication error",
    "rmu system 4 kom.avb": "rmu system 4 communication error",
}


def normalize(label: str) -> str:
    """Return the lookup key for a label."""
    return "".join(c if c.isascii() else "?" for c in label.casefold().strip())


def translate(label: str, language: str) -> str:
    """Translate a NibePi value label; unknown labels are returned unchanged."""
    if language not in LANGUAGES:
        return label
    key = normalize(label)
    row = _ROWS.get(_ALIASES.get(key, key))
    if row is None:
        return label
    if key == "normal+":  # keep the "+" variant distinguishable
        return f"{row[LANGUAGES.index(language)]}+"
    return row[LANGUAGES.index(language)]


def resolve_language(setting: str | None, ha_language: str | None) -> str:
    """Pick the label language: explicit setting, else HA's, else Norwegian."""
    if setting and setting != LANGUAGE_AUTO:
        return setting if setting in LANGUAGES else DEFAULT_LANGUAGE
    lang = (ha_language or "").replace("_", "-").split("-")[0].lower()
    if lang in ("no", "nn"):
        lang = "nb"
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE
