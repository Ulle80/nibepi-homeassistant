# CLAUDE.md – NibePi Home Assistant Integration

## Ziel
Custom-Integration `nibepi` für den HA-Marketplace (ab 2026.11, vorher HACS; braucht weiterhin `hacs.json`) für [anerdins/nibepi](https://github.com/anerdins/nibepi) (RPi + RS485 an NIBE F-Serie). Kommunikation ausschließlich über HAs MQTT-Integration (`dependencies: ["mqtt"]`), `iot_class: local_push`. Protokolldetails: `docs/NIBEPI_PROTOCOL.md` – vor Änderungen an Topics/Parsing lesen.

## Architektur
- `models.py` – reines Python, **keine HA-Imports**. Parsing der `/json`-Payloads → `NibeRegister`. Soll später als eigene PyPI-Lib ausgelagert werden können (Core-Pflicht).
- `hub.py` – `NibePiHub`: abonniert `<base>+/json` und LWT-Topic, hält `registers`, sendet Dispatcher-Signale (`SIGNAL_NEW_REGISTER`, `SIGNAL_REGISTER_UPDATE`, `SIGNAL_AVAILABILITY`), schreibt via `<base><reg>/set`.
- `entity.py` – `NibePiEntity`-Basis (has_entity_name, unique_id `<entry_id>_<register>`, DeviceInfo).
- Plattformen legen Entities **dynamisch** an, wenn ein neues Register auftaucht (`async_setup_register_platform`). `NibeRegister.kind` entscheidet: nur lesbar → `sensor`; R/W mit `map` → `select`; R/W, factor 1, 0..1, ohne Einheit → `switch`; sonst R/W → `number`. Jedes Register erzeugt genau eine Entity.
- Schreiben immer über `NibeRegister.encode_value()` / `key_for_label()` – NibePi akzeptiert nur Zahlen, schneidet ab und verwirft Werte über max. Nicht exakt kodierbare Werte (z.B. 4.35 bei max 435/factor 100) → `UnencodableValueError` → übersetzte `ServiceValidationError`.
- Ändert sich die Definition eines bekannten Registers, wird sie übernommen, gespeichert und der Entry einmal neu geladen. Wechselt dabei der Entity-Typ, entfernt der Hub die alte Registry-Entity.
- Wertetabellen: `map` aus der Modelldatei, sonst aus `info` geparst (`_mapping_from_info`, nur factor 1; bei schreibbaren Registern nur, wenn min und max als Schlüssel vorkommen). NibePi sendet dann Zahlen statt Labels → immer `current_label` nutzen.
- Fehlender Fühler = kleinster Wert des signed-Typs (z.B. −32768) → `value = None`.
- Zähler (`is_counter`): read-only, s32/u32, min 0/None → `total_increasing`.
- Schreibbare Entities standardmäßig deaktiviert außer `COMFORT_REGISTERS` (const.py).
- Sprache der Wertebezeichnungen: `labels.py` (HA-frei, Tabelle en/de/sv/da/nb, Fallback nb). Entities zeigen `translate(label)`, Select schreibt über `_original_label` → `key_for_label`. Optionen per `OptionsFlowWithReload` – **kein** Update-Listener: der würde bei jeder MQTT-Discovery-Nachricht feuern (HA speichert discovery_keys am Entry) und die Integration endlos neu laden.
- Neue Labels aus Modelldateien → `_ROWS`/`_ALIASES` in labels.py ergänzen; `tests/test_labels.py` listet alle schwedischen Labels.
- Pumpenmodell: `pump_models.py` (HA-frei) gleicht die gesehenen Register mit `pump_model_data.py` ab (generiert per `scripts/generate_pump_models.py` aus NibePis `models/*.json`). Modell nur, wenn genau eine Modelldatei alle Register enthält; RMU40-Register zählen nicht. Optional fest gewählt (`CONF_MODEL`). **Nur Anzeige** (DeviceInfo, Diagnose) – keine Entities vom Modell abhängig machen.
- Nicht angeschlossene Fühler (`NibeRegister.not_connected`): Sensor-Entities, die nie einen echten Wert hatten, deaktiviert der Hub (`disabled_by=INTEGRATION`, neue Entities starten deaktiviert); echter Wert → wieder aktiviert. Store merkt `connected` und `hidden_not_connected`, damit jede Entity nur einmal ausgeblendet wird und Nutzerentscheidungen bleiben.
- Echte Testdaten: F1145 mit 102 Registern (siehe Tests `test_real_world_registers`, `test_mapping_from_info`).
- Last Will `nibe` ist bei allen NibePis gleich → nach einem LWT wird das eigene Gerät per `/get` angepingt.
- Unload: erst `hub.async_stop()` (MQTT ab), dann Plattformen, dann `async_save()`. Setup-Fehler nach dem Forwarding rollt die Plattformen zurück.

## Test-Konventionen
- Kein pauschales `expected_lingering_timers`: `conftest.cancel_mqtt_misc_timer` beendet gezielt nur HAs MQTT-Timer.
- Hintergrund-Tasks des Hubs: `await hass.async_block_till_done(wait_background_tasks=True)`.
- `entry.runtime_data` = Hub (typisiert über `NibePiConfigEntry`).
- Neustart: NibePi published nicht retained. Der Hub speichert Register-**Definitionen** (keine Werte) im HA-Store `nibepi.<entry_id>` (verzögert bei neuen Registern, sofort beim Unload), stellt sie beim Start wieder her und fragt fehlende Werte gedrosselt per `<base><reg>/get` ab (`REFRESH_REQUEST_DELAY`). `async_remove_entry` löscht den Store.

## Standards (verbindlich)
- [HA Developer Docs](https://developers.home-assistant.io/) + [Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/). Fortschritt in `custom_components/nibepi/quality_scale.yaml` pflegen; Ziel: Silver, dann Gold.
- Alles async, keine blockierenden Calls im Event-Loop.
- UI-Texte nur über `strings.json`; `translations/en.json` = Kopie von `strings.json`, `de.json` mitpflegen.
- Kein YAML-Setup, nur Config Flow.
- Jede Änderung mit Tests (`pytest-homeassistant-custom-component`), Config Flow 100 % Coverage.
- `ruff check` + `ruff format` müssen sauber sein. Typ-Hints überall.
- README.md englisch, README.de.md deutsch – beide pflegen.
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

## Releases
Marketplace/HACS installiert **Releases**, nicht `main`. Änderungen kommen beim Nutzer erst an mit: Version in `manifest.json` + `pyproject.toml` erhöhen, CHANGELOG-Abschnitt, Commit, CI grün, dann `gh release create vX.Y.Z --target <volle SHA> --notes-file …`.

## Roadmap
1. ~~Writable Register: `number`, `select`, `switch`~~ (erledigt, v0.2.0)
2. ~~Nach Neustart Register aus Store laden und per `/get` abfragen~~ (erledigt, v0.3.0)
   - Offen: Register, die NibePi nicht mehr liefert (Modellwechsel), aufräumen → `stale-devices`/Entity-Removal
3. ~~Diagnostics~~ (erledigt), ~~Entity-Kategorien~~ (erledigt), ~~nicht angeschlossene Fühler ausblenden~~ (erledigt, v0.5.0)
4. Climate/Water-Heater-Abstraktion für die gängigsten Register (40004, 40013, 47011 …)
5. Brands-PR, Aufnahme in den Marketplace-Katalog (früher HACS-Default)
