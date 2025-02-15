# coding=utf-8
import time
import threading
import os
import logging

import octoprint.plugin
import flask

# Versuche, das xbox360controller-Modul zu importieren
try:
    from xbox360controller import XboxController
except ImportError:
    XboxController = None
    logging.error("Das Modul 'xbox360controller' ist nicht installiert.")


################################################################
# Controller Handler Klasse
################################################################
class XboxControllerHandler:
    def __init__(self, send_gcode_callback, settings):
        self.send_gcode = send_gcode_callback
        self.settings = settings

        self.controller = None
        self.running = False
        self.thread = None
        self._last_sent_time = 0

        # Lade Skalierungsfaktoren aus den Plugin-Einstellungen
        self.xy_scale_factor = self.settings.get_int(["xy_scale_factor"], 150)
        self.e_scale_factor = self.settings.get_int(["e_scale_factor"], 150)
        self.z_scale_factor = self.settings.get_int(["z_scale_factor"], 150)
        self.max_z = self.settings.get_int(["max_z"], 100)
        self.current_z = 0

    def init_controller(self):
        if XboxController is None:
            logging.error("xbox360controller-Modul nicht verfügbar.")
            return
        try:
            self.controller = XboxController()
            logging.info("Xbox-Controller erfolgreich initialisiert.")
        except Exception as e:
            logging.error("Fehler bei der Controller-Initialisierung: %s", e)
            self.controller = None

    def _clamp(self, value, min_val, max_val):
        return max(min(value, max_val), min_val)

    def read_controller(self):
        if not self.controller:
            return None

        # Lese relevante Achsen:
        x = self.controller.get_axis(3)  # Rechte Joystick X
        y = self.controller.get_axis(4)  # Rechte Joystick Y
        e = self.controller.get_axis(0)  # Linker Joystick
        lt = self.controller.get_axis(2) # Linker Trigger
        rt = self.controller.get_axis(5) # Rechter Trigger

        # Nutze Trigger als Geschwindigkeitsfaktor (0.1 bis 2.0)
        trigger_value = max(lt, rt)
        speed_factor = 0.1 + trigger_value * 1.9

        movement = {
            "x": x * speed_factor,
            "y": y * speed_factor,
            "z": 0.0,  # Erweiterbar: separate Logik für Z-Achse möglich
            "e": e * speed_factor,
        }
        return movement

    def send_relative_command(self, movement):
        # Werte auf voreingestellte Bereiche beschränken:
        x_val = self._clamp(movement["x"], -10, 10)
        y_val = self._clamp(movement["y"], -10, 10)
        z_val = self._clamp(movement["z"], -10, 10)
        e_val = self._clamp(movement["e"], -5, 5)
        # Erstelle den G-Code-Befehl im relativen Modus (G91)
        gcode = "G91\nG1 X{:.1f} Y{:.1f} Z{:.1f} E{:.1f}\nG90".format(
            x_val, y_val, z_val, e_val
        )
        self.send_gcode(gcode)

    def update_loop(self):
        while self.running:
            if self.controller is None:
                self.init_controller()
                time.sleep(1)
                continue

            now = time.time()
            if now - self._last_sent_time >= 0.5:
                movement = self.read_controller()
                if movement:
                    self.send_relative_command(movement)
                self._last_sent_time = now
            time.sleep(0.01)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.update_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


################################################################
# Haupt-Plugin Klasse
################################################################
class XboxControllerPlugin(octoprint.plugin.StartupPlugin,
                           octoprint.plugin.ShutdownPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self._controller_handler = None

    ## StartupPlugin: Wird nach dem Start von OctoPrint aufgerufen
    def on_after_startup(self):
        self._logger.info("Starte Xbox Controller Plugin")
        self._controller_handler = XboxControllerHandler(self._send_gcode, self._settings)
        self._controller_handler.start()

    ## ShutdownPlugin: Wird beim Herunterfahren von OctoPrint aufgerufen
    def on_shutdown(self):
        if self._controller_handler:
            self._controller_handler.stop()

    ## SettingsPlugin: Standard-Einstellungen für das Plugin
    def get_settings_defaults(self):
        return dict(
            xy_scale_factor=150,
            e_scale_factor=150,
            z_scale_factor=150,
            max_z=100
        )

    ## API Plugin: Definiert einfache API-Befehle (z.B. für Aufnahme/Wiedergabe)
    def get_api_commands(self):
        return dict(
            start_recording=[],
            stop_recording=[],
            playback_recording=["index"]
        )

    def on_api_command(self, command, data):
        # Beispielhafte Implementierung – hier können Funktionen erweitert werden
        if command == "start_recording":
            self._logger.info("Recording gestartet")
            return flask.jsonify(dict(success=True))
        elif command == "stop_recording":
            self._logger.info("Recording gestoppt")
            return flask.jsonify(dict(success=True))
        elif command == "playback_recording":
            index = data.get("index")
            self._logger.info("Wiedergabe Recording index: %s", index)
            return flask.jsonify(dict(success=True))
        else:
            return flask.make_response("Unbekannter Befehl", 400)

    def _send_gcode(self, command):
        # Nutzt die OctoPrint-Drucker-Schnittstelle, um G-Code zu senden.
        self._printer.commands(command)

__plugin_name__ = "Xbox Controller Plugin"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()

def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation__
