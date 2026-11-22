# Hardware-Test mit echtem NibePi

Ziel: v0.3.0 an deiner Wärmepumpe Schritt für Schritt prüfen – erst nur lesen, dann gezielt **ein** harmloses Register schreiben. Plane ca. 45 Minuten ein. Haken ab, was klappt; notiere bei Abweichungen, was du siehst.

> ⚠️ Schreiben verändert echte Einstellungen deiner Heizung. Schritt 6 erst machen, wenn 1–5 sauber laufen, und den Ausgangswert vorher notieren.

## 0. Vorbereitung
- [ ] Home Assistant läuft, die **MQTT-Integration** ist eingerichtet (gleicher Broker wie der NibePi)
- [ ] Backup von Home Assistant (Einstellungen → System → Backups)
- [ ] Debug-Logging ist nach der Einrichtung (Schritt 3) möglich – siehe Schritt 3

## 1. NibePi vorbereiten
In der NibePi-Oberfläche (`http://nibepi:1880/ui` bzw. IP):
- [ ] MQTT aktivieren, Broker-Adresse/Port/Benutzer eintragen
- [ ] Basis-Topic notieren (Standard `nibe/modbus/`)
- [ ] **NibePi-eigene Home-Assistant-Discovery ausschalten** (sonst doppelte Sensoren). War sie schon an: alte `sensor.nibe_*`-Entities danach in HA löschen

## 2. Prüfen, dass Daten ankommen (noch ohne Integration)
Einstellungen → Geräte & Dienste → **MQTT** → Konfigurieren → „Auf ein Topic hören“:
- [ ] Topic `nibe/modbus/+/json` eingeben → „Zuhören starten“
- [ ] Innerhalb von ~1 Minute kommen Nachrichten wie `{"register":"40004",...,"data":-3.5}`
- [ ] Notiere 2–3 Registernummern mit Wert, die du auch am Display der Pumpe siehst (z.B. 40004 Außentemperatur)

Kommt nichts: MQTT im NibePi prüfen, Broker-Log ansehen, Basis-Topic vergleichen. Erst weiter, wenn hier Daten sichtbar sind.

## 3. Integration installieren und einrichten
Über den Marketplace (HA ab 2026.11) bzw. HACS installieren, siehe [README](../README.de.md#installation), danach Home Assistant **neu starten**.

Ohne Marketplace/HACS: auf GitHub → Releases → neueste Version → „Source code (zip)“ herunterladen, den Ordner `custom_components/nibepi` nach `/config/custom_components/nibepi` kopieren (Samba-, SSH- oder File-Editor-App) und neu starten.

- [ ] Einstellungen → Geräte & Dienste: NibePi wird **automatisch gefunden** (bei Standard-Topic) → „Hinzufügen“
  - Sonst: „Integration hinzufügen“ → NibePi → Basis-Topic eintragen
- [ ] NibePi-Integration → ⋮ → **Debug-Logging aktivieren**

## 4. Lesen prüfen
- [ ] Gerät „NibePi“ erscheint; nach und nach tauchen Entities auf (jedes gemeldete Register eins)
- [ ] Die in Schritt 2 notierten Werte stimmen mit HA **und** dem Pumpendisplay überein (Faktor/Komma richtig?)
- [ ] Temperaturen haben °C, Leistungen kW/W usw.
- [ ] Register mit Wertetabelle (z.B. Betriebsart) zeigen Klartext statt Zahl
- [ ] Schreibbare Register erscheinen unter **Konfiguration** am Gerät (Number/Auswahl/Schalter), *nicht* zusätzlich als Sensor
- [ ] **Diagnose herunterladen** (Integration → ⋮) und aufheben

## 5. Neustart und Verfügbarkeit
- [ ] Home Assistant neu starten → alle NibePi-Entities sind **sofort** wieder da (erst „nicht verfügbar“), Werte füllen sich innerhalb von ~1 Minute
- [ ] Erneut Diagnose herunterladen: `registers_without_value` sollte (fast) leer sein
- [ ] NibePi neu starten (über seine UI) → Entities werden „nicht verfügbar“ und kommen nach dem Neustart des NibePi von selbst zurück
  - Hinweis: Der Last Will kommt nur bei *unerwartetem* Verbindungsabbruch; bei sauberem Neustart werden Entities evtl. gar nicht unavailable – beides notieren

## 6. Schreiben – ein harmloses Register
Wähle **ein** Register, dessen Wirkung du kennst und das sofort zurückgestellt werden kann, z.B. einen Komfort-Sollwert oder eine Kurvenverschiebung um eine Stufe.

**Nicht** zum Testen verwenden: Betriebsart, Zusatzheizung, Legionellen/Warmwasser-Programme, Kompressor-, Pumpen- oder Frostschutzeinstellungen.

- [ ] Ausgangswert am Pumpendisplay **und** in HA notieren
- [ ] In HA um **eine Stufe** ändern
- [ ] Nach einigen Sekunden zeigt HA den neuen Wert (NibePi liest zurück) **und** das Pumpendisplay ebenfalls
- [ ] Wieder auf den Ausgangswert stellen und beides erneut prüfen
- [ ] Optional bei einem Schalter: einmal an, einmal aus, jeweils am Display prüfen

Wird der Wert in HA gesetzt, springt aber zurück: NibePi hat abgelehnt (steht nur im NibePi-Log, nicht in HA). Diagnose + NibePi-Log sichern.

## 7. Ergebnis zurückmelden
Für die Auswertung brauche ich:
- Welche Schritte geklappt haben / was abwich (kurz)
- Pumpenmodell und NibePi-Version
- Die beiden Diagnose-Dateien (Schritt 4 und 5)
- Bei Fehlern: Einstellungen → System → Protokolle, nach `nibepi` filtern, Auszug kopieren

Danach Debug-Logging wieder ausschalten (Integration → ⋮).

Klappt alles: Pre-Release-Status aufheben
```
gh release edit v0.3.0 --repo Ulle80/nibepi-homeassistant --prerelease=false
```
