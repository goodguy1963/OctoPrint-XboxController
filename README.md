# OctoPrint Xbox Controller Plugin

Ein umfassendes Plugin zur präzisen Steuerung eines 3D-Druckers mit einem Xbox-Controller.

## Features & Funktionsweise

### Grundlegende Funktionen
- **Echtzeit-Steuerung**: Direktes Mapping von Controller-Eingaben zu Druckerbewegungen
- **Achsensteuerung**:
  - Linker Stick: X/Y-Achsen Bewegung
  - Rechter Stick (vertikal): Z-Achsen Bewegung
  - Rechter Trigger: Extruder-Steuerung

### Plugin-Modi

#### Normaler Betriebsmodus
- Sendet G-Code-Befehle direkt an den Drucker
- Relative Bewegungen (G91) für präzise Steuerung
- Automatische Rückkehr zum absoluten Positionierungsmodus (G90) nach jeder Bewegung

#### Test-Modus
- Aktivierbar über Button im Plugin-Tab
- Zeigt Controller-Werte in Echtzeit an, ohne Befehle an den Drucker zu senden
- Alle Bewegungen werden im Terminal protokolliert
- Ideal zur Kalibrierung und zum Testen der Steuerung

### Sicherheitsfunktionen
- Bewegungsbegrenzung durch konfigurierbare Grenzwerte
  - X/Y: -10mm bis +10mm pro Bewegung
  - Z: -10mm bis +10mm pro Bewegung
  - E: -5mm bis +5mm pro Extrudierung
- Automatische Wiederverbindungsversuche bei Verbindungsverlust
- Fehlertolerante Ausführung mit detailliertem Logging

## Installation

### Voraussetzungen
- OctoPrint Version 1.3.0 oder höher
- Python 3.6 oder höher
- Installiertes `xbox360controller` Modul
- Kompatible Xbox-Controller Hardware

### Installationsschritte
1. Installation über den OctoPrint Plugin Manager:
   ```
   https://github.com/goodguy1963/OctoPrint-XboxController/archive/main.zip
   ```
2. Server-Neustart nach Installation
3. Plugin in OctoPrint-Einstellungen aktivieren

### Konfiguration

#### Grundeinstellung
1. Plugin-Tab "Xbox Controller" öffnen
2. Test-Modus aktivieren für erste Einrichtung
3. Bewegungswerte in Echtzeit überprüfen

#### Achsen-Kalibrierung
- **X/Y-Skalierung**: Beeinflusst Geschwindigkeit der horizontalen Bewegung
- **Z-Skalierung**: Steuert Präzision der Höhenverstellung
- **E-Skalierung**: Reguliert Extrusionsgeschwindigkeit

### Fehlerbehebung

#### Status-Meldungen
- "Controller verbunden": Erfolgreiche Verbindung
- "Kein Controller gefunden": Gerät nicht erkannt
- "Controller Modul nicht verfügbar": Software-Abhängigkeit fehlt

#### Bekannte Probleme
- Plugin startet im deaktivierten Zustand: Neustart von OctoPrint erforderlich
- Keine Bewegung trotz Verbindung: Test-Modus prüfen
- Verzögerte Reaktion: Skalierungsfaktoren anpassen

### Technische Details

#### G-Code Implementierung
- Verwendet relativen Bewegungsmodus (G91)
- Standardformat: `G91\nG1 X{x} Y{y} Z{z} E{e}\nG90`
- Automatische Normalisierung der Controller-Werte

#### Ereignisverarbeitung
- Controller-Abfrage alle 0.01 Sekunden
- Bewegungsbefehle maximal alle 0.5 Sekunden
- Automatische Wiederverbindung alle 5 Sekunden bei Verbindungsverlust

## Support

- GitHub Issues für Fehlermeldungen
- Logs prüfen unter OctoPrint-Einstellungen -> Logging

## Lizenz

Veröffentlicht unter der MIT-Lizenz
