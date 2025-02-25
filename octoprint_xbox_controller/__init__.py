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
        self.test_mode = True  # Debug-Modus standardmäßig aktivieren
        self.xy_scale_factor = 150
        self.z_scale_factor = 150
        self.e_scale_factor = 150
        self._logger.setLevel(logging.DEBUG)  # Debug-Level für Logger setzen

    def get_template_configs(self):
        return [
            dict(type="tab", template="xbox_controller_tab.jinja2", name="Xbox Controller", custom_bindings=True),
            dict(type="settings", template="xbox_controller_settings.jinja2", name="Xbox Controller", custom_bindings=True),
            dict(type="navbar", template="xbox_controller_navbar.jinja2", custom_bindings=False)  # Einfaches Template ohne Bindung
        ]

    def get_assets(self):
        return dict(
            js=["js/xbox_controller.js"],
            css=["css/xbox_controller.css"]
        )

    def get_settings_defaults(self):
        return dict(
            xy_scale_factor=150,
            z_scale_factor=150,
            e_scale_factor=150,
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
            
            # Debug-Ausgabe für Controller-Erkennung
            self._logger.info("Suche nach Controllern...")
            
            # Warte auf Controller-Verbindung
            while self.controller_running:
                joystick_count = pygame.joystick.get_count()
                self._logger.info("Gefundene Controller: %d", joystick_count)
                
                if joystick_count > 0:
                    break
                self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Warte auf Controller..."})
                time.sleep(1)
            
            if not self.controller_running:
                return
            
            # Controller initialisieren
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            
            # Debug-Informationen zum Controller
            controller_name = joystick.get_name()
            num_axes = joystick.get_numaxes()
            num_buttons = joystick.get_numbuttons()
            
            self._logger.info("Controller verbunden: %s", controller_name)
            self._logger.info("Anzahl Achsen: %d, Anzahl Tasten: %d", num_axes, num_buttons)
            
            # Achsen-Mapping basierend auf Controller-Typ
            left_x_axis = 0
            left_y_axis = 1
            right_x_axis = 2
            right_y_axis = 3
            left_trigger_axis = 4
            right_trigger_axis = 5

            # Anpassung für verschiedene Controller-Typen
            if "Xbox 360" in controller_name:
                # Standard-Mapping für Xbox 360 Controller
                pass
            elif "Xbox One" in controller_name:
                # Anpassung für Xbox One Controller
                pass
            elif "Logitech" in controller_name:
                # Anpassung für Logitech Controller
                left_trigger_axis = 2
                right_trigger_axis = 5
                right_x_axis = 3
                right_y_axis = 4

            self._logger.info("Achsen-Mapping: LX=%d, LY=%d, RX=%d, RY=%d, LT=%d, RT=%d",
                             left_x_axis, left_y_axis, right_x_axis, right_y_axis, 
                             left_trigger_axis, right_trigger_axis)
            
            self._plugin_manager.send_plugin_message(self._identifier, {
                "type": "status", 
                "status": "Verbunden: " + controller_name
            })
            
            # Hauptschleife
            while self.controller_running:
                # Verarbeite alle Events
                for event in pygame.event.get():
                    if event.type == pygame.JOYBUTTONDOWN:
                        self._logger.info("Taste gedrückt: %d", event.button)
                        self.handle_button_press(event.button)
                
                pygame.event.pump()
                
                # Joystick-Werte auslesen
                left_x = joystick.get_axis(left_x_axis)  # Linker Joystick X-Achse für Extruder
                left_y = -joystick.get_axis(left_y_axis)  # Y-Achse invertieren
                right_x = joystick.get_axis(right_x_axis)  # Rechter Joystick X-Achse
                right_y = -joystick.get_axis(right_y_axis)  # Y-Achse invertieren
                
                # Debug-Ausgabe für Joystick-Werte
                if abs(left_x) > 0.1 or abs(left_y) > 0.1 or abs(right_x) > 0.1 or abs(right_y) > 0.1:
                    self._logger.debug("Joystick-Werte: L(%0.2f, %0.2f), R(%0.2f, %0.2f)", 
                                      left_x, left_y, right_x, right_y)
                
                # Trigger-Werte auslesen (können je nach Controller unterschiedlich sein)
                try:
                    left_trigger = joystick.get_axis(left_trigger_axis) if joystick.get_numaxes() > left_trigger_axis else 0
                    right_trigger = joystick.get_axis(right_trigger_axis) if joystick.get_numaxes() > right_trigger_axis else 0
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
            self._logger.warning("Drucker ist nicht betriebsbereit oder druckt gerade")
            return
        
        # Distanz auf eine Dezimalstelle runden
        distance = round(distance, 1)
        
        # Debug-Ausgabe
        self._logger.info("Sende Bewegungsbefehl: %s: %.1f", axis, distance)
        
        # Jog-Befehl senden
        try:
            self._printer.jog({axis: distance})
            self._logger.debug("Bewegungsbefehl gesendet")
        except Exception as e:
            self._logger.error("Fehler beim Senden des Bewegungsbefehls: %s", str(e))
    
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
__plugin_identifier__ = "xbox_controller"
__plugin_version__ = "0.1.0"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()


def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation__
