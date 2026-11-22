# NibePi – MQTT-Schnittstelle (Recherche)

Quelle: [anerdins/nibepi](https://github.com/anerdins/nibepi) (`index.js`, `default.json`, `models/*.json`), Stand master Okt. 2023 (Projekt seitdem ruhend). MIT-Lizenz.

## Was NibePi ist
Raspberry Pi Zero W + RS485-HAT, eingebaut in die Pumpe, spricht Modbus über RS485 mit NIBE **F-Serie** (F370, F470, F730, F750, F1145/F1155, F1245/F1255, F1345/F1355, VVM225/310/320/325/500, SMO20/40). Software: Node.js + Node-RED (UI auf Port 1880). Modbus muss an der Pumpe in Menü 5.2 aktiviert sein.

## MQTT
Default in `default.json`: `"topic": "nibe/modbus/"`, MQTT standardmäßig **aus** (in der NibePi-UI aktivieren).

Pro Register (bei jeder Wertänderung, `retain: false`):

| Topic | Inhalt |
|---|---|
| `<base><reg>` | skalierter Wert als Text (z.B. `-3.5`) oder Map-Label (z.B. `CHEAP`) |
| `<base><reg>/raw` | Rohwert (Integer, z.B. `-35`) |
| `<base><reg>/json` | komplettes Register-Objekt inkl. Metadaten |

`/json` Beispiel:
```json
{"register":"40004","factor":10,"size":"s16","mode":"R","titel":"BT1 Outdoor Temperature",
 "info":"Current outdoor temperature","unit":"°C","min":"-500","max":"500",
 "data":-3.5,"raw_data":-35,"timestamp":1732272000000}
```
- `mode`: `R` oder `R/W` → schreibbar
- `min`/`max`: **unskaliert**, `0/0` = kein Bereich
- optional `map`: `[{"0":"UNKNOWN"},{"1":"CHEAP"},...]`
- Werte außerhalb min/max werden als CORRUPT verworfen (nicht publiziert)

### Eingehende Befehle (NibePi abonniert `<base>#`)
| Topic | Wirkung |
|---|---|
| `<base><reg>/set` + Payload | Wert schreiben (Anzeigeeinheit, NibePi multipliziert mit `factor`, prüft min/max und `R/W`) |
| `<base><reg>/get` | Register sofort lesen |
| `<base><reg>/add` | Register zur Polling-Liste hinzufügen |
| `<base><reg>/remove` | Register aus Polling-Liste entfernen |

### Schreib-Semantik (`setData`/`setDataValue` in index.js)
- Payload wird **nicht** geparst, sondern implizit per `payload * factor` (JS) zu einer Zahl. Nicht-numerisch → `NaN` → wird vermutlich als **0** geschrieben (kein Reject!). → Nur Zahlen senden; bei `map`-Registern den **Schlüssel** (`"1"`), nie das Label. Schalter: `"1"`/`"0"`, nie `on`/`true`.
- Ergebnis wird **abgeschnitten**, nicht gerundet (Bitmasken). `4.35 * 100 = 434.99999…` → 434. Die Integration kodiert deshalb in `NibeRegister.encode_value()` so, dass die Trunkierung exakt den Zielwert trifft.
- min/max-Prüfung auf dem **skalierten** Wert gegen die rohen min/max. Außerhalb → geklemmt, als corrupt markiert und **nicht** gesendet. HA muss die Grenzen also selbst durchsetzen.
- Schreibbar nur bei exakt `mode == "R/W"`; RMU-Schattenregister werden zur Laufzeit auf `R` gezwungen.
- Nach erfolgreichem Senden: `reqData(address)` → Register wird zurückgelesen und über die normalen drei Topics publiziert (sofort, oder beim nächsten Poll, wenn es ohnehin gepollt wird).
- **Kein** Ack/Fehler per MQTT. Ablehnungen landen nur im NibePi-Log.
- 0/1-Register mit R/W, z.B. F750 `40881–40888` „=+Adjust Affect system1..8“ (u8, min 0, max 1).

### Verfügbarkeit
Kein Availability-Topic. Last Will ist **hart kodiert** auf Topic `nibe` (nicht unter base!), Payload `nibe_<8hex> disconnected`, nicht retained.

### Eingebaute HA-Discovery (optional, `config.mqtt.discovery`)
Publiziert `homeassistant/sensor/<reg>/config` – nur Sensoren, **ohne** `unique_id`, `device`, `availability`. Grund für diese Integration. Wer diese Integration nutzt, sollte die NibePi-Discovery **ausschalten**, sonst gibt es Dubletten.

## Konsequenzen fürs Design
- Register sind nicht vorab bekannt → Entities werden **dynamisch** beim ersten `/json` angelegt.
- Kein retain → nach HA-Neustart wären Entities erst beim nächsten Publish da. Umgesetzt: Register-Definitionen werden im HA-Store gespeichert, nach dem Start sofort als Entities angelegt (unavailable bis Wert da) und per `<base><reg>/get` abgefragt, alle 0,25 s eins (jede Abfrage = ein RS485-Read). Für Register, die NibePi ohnehin pollt, wartet NibePi auf den nächsten Broadcast statt aktiv zu lesen.
- Geräte-ID: NibePi publiziert keine Seriennummer per MQTT → Unique-ID = Basis-Topic.
