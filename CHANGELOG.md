# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).

## [0.3.0] – 2026-11-22

Erstes Release. **Noch nicht gegen echte NibePi-Hardware getestet.**

### Hinzugefügt
- Einrichtung über die UI, inkl. automatischer Erkennung per MQTT beim Standard-Topic `nibe/modbus/`
- Entities werden dynamisch angelegt, sobald NibePi ein Register meldet – ein Gerät, stabile Unique-IDs
- Nur lesbare Register → Sensoren mit passender Geräteklasse/Einheit; Register mit Wertetabelle → Auswahl-Sensor
- Schreibbare Register → Number (Grenzen/Schrittweite aus dem Register), Select (Wertetabelle) oder Switch (0/1)
- Verfügbarkeit über den NibePi-Last-Will; nach einem Last Will wird das eigene Gerät aktiv angepingt (das LWT-Topic ist bei allen NibePis gleich)
- Nach einem HA-Neustart sind alle bekannten Entities sofort da; Werte werden gedrosselt per `/get` abgefragt
- Geänderte Registerdefinitionen werden übernommen und die Entities neu aufgebaut
- Diagnose-Download
- Deutsch und Englisch

### Bekannte Eigenheiten von NibePi (abgefangen)
- NibePi schreibt nur Zahlen und schneidet `Wert × Faktor` ab: Werte werden so kodiert, dass exakt der gewünschte Wert ankommt
- Werte, die NibePi prinzipiell nicht exakt speichern kann (z.B. 4.35 bei Maximum 435/Faktor 100), werden mit Fehlermeldung abgelehnt statt falsch geschrieben
- NibePi meldet abgelehnte Schreibvorgänge nicht per MQTT

### Bekannte Einschränkungen
- Register, die NibePi nicht mehr liefert, bleiben als „nicht verfügbar“ bestehen
- Automatische Erkennung nur für das Standard-Basis-Topic; sonst manuell einrichten
- NibePi-eigene HA-Discovery bitte abschalten, sonst doppelte Sensoren

[0.3.0]: https://github.com/Ulle80/nibepi-homeassistant/releases/tag/v0.3.0
