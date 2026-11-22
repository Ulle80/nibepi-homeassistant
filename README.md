# NibePi für Home Assistant

Custom Integration (HACS), die einen [NibePi](https://github.com/anerdins/nibepi) – Raspberry Pi am RS485/Modbus einer NIBE F-Serie-Wärmepumpe – über **MQTT** sauber in Home Assistant einbindet: ein Gerät, stabile Unique-IDs, korrekte Device-Classes, Verfügbarkeit über den NibePi-Last-Will.

> Status: **frühes Grundgerüst** (v0.1.0). Aktuell nur Sensoren. Schreiben (Number/Select/Switch) ist in Arbeit.

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
