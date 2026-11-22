# NibePi for Home Assistant

**English** · [Deutsch](README.de.md)

A custom integration (HACS) that brings a [NibePi](https://github.com/anerdins/nibepi) into Home Assistant over **MQTT**. NibePi is a Raspberry Pi connected to the RS485/Modbus port of a NIBE F-series heat pump. You get one device with stable unique IDs, proper device classes, and availability based on NibePi's last will.

> Status: **early** (v0.5.0). Tested on a NIBE F1145 and checked against all NibePi model files.

## Features
- **Automatic discovery** of a NibePi on the default topic `nibe/modbus/`, or manual setup with your own topic.
- **All registers NibePi publishes**, created automatically as they appear:

  | Register | Entity |
  |---|---|
  | read-only | Sensor (enum sensor if the register has a value table) |
  | writable, with value table | Select |
  | writable, 0/1 without unit | Switch |
  | writable, other | Number (limits and step taken from the register) |

- **Safe writing.** NibePi only accepts numbers and truncates them. The integration encodes every value so NibePi stores exactly what you chose. Values NibePi cannot store exactly are rejected with an error message.
- **Writable registers start disabled.** They appear as configuration entities on the device. Only common comfort settings are enabled out of the box: heating curve, curve offset, room setpoint, hot water comfort mode and Temporary Lux. Enable anything else (operating mode, degree minutes, pump speeds, additional heater …) yourself under Device → Entities.
- **Sensors that are not connected are hidden.** NibePi reports sensors of accessories you do not have, such as the supply temperature of a second climate system, with a placeholder value. The integration disables these sensors automatically. If one delivers real values later, it is enabled again. A sensor that has delivered values before stays visible (as unavailable), so a broken sensor does not go unnoticed. Entities you enable or disable yourself are left alone.
- **Pump model on the device.** NibePi does not publish its model, so the integration compares the registers it receives with NibePi's model files. The model is shown once only one model fits, e.g. "F1145 / F1245". Models with identical model files cannot be told apart. You can also set the model under **Configure**. The model is for display and diagnostics only; NibePi decides which entities exist.
- **Value labels in your language.** States such as operating mode, alarms or pump status are shown in English, German, Swedish, Danish or Norwegian. Many come from NibePi in Swedish. Set the language under **Configure**; the default is the Home Assistant language, or Norwegian if it is not supported. Entity names stay in English, as NibePi provides them.
- **Survives restarts.** NibePi does not publish retained messages. The integration remembers all known registers, recreates their entities immediately after a restart and requests current values from NibePi. Until a value arrives, an entity shows as unavailable.
- **Diagnostics** for troubleshooting (see below).

## Requirements
- A NibePi with MQTT enabled (Node-RED UI → settings). Note the base topic (default `nibe/modbus/`).
- NibePi's own Home Assistant discovery **turned off**, otherwise you get duplicate sensors.
- Home Assistant 2025.8 or newer with the [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) set up on the same broker.

## Installation (HACS)
1. HACS → ⋮ → Custom repositories → `https://github.com/Ulle80/nibepi-homeassistant`, type *Integration*.
2. Install "NibePi" and restart Home Assistant.
3. Settings → Devices & services: NibePi is discovered automatically on the default topic. Otherwise use "Add integration" → NibePi.

## Configuration
Settings → Devices & services → NibePi → **Configure**:
- **Language of value labels**: Automatic, English, Deutsch, Svenska, Dansk, Norsk.
- **Pump model**: Automatic (detected from the registers) or a fixed NIBE model.

## First test with real hardware
Step-by-step checklist (German): [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md)

## Troubleshooting
Settings → Devices & services → NibePi → ⋮ → **Download diagnostics**. The file contains the configuration, availability, the detected model, hidden sensors and all known registers with definition, entity type and current value. It contains no passwords; those are stored in the MQTT integration. Please attach it to issues.

## Removal
Settings → Devices & services → NibePi → Delete, then uninstall it in HACS.

## Development
See [CLAUDE.md](CLAUDE.md) and [docs/NIBEPI_PROTOCOL.md](docs/NIBEPI_PROTOCOL.md) (German).

```bash
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```
The easiest way is the dev container (VS Code → "Reopen in Container").

## Credits
Register data per model comes from [anerdins/nibepi](https://github.com/anerdins/nibepi) (MIT licence). Not affiliated with NIBE.
