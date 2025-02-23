# OctoPrint Xbox Controller Plugin

Ein Plugin zur Steuerung eines 3D-Druckers mit einem Xbox-Controller.

## Wichtige Information
Das Plugin ist nach der Installation sofort aktiv und läuft permanent im Hintergrund. Es sind keine zusätzlichen Aktivierungsschritte erforderlich.

## Funktionsweise

### Betriebsmodi
1. **Normaler Modus** (Standard)
   - Sendet Bewegungsbefehle direkt an den Drucker
   - Aktiv sobald ein Controller erkannt wird
   - Keine manuelle Aktivierung erforderlich

2. **Test-Modus**
   - Aktivierbar über Button im Plugin-Tab
   - Zeigt Controller-Werte in Echtzeit an
   - Simuliert Befehle ohne sie an den Drucker zu senden
   - Ausgabe der Bewegungsbefehle im Terminal

### Controller-Status
- "Controller verbunden": Bereit für Bewegungsbefehle
- "Kein Controller gefunden": Plugin aktiv, wartet auf Controller
- "Controller Modul nicht verfügbar": Xbox360Controller Modul fehlt

## Steuerung
- **Linker Stick**: X/Y-Achsen (horizontale Bewegung)
- **Rechter Stick**: Z-Achse (vertikale Bewegung)
- **Rechter Trigger**: Extruder

## Installation

1. Plugin installieren über OctoPrint Plugin Manager:
   ```
   https://github.com/goodguy1963/OctoPrint-XboxController/archive/main.zip
   ```
2. OctoPrint neustarten
3. Xbox Controller anschließen (optional, Plugin funktioniert auch ohne)

## Konfiguration

### Test-Modus Einrichtung
1. Plugin-Tab "Xbox Controller" öffnen
2. "Test-Modus" aktivieren
3. Controller-Bewegungen testen
4. Skalierungsfaktoren nach Bedarf anpassen

### Feinjustierung
- **X/Y-Skalierung**: Geschwindigkeit der horizontalen Bewegung
- **Z-Skalierung**: Präzision der Höhenverstellung
- **E-Skalierung**: Extrusionsgeschwindigkeit

## Technische Details

### Bewegungsgrenzen
- X/Y: ±10mm pro Bewegung
- Z: ±10mm pro Bewegung
- E: ±5mm pro Extrusion

### Timing
- Controller-Abfrage: 10ms
- Bewegungskommandos: max. alle 500ms
- Verbindungsversuche: alle 5 Sekunden

## Support & Fehlersuche

### Häufige Probleme
- **Keine Bewegung**: Test-Modus aktiv?
- **Kein Controller erkannt**: USB-Verbindung prüfen
- **Zu schnelle/langsame Bewegung**: Skalierungsfaktoren anpassen

### Logs
Terminal-Ausgaben im Test-Modus zeigen:
- Simulierte G-Code Befehle
- Controller-Werte in Echtzeit
- Verbindungsstatus

## Lizenz
MIT
