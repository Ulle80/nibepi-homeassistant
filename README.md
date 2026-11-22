# NibePi für Home Assistant

Custom Integration (HACS), die einen [NibePi](https://github.com/anerdins/nibepi) – Raspberry Pi am RS485/Modbus einer NIBE F-Serie-Wärmepumpe – über **MQTT** sauber in Home Assistant einbindet: ein Gerät, stabile Unique-IDs, korrekte Device-Classes, Verfügbarkeit über den NibePi-Last-Will.

> Status: **früh** (v0.3.0), noch nicht gegen echte Hardware getestet.

Nach einem Neustart von Home Assistant sind alle bekannten Entities sofort wieder da und werden aktiv beim NibePi abgefragt; sie zeigen „nicht verfügbar“, bis der erste Wert eintrifft.

## Was du bekommst
| Register | Entity |
|---|---|
| nur lesbar | Sensor (mit Wertetabelle als Auswahl-Sensor) |
| schreibbar, mit Wertetabelle | Select |
| schreibbar, 0/1 ohne Einheit | Switch |
| schreibbar, sonst | Number (Grenzen und Schrittweite aus dem Register) |

Schreibbare Register erscheinen als Konfigurations-Entities am Gerät. Nach dem Schreiben liest NibePi das Register zurück; der neue Wert erscheint, sobald NibePi ihn publiziert. Eine Fehlermeldung bei abgelehnten Werten liefert NibePi nicht.

## Voraussetzungen
- NibePi mit aktiviertem MQTT (Node-RED-UI → Einstellungen), Basis-Topic merken (Standard `nibe/modbus/`)
- NibePi-eigene HA-Discovery **aus**, sonst entstehen doppelte Sensoren
- Home Assistant mit eingerichteter [MQTT-Integration](https://www.home-assistant.io/integrations/mqtt/) am selben Broker

## Installation (HACS)
1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories → dieses Repo, Kategorie *Integration*
2. „NibePi“ installieren, HA neu starten
3. Einstellungen → Geräte & Dienste: NibePi wird bei Standard-Topic automatisch gefunden, sonst „Integration hinzufügen“ → NibePi

## Entfernen
Einstellungen → Geräte & Dienste → NibePi → Löschen; danach in HACS deinstallieren.

## Entwicklung
Siehe [CLAUDE.md](CLAUDE.md) und [docs/NIBEPI_PROTOCOL.md](docs/NIBEPI_PROTOCOL.md).

```bash
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```
Am einfachsten im Devcontainer (VS Code → „Reopen in Container“).
