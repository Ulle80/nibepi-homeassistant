# CLAUDE.md – NibePi Home Assistant Integration

## Ziel
HACS-Custom-Integration `nibepi` für [anerdins/nibepi](https://github.com/anerdins/nibepi) (RPi + RS485 an NIBE F-Serie). Kommunikation ausschließlich über HAs MQTT-Integration (`dependencies: ["mqtt"]`), `iot_class: local_push`. Protokolldetails: `docs/NIBEPI_PROTOCOL.md` – vor Änderungen an Topics/Parsing lesen.

## Architektur
- `models.py` – reines Python, **keine HA-Imports**. Parsing der `/json`-Payloads → `NibeRegister`. Soll später als eigene PyPI-Lib ausgelagert werden können (Core-Pflicht).
- `hub.py` – `NibePiHub`: abonniert `<base>+/json` und LWT-Topic, hält `registers`, sendet Dispatcher-Signale (`SIGNAL_NEW_REGISTER`, `SIGNAL_REGISTER_UPDATE`, `SIGNAL_AVAILABILITY`), schreibt via `<base><reg>/set`.
- `entity.py` – `NibePiEntity`-Basis (has_entity_name, unique_id `<entry_id>_<register>`, DeviceInfo).
- Plattformen legen Entities **dynamisch** an, wenn ein neues Register auftaucht.
- `entry.runtime_data` = Hub (typisiert über `NibePiConfigEntry`).

## Standards (verbindlich)
- [HA Developer Docs](https://developers.home-assistant.io/) + [Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/). Fortschritt in `custom_components/nibepi/quality_scale.yaml` pflegen; Ziel: Silver, dann Gold.
- Alles async, keine blockierenden Calls im Event-Loop.
- UI-Texte nur über `strings.json`; `translations/en.json` = Kopie von `strings.json`, `de.json` mitpflegen.
- Kein YAML-Setup, nur Config Flow.
- Jede Änderung mit Tests (`pytest-homeassistant-custom-component`), Config Flow 100 % Coverage.
- `ruff check` + `ruff format` müssen sauber sein. Typ-Hints überall.
- `manifest.json`: Keys alphabetisch (außer domain, name zuerst), Version bei Release erhöhen.

## Befehle
```bash
pip install -r requirements_dev.txt
pytest
ruff check . --fix && ruff format .
PYTHONPATH=. hass -c config --debug   # Dev-Instanz auf :8123
```
Lokal unter Windows: HA lässt sich nativ nicht installieren (C-Extensions). Daher:
- ruff: `.\.venv\Scripts\ruff.exe check .` (Windows-venv, Python 3.13, nur Lint-Tools)
- Tests in WSL (Ubuntu, venv `~/.venvs/nibepi`):
  `wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/socia/Documents/Claude/nibepi-homeassistant && ~/.venvs/nibepi/bin/pytest -p no:cacheprovider"`
- Alternativ Devcontainer.

## Projekt-Agenten (`.claude/agents/`)
- `ha-integration-reviewer` – prüft Änderungen gegen HA-Standards/Quality Scale
- `ha-test-engineer` – schreibt/erweitert Tests
- `nibepi-protocol-researcher` – recherchiert im NibePi-Quellcode (Topics, Register, Modelle)

## Roadmap
1. Writable Register: `number` (numerisch, min/max skaliert), `select` (mit `map`), ggf. `switch` (0/1)
2. Nach Neustart Register-Liste aus Entry/Store laden und per `/get` aktiv abfragen (NibePi published nicht retained)
3. Diagnostics, Entity-Kategorien, disabled-by-default für Exoten-Register
4. Climate/Water-Heater-Abstraktion für die gängigsten Register (40004, 40013, 47011 …)
5. Brands-PR, HACS-Default-Repo
