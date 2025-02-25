# coding=utf-8
import time
import threading
import os
import logging

import octoprint.plugin
import flask
import pygame

################################################################
# Haupt-Plugin Klasse
################################################################
class XboxControllerPlugin(octoprint.plugin.StartupPlugin,
                           octoprint.plugin.ShutdownPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self._identifier = "xbox_controller"
        self.controller_thread = None
        self.controller_running = False
        self.test_mode = False
        self.xy_scale_factor = 150
        self.z_scale_factor = 150
        self.e_scale_factor = 150

    def get_template_configs(self):
        return [
            dict(type="tab", name="Xbox Controller", custom_bindings=True),
            dict(type="settings", name="Xbox Controller", custom_bindings=True)
        ]

    def get_assets(self):
        return dict(
            js=["js/xbox_controller.js"],
            css=["css/xbox_controller.css"]
        )

    def get_settings_defaults(self):
        return dict(
            xy_scale_factor=150,
            e_scale_factor=150,
            z_scale_factor=150,
            max_z=100
        )

    def on_api_command(self, command, data):
        if command == "toggleTestMode":
            self.test_mode = bool(data.get("enabled", False))
        elif command == "updateScaleFactor":
            axis = data.get("axis")
            value = int(data.get("value", 150))
            
            if axis == "xy":
                self.xy_scale_factor = value
            elif axis == "z":
                self.z_scale_factor = value
            elif axis == "e":
                self.e_scale_factor = value
                
            self._settings.save()
            return flask.jsonify(success=True)

    def update_status(self, status):
        self._plugin_manager.send_plugin_message(
            self._identifier,
            dict(type="status", status=status)
        )

    ## StartupPlugin: Wird nach dem Start von OctoPrint aufgerufen
    def on_after_startup(self):
        self._logger.info("Xbox Controller Plugin gestartet")
        self._logger.info("Überprüfe Template-Konfiguration...")
        self._logger.info("Template-Configs: %s", self.get_template_configs())
        self._logger.info("Asset-Configs: %s", self.get_assets())
        
        self.xy_scale_factor = self._settings.get_int(["xy_scale_factor"], 150)
        self.z_scale_factor = self._settings.get_int(["z_scale_factor"], 150)
        self.e_scale_factor = self._settings.get_int(["e_scale_factor"], 150)
        self.start_controller_thread()

    ## ShutdownPlugin: Wird beim Herunterfahren von OctoPrint aufgerufen
    def on_shutdown(self):
        self.controller_running = False
        if self.controller_thread is not None:
            self.controller_thread.join(timeout=1.0)

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.xy_scale_factor = self._settings.get_int(["xy_scale_factor"], 150)
        self.z_scale_factor = self._settings.get_int(["z_scale_factor"], 150)
        self.e_scale_factor = self._settings.get_int(["e_scale_factor"], 150)

    def start_controller_thread(self):
        if self.controller_thread is not None and self.controller_thread.is_alive():
            return
        
        self.controller_running = True
        self.controller_thread = threading.Thread(target=self.controller_worker)
        self.controller_thread.daemon = True
        self.controller_thread.start()
    
    def controller_worker(self):
        try:
            pygame.init()
            pygame.joystick.init()
            
            # Warte auf Controller-Verbindung
            while self.controller_running:
                joystick_count = pygame.joystick.get_count()
                if joystick_count > 0:
                    break
                self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Warte auf Controller..."})
                time.sleep(1)
            
            if not self.controller_running:
                return
            
            # Controller initialisieren
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Verbunden: " + joystick.get_name()})
            
            # Hauptschleife
            while self.controller_running:
                pygame.event.pump()
                
                # Joystick-Werte auslesen
                left_x = joystick.get_axis(0)  # Linker Joystick X-Achse für Extruder
                left_y = -joystick.get_axis(1)  # Y-Achse invertieren
                right_x = joystick.get_axis(2)  # Rechter Joystick X-Achse
                right_y = -joystick.get_axis(3)  # Y-Achse invertieren
                
                # Trigger-Werte auslesen (können je nach Controller unterschiedlich sein)
                try:
                    left_trigger = joystick.get_axis(4) if joystick.get_numaxes() > 4 else 0
                    right_trigger = joystick.get_axis(5) if joystick.get_numaxes() > 5 else 0
                except:
                    # Fallback für andere Controller-Layouts
                    left_trigger = (joystick.get_button(6) * 1.0) if joystick.get_numbuttons() > 6 else 0
                    right_trigger = (joystick.get_button(7) * 1.0) if joystick.get_numbuttons() > 7 else 0
                
                # X/Y-Bewegung mit rechtem Joystick
                if abs(right_x) > 0.1:
                    distance = min(abs(right_x) * 10, 10)
                    self.move_printer("x", distance if right_x > 0 else -distance)
                
                if abs(right_y) > 0.1:
                    distance = min(abs(right_y) * 10, 10)
                    self.move_printer("y", distance if right_y > 0 else -distance)
                
                # Extruder-Bewegung mit linkem Joystick (X-Achse)
                if abs(left_x) > 0.1:
                    distance = min(abs(left_x) * 5, 5)  # Kleinere Werte für Extruder
                    self._printer.extrude(distance if left_x > 0 else -distance)
                
                # Z-Bewegung mit Triggern
                # Rechter Trigger (RT) - nach oben
                if right_trigger > 0.1:
                    distance = min(right_trigger * 10, 10)
                    self.move_printer("z", distance)  # Positive Werte = nach oben
                
                # Linker Trigger (LT) - nach unten
                if left_trigger > 0.1:
                    distance = min(left_trigger * 10, 10)
                    self.move_printer("z", -distance)  # Negative Werte = nach unten
                
                # Buttons für andere Funktionen
                for i in range(joystick.get_numbuttons()):
                    if joystick.get_button(i):
                        self.handle_button_press(i)
                
                # Testmodus-Daten senden
                if self.test_mode:
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "controller_values",
                        "x": right_x,
                        "y": right_y,
                        "z": right_trigger - left_trigger,  # Kombinierte Z-Bewegung
                        "e": left_x  # Extruder-Bewegung
                    })
                
                time.sleep(0.1)  # Kurze Pause, um CPU-Last zu reduzieren
        
        except Exception as e:
            self._logger.error("Fehler im Controller-Thread: %s", str(e))
            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Fehler: " + str(e)})
        
        finally:
            try:
                pygame.joystick.quit()
                pygame.quit()
            except:
                pass
            
            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Nicht verbunden"})
    
    def move_printer(self, axis, distance):
        """Bewegt den Drucker in der angegebenen Achse um die angegebene Distanz"""
        if not self._printer.is_operational() or self._printer.is_printing():
            return
        
        # Distanz auf eine Dezimalstelle runden
        distance = round(distance, 1)
        
        # Jog-Befehl senden
        self._printer.jog({axis: distance})
    
    def handle_button_press(self, button_index):
        """Verarbeitet Tastendrücke des Controllers"""
        # Reduzierte Implementierung für Tasten
        if button_index == 0:  # A-Taste
            self._printer.home(['x', 'y'])
        elif button_index == 1:  # B-Taste
            # Vollständiger Autohome für alle Achsen
            self._printer.home(['x', 'y', 'z'])
            self._logger.info("Autohome-Befehl gesendet")
        # X- und Y-Tasten haben keine Funktion mehr
    
    # API-Endpunkte
    def get_api_commands(self):
        return dict(
            toggleTestMode=["enabled"],
            updateScaleFactor=["axis", "value"]
        )

__plugin_name__ = "Xbox Controller Plugin"
__plugin_identifier__ = "octoprint_xbox_controller"
__plugin_version__ = "0.1.0"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()


def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation__
