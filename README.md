# OctoPrint Xbox Controller Plugin

Dieses Plugin ermöglicht die Steuerung eines 3D-Druckers über einen Xbox-Controller in OctoPrint.

## Funktionen

- Steuerung der Achsen X, Y, Z sowie des Extruders mittels eines Xbox-Controllers
- Konfigurierbare Skalierungsfaktoren für präzise Steuerung

## Installation

1. Lade das Plugin als ZIP herunter oder klone das Repository.
2. Installiere das Plugin über den OctoPrint Plugin Manager.
3. Konfiguriere das Plugin in den OctoPrint-Einstellungen.
4. Alternativ kann das Plugin auch direkt über diese URL im OctoPrint Plugin Manager installiert werden:
   ```
   https://github.com/goodguy1963/OctoPrint-XboxController/archive/main.zip
   ```

## Plugin Aktivierung und Verhalten
- Sobald das Plugin in den Einstellungen aktiviert wird, versucht es eine Verbindung zum Xbox-Controller herzustellen.
- Bei erfolgreicher Aktivierung und erkanntem Controller können direkt G-Code-Befehle an den Drucker gesendet werden, sofern der Testmodus deaktiviert ist.
- Ist das Plugin deaktiviert, werden keine G-Code-Befehle gesendet und die Steuerung ist nicht aktiv.
- Sobald die Einstellungen gespeichert werden, startet das Plugin automatisch oder stoppt je nach gesetztem Status.

## Usage

Das Xbox Controller Plugin bietet folgende Funktionen:
- Test-Modus zum virtuellen Senden von Befehlen.
- Live-Kalibrierung der Achsenskalierung über Schieberegler.

### Controller-Kalibrierung

1. Aktiviere das Plugin in den Einstellungen.
2. Wechsle in den Tab "Xbox Controller".
3. Aktiviere den Test-Modus und beobachte die aktuellen Werte.
4. Passe die Skalierungsfaktoren für X/Y, Z und E-Achsen an, um die Bewegung zu verfeinern.

### Hinweis

Stelle sicher, dass das xbox360controller-Modul installiert ist, damit der Controller erkannt wird.
