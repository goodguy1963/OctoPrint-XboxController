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
        self._logger.debug("API command received: %s, data: %s", command, data)
        
        if command == "toggleTestMode":
            enabled = bool(data.get("enabled", False))
            self._logger.info("Test mode toggled: %s", enabled)
            self.test_mode = enabled
            self._plugin_manager.send_plugin_message(self._identifier, 
                                                   {"type": "status", "status": "Test Mode: " + ("Enabled" if enabled else "Disabled")})
            return flask.jsonify(success=True, testMode=enabled)
            
        elif command == "updateScaleFactor":
            axis = data.get("axis")
            value = int(data.get("value", 150))
            
            if axis == "xy":
                self.xy_scale_factor = value
            elif axis == "z":
                self.z_scale_factor = value
            elif axis == "e":
                self.e_scale_factor = value
                
            self._settings.set([axis + "_scale_factor"], value)
            self._settings.save()
            return flask.jsonify(success=True)
            
        elif command == "controllerValues":
            # Handle controller values from JavaScript
            self._logger.debug("Received controller values: x=%s, y=%s, z=%s, e=%s", 
                            data.get("x", 0), data.get("y", 0), data.get("z", 0), data.get("e", 0))
            
            # Always forward to UI for display
            self._plugin_manager.send_plugin_message(self._identifier, {
                "type": "controller_values",
                "x": float(data.get("x", 0)),
                "y": float(data.get("y", 0)),
                "z": float(data.get("z", 0)),
                "e": float(data.get("e", 0))
            })
            
            # If not in test mode, process movement commands
            if not self.test_mode:
                self._process_controller_values(data)
                
            return flask.jsonify(success=True)
        
        return flask.jsonify(error="Unknown command")

    def _process_controller_values(self, data):
        """Process controller values and send commands to printer"""
        try:
            # Only process if printer is operational
            if not self._printer.is_operational() or self._printer.is_printing():
                return
                
            # X movement
            x_val = float(data.get("x", 0))
            if abs(x_val) > 0.1:
                distance = min(abs(x_val) * 10, 10)
                distance = round(distance, 1)
                self._printer.jog({"x": distance if x_val > 0 else -distance})
                self._logger.debug("X movement: %s", distance if x_val > 0 else -distance)
                
            # Y movement
            y_val = float(data.get("y", 0))
            if abs(y_val) > 0.1:
                distance = min(abs(y_val) * 10, 10)
                distance = round(distance, 1)
                self._printer.jog({"y": distance if y_val > 0 else -distance})
                self._logger.debug("Y movement: %s", distance if y_val > 0 else -distance)
                
            # Z movement
            z_val = float(data.get("z", 0))
            if abs(z_val) > 0.1:
                distance = min(abs(z_val) * 10, 10)
                distance = round(distance, 1)
                self._printer.jog({"z": distance if z_val > 0 else -distance})
                self._logger.debug("Z movement: %s", distance if z_val > 0 else -distance)
                
            # Extruder movement
            e_val = float(data.get("e", 0))
            if abs(e_val) > 0.1:
                distance = min(abs(e_val) * 5, 5)
                distance = round(distance, 1)
                self._printer.extrude(distance if e_val > 0 else -distance)
                self._logger.debug("Extruder movement: %s", distance if e_val > 0 else -distance)
                
            # Handle buttons if present in data
            buttons = data.get("buttons", {})
            for btn_idx, pressed in buttons.items():
                if pressed:
                    self._logger.debug("Button pressed: %s", btn_idx)
                    self.handle_button_press(int(btn_idx))
                    
        except Exception as e:
            self._logger.error("Error processing controller values: %s", str(e))

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
            controller_name = joystick.get_name()
            self._logger.info("Controller connected: %s with %d axes and %d buttons", 
                             controller_name, joystick.get_numaxes(), joystick.get_numbuttons())
            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Verbunden: " + controller_name})
            
            # Hauptschleife
            while self.controller_running:
                pygame.event.pump()
                
                # Joystick-Werte auslesen
                try:
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
                    
                    # Daten für die UI
                    controller_data = {
                        "type": "controller_values",
                        "x": right_x,
                        "y": right_y,
                        "z": right_trigger - left_trigger,  # Kombinierte Z-Bewegung
                        "e": left_x  # Extruder-Bewegung
                    }
                    
                    # Immer Daten senden, unabhängig vom Testmodus
                    self._plugin_manager.send_plugin_message(self._identifier, controller_data)
                    
                    # Nur im Nicht-Testmodus Bewegungsbefehle ausführen
                    if not self.test_mode:
                        # Movement processing moved to _process_controller_values
                        self._process_controller_values({
                            "x": right_x,
                            "y": right_y,
                            "z": right_trigger - left_trigger,
                            "e": left_x
                        })
                        
                        # Buttons weiterhin direkt verarbeiten
                        for i in range(joystick.get_numbuttons()):
                            if joystick.get_button(i):
                                self.handle_button_press(i)
                    
                except Exception as e:
                    self._logger.error("Error reading controller: %s", str(e))
                
                time.sleep(0.1)  # Kurze Pause, um CPU-Last zu reduzieren
        
        except Exception as e:
            self._logger.error("Error in controller thread: %s", str(e))
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
            updateScaleFactor=["axis", "value"],
            controllerValues=["x", "y", "z", "e"]
        )

__plugin_name__ = "Xbox Controller Plugin"
__plugin_identifier__ = "xbox_controller"
__plugin_version__ = "0.1.0"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()


def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation__
