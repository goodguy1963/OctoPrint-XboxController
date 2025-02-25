# OctoPrint Xbox Controller Plugin

Dieses Plugin ermöglicht die Steuerung eines 3D-Druckers mit einem Xbox-Controller über OctoPrint.

## Installation

1. Installieren Sie das Plugin über den OctoPrint Plugin Manager:
   - Gehen Sie zu Einstellungen > Plugin Manager > Weitere Plugins durchsuchen
   - Fügen Sie diese URL ein:
     ```https://github.com/goodguy1963/OctoPrint-XboxController/archive/main.zip
     ```
   - Klicken Sie auf "Installieren"

2. Alternativ können Sie das Plugin auch direkt über den Plugin Manager installieren, wenn es im offiziellen Repository verfügbar ist.

3. Starten Sie OctoPrint neu

4. Schließen Sie einen Xbox-Controller an Ihren Raspberry Pi / Computer an

## Funktionen

- Steuerung der Druckerbewegungen (X, Y, Z) mit dem Xbox-Controller
- Steuerung des Extruders mit dem linken Joystick
- Variable Bewegungsgeschwindigkeit basierend auf der Joystick-Position (max. 10mm)
- Einfache Konfiguration über die OctoPrint-Oberfläche
- Testmodus zur Überprüfung der Controller-Eingaben

## Voraussetzungen

- OctoPrint 1.3.0 oder höher
- Python 3
- Pygame-Bibliothek (wird automatisch installiert)

## Controller-Belegung

### Bewegungssteuerung
- **Rechter Joystick**: X/Y-Achsen-Bewegung
  - Links/Rechts: X-Achse
  - Vor/Zurück: Y-Achse
- **Trigger-Tasten**: Z-Achsen-Bewegung
  - Rechter Trigger (RT): Z-Achse nach oben
  - Linker Trigger (LT): Z-Achse nach unten
- **Linker Joystick**: Extruder-Steuerung
  - Links/Rechts: Filament zurückziehen/extrudieren

### Tasten
- **A-Taste**: Home X/Y-Achsen
- **B-Taste**: Vollständiger Autohome (X, Y, Z)

## Konfiguration

Im Einstellungsbereich des Plugins können Sie folgende Parameter anpassen:

- XY-Skalierungsfaktor: Beeinflusst die Empfindlichkeit der X/Y-Bewegung
- Z-Skalierungsfaktor: Beeinflusst die Empfindlichkeit der Z-Bewegung
- E-Skalierungsfaktor: Beeinflusst die Empfindlichkeit der Extruder-Bewegung

## Testmodus

Der Testmodus kann über den Tab "Xbox Controller" aktiviert werden. In diesem Modus werden die Controller-Eingaben angezeigt, ohne dass tatsächliche Bewegungsbefehle an den Drucker gesendet werden.

## Fehlerbehebung

- **Controller wird nicht erkannt**: Stellen Sie sicher, dass der Controller korrekt angeschlossen ist und von Ihrem System erkannt wird.
- **Unerwartete Bewegungen**: Überprüfen Sie die Joystick-Kalibrierung und passen Sie die Skalierungsfaktoren an.
- **Plugin startet nicht**: Überprüfen Sie die OctoPrint-Logs auf Fehlermeldungen.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.
