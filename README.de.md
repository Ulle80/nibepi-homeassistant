# NibePi für Home Assistant

[English](README.md) · **Deutsch**

Custom Integration für den Home-Assistant-Marketplace (früher HACS), die einen [NibePi](https://github.com/anerdins/nibepi) – Raspberry Pi am RS485/Modbus einer NIBE F-Serie-Wärmepumpe – über **MQTT** sauber in Home Assistant einbindet: ein Gerät, stabile Unique-IDs, korrekte Device-Classes, Verfügbarkeit über den NibePi-Last-Will.

> Status: **früh** (v0.5.0), getestet an einer NIBE F1145, geprüft gegen alle NibePi-Modelldateien.

**Sprache:** Zustände wie Betriebsart, Alarme oder Pumpenstatus erscheinen auf Deutsch, Englisch, Schwedisch, Dänisch oder Norwegisch – einstellbar unter Integration → **Konfigurieren** (Standard: Sprache von Home Assistant, sonst Norwegisch). Entity-Namen bleiben englisch, so wie NibePi sie liefert.

**Pumpenmodell:** wird automatisch aus den gemeldeten Registern erkannt und am Gerät angezeigt, z.B. „F1145 / F1245“ (Modelle mit identischer NibePi-Modelldatei lassen sich nicht unterscheiden). Unter **Konfigurieren** kannst du es auch fest wählen. Das Modell dient nur der Anzeige – welche Entities es gibt, bestimmt NibePi.

**Nicht angeschlossene Fühler** (z.B. Vorlauf Heizkreis 2, wenn es keinen zweiten Heizkreis gibt) meldet NibePi mit einem Platzhalterwert. Die Integration deaktiviert solche Sensoren automatisch; liefern sie später Werte, werden sie wieder aktiviert. Ein Fühler, der schon einmal Werte geliefert hat, bleibt sichtbar (dann als „nicht verfügbar“), damit ein Defekt auffällt.

Nach einem Neustart von Home Assistant sind alle bekannten Entities sofort wieder da und werden aktiv beim NibePi abgefragt; sie zeigen „nicht verfügbar“, bis der erste Wert eintrifft.

## Was du bekommst
| Register | Entity |
|---|---|
| nur lesbar | Sensor (mit Wertetabelle als Auswahl-Sensor) |
| schreibbar, mit Wertetabelle | Select |
| schreibbar, 0/1 ohne Einheit | Switch |
| schreibbar, sonst | Number (Grenzen und Schrittweite aus dem Register) |

Schreibbare Register erscheinen als Konfigurations-Entities am Gerät und sind **standardmäßig deaktiviert** – außer Heizkurve, Kurvenverschiebung, Raum-Sollwert, Warmwasser-Komfortmodus und Temporary Lux. Alles andere (Betriebsart, Gradminuten, Pumpendrehzahlen, Zusatzheizung …) aktivierst du bewusst unter Gerät → Entities. Nach dem Schreiben liest NibePi das Register zurück; der neue Wert erscheint, sobald NibePi ihn publiziert. Eine Fehlermeldung bei abgelehnten Werten liefert NibePi nicht.

## Voraussetzungen
- NibePi mit aktiviertem MQTT (Node-RED-UI → Einstellungen), Basis-Topic merken (Standard `nibe/modbus/`)
- NibePi-eigene HA-Discovery **aus**, sonst entstehen doppelte Sensoren
- Home Assistant mit eingerichteter [MQTT-Integration](https://www.home-assistant.io/integrations/mqtt/) am selben Broker

## Installation
NibePi steht noch nicht im Katalog des Marketplace, deshalb fügst du es über den Link hinzu.

**Home Assistant ab 2026.11 (Marketplace):**
1. **Einstellungen** → **Marketplace** → oben rechts **Add from link** (in der deutschen Oberfläche entsprechend übersetzt)
2. Bei **GitHub link** `https://github.com/Ulle80/nibepi-homeassistant` eintragen → **Hinzufügen**. Ist GitHub noch nicht verbunden, fragt der Marketplace vorher danach (GitHub-Gerätecode, nur Lesezugriff auf öffentliche Daten).
3. „NibePi“ in der Liste öffnen, installieren, HA neu starten

**Ältere Versionen mit HACS:** HACS → ⋮ → Benutzerdefinierte Repositories → `https://github.com/Ulle80/nibepi-homeassistant`, Kategorie *Integration* → „NibePi“ installieren, HA neu starten.

Danach unter Einstellungen → Geräte & Dienste: NibePi wird bei Standard-Topic automatisch gefunden, sonst „Integration hinzufügen“ → NibePi.

## Updates
Neue Versionen erscheinen unter **Einstellungen** → **Updates**, zusammen mit den Home-Assistant-Updates. Nach dem Update HA neu starten. Angeboten werden nur GitHub-Releases, nicht jeder Commit.

## Erster Test mit echter Hardware
Schritt-für-Schritt-Checkliste: [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md)

## Fehlersuche
Einstellungen → Geräte & Dienste → NibePi → ⋮ → **Diagnose herunterladen**. Die Datei enthält Konfiguration, Verfügbarkeit und alle bekannten Register mit Definition, Entity-Typ und aktuellem Wert (keine Passwörter – die liegen in der MQTT-Integration). Bitte bei Issues anhängen.

## Entfernen
Einstellungen → **Marketplace** → NibePi öffnen → oben rechts über das ⋮-Menü deinstallieren. Ist die Integration noch eingerichtet, bietet der Dialog an, sie gleich mit zu löschen – das entfernt auch Gerät und Entities. Mit HACS: erst unter Geräte & Dienste löschen, dann in HACS deinstallieren.

## Entwicklung
Siehe [CLAUDE.md](CLAUDE.md) und [docs/NIBEPI_PROTOCOL.md](docs/NIBEPI_PROTOCOL.md).

```bash
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```
Am einfachsten im Devcontainer (VS Code → „Reopen in Container“).
