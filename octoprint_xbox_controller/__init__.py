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
    logging.error("Das Modul 'xboxcontroller' ist nicht installiert.")


################################################################
# Controller Handler Klasse
################################################################
class XboxControllerHandler:
    def __init__(self, send_gcode_callback, settings, plugin):  # Add plugin parameter
        self.send_gcode = send_gcode_callback
        self.settings = settings
        self._plugin = plugin  # Store plugin reference

        self.controller = None
        self.running = False
        self.thread = None
        self._last_sent_time = 0
        self.initialized = False  # Add initialization flag

        # Lade Skalierungsfaktoren aus den Plugin-Einstellungen
        self.xy_scale_factor = self.settings.get_int(["xy_scale_factor"], 150)
        self.e_scale_factor = self.settings.get_int(["e_scale_factor"], 150)
        self.z_scale_factor = self.settings.get_int(["z_scale_factor"], 150)
        self.max_z = self.settings.get_int(["max_z"], 100)
        self.current_z = 0

    def init_controller(self):
        try:
            if XboxController is None:
                self._plugin.update_status("Controller Modul nicht verfügbar")
                self._plugin._logger.warning("Xbox360Controller module not available")
                return False
            
            self.controller = XboxController()
            self.initialized = True
            self._plugin.update_status("Controller verbunden")
            return True
            
        except Exception as e:
            self._plugin.update_status("Kein Controller gefunden - Plugin läuft im Offline-Modus")
            self._plugin._logger.warning("No controller found: %s", str(e))
            return False

    def _clamp(self, value, min_val, max_val):
        return max(min(value, max_val), min_val)

    def read_controller(self):
        if not self.controller:
            return None

        # Implement the logic to read controller values
        movement = {
            "x": self.controller.axis_l.x,
            "y": self.controller.axis_l.y,
            "z": self.controller.axis_r.y,
            "e": self.controller.trigger_r.value
        }

        # UI Update hinzufügen
        self._plugin.update_ui(movement)
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
            try:
                if not self.initialized:
                    if not self.init_controller():
                        time.sleep(5)  # Retry every 5 seconds
                        continue
                
                now = time.time()
                if now - self._last_sent_time >= 0.5:
                    movement = self.read_controller()
                    if movement:
                        self.send_relative_command(movement)
                    self._last_sent_time = now
                time.sleep(0.01)
                
            except Exception as e:
                self._plugin._logger.error("Error in update loop: %s", str(e))
                self.initialized = False
                time.sleep(5)

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
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin):

    def __init__(self):
        self._identifier = "xbox_controller"  # Ensure a unique identifier is set
        self._controller_handler = None
        self._test_mode = False

    def get_template_configs(self):
        return [
            dict(type="tab", name="Xbox Controller", custom_bindings=True),
            dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        return dict(
            js=["js/xbox_controller.js"]
        )

    def get_settings_defaults(self):
        # Removed the 'enabled' setting to always run the plugin
        return dict(
            xy_scale_factor=150,
            e_scale_factor=150,
            z_scale_factor=150,
            max_z=100
        )

    def on_api_command(self, command, data):
        if command == "toggleTestMode":
            self._test_mode = data.get("enabled", False)
            return flask.jsonify(success=True)
        elif command == "updateScaleFactor":
            axis = data.get("axis")
            value = data.get("value")
            
            if axis == "xy":
                self._settings.set_int(["xy_scale_factor"], value)
            elif axis == "z":
                self._settings.set_int(["z_scale_factor"], value)
            elif axis == "e":
                self._settings.set_int(["e_scale_factor"], value)
                
            self._settings.save()
            
            # Update die Werte im Controller Handler
            if self._controller_handler:
                if axis == "xy":
                    self._controller_handler.xy_scale_factor = value
                elif axis == "z":
                    self._controller_handler.z_scale_factor = value
                elif axis == "e":
                    self._controller_handler.e_scale_factor = value
                    
            return flask.jsonify(success=True)

    def send_controller_values(self, values):
        # Remove duplicate test mode check
        self._plugin_manager.send_plugin_message(
            self._identifier,
            dict(type="controller_values", **values)
        )
        if self._test_mode:
            self._logger.info("Test Mode Values: %s", values)

    def update_status(self, status):
        self._plugin_manager.send_plugin_message(
            self._identifier,
            dict(type="status", status=status)
        )

    ## StartupPlugin: Wird nach dem Start von OctoPrint aufgerufen
    def on_after_startup(self):
        self._logger.info("Starting Xbox Controller Plugin")
        self._controller_handler = XboxControllerHandler(
            self._send_gcode, 
            self._settings,
            self  # Plugin reference
        )
        # Always start the handler, regardless of controller presence.
        self._controller_handler.start()

    ## ShutdownPlugin: Wird beim Herunterfahren von OctoPrint aufgerufen
    def on_shutdown(self):
        if self._controller_handler:
            self._controller_handler.stop()

    def update_ui(self, movement=None):
        if movement and self._test_mode:
            self._plugin_manager.send_plugin_message(
                self._identifier,
                dict(
                    type="controller_values",
                    x=movement["x"],
                    y=movement["y"],
                    z=movement["z"],
                    e=movement["e"]
                )
            )

    def _send_gcode(self, command):
        if self._test_mode:
            self._logger.info("Test Mode: Simulated sending command: %s", command)
            # Optionally send a plugin message for UI or further terminal logging
            self._plugin_manager.send_plugin_message(
                self._identifier,
                dict(type="simulated_command", command=command)
            )
        else:
            self._printer.commands(command)

    def on_settings_save(self, data):
        # Save settings without checking an 'enabled' state
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        # Optionally update scaling factors in the handler
        if self._controller_handler:
            self._controller_handler.xy_scale_factor = self._settings.get_int(["xy_scale_factor"], 150)
            self._controller_handler.z_scale_factor = self._settings.get_int(["z_scale_factor"], 150)
            self._controller_handler.e_scale_factor = self._settings.get_int(["e_scale_factor"], 150)

__plugin_name__ = "Xbox Controller Plugin"
__plugin_identifier__ = "octoprint_xbox_controller"  # Added unique identifier
__plugin_version__ = "0.1.0"             # Added version information
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()


def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation
