# coding=utf-8
import time
import threading
import os
import logging
import sys

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
        self.controller_initialized = False
        self.last_controller_check = 0

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

    def get_api_commands(self):
        return dict(
            toggleTestMode=["enabled"],
            updateScaleFactor=["axis", "value"],
            controllerValues=["x", "y", "z", "e"],
            controllerDiscovered=["id"]  # New command to handle controller discovery from JS
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
            try:
                # Extract values with proper error handling
                x_val = float(data.get("x", 0))
                y_val = float(data.get("y", 0))
                z_val = float(data.get("z", 0))
                e_val = float(data.get("e", 0))
                
                self._logger.debug("Received controller values: x=%.2f, y=%.2f, z=%.2f, e=%.2f", 
                                x_val, y_val, z_val, e_val)
                
                # Always forward to UI for display - this is critical for test mode
                self._plugin_manager.send_plugin_message(self._identifier, {
                    "type": "controller_values",
                    "x": x_val,
                    "y": y_val,
                    "z": z_val,
                    "e": e_val
                })
                
                # If not in test mode, process movement commands
                if not self.test_mode:
                    self._process_controller_values(data)
                else:
                    self._logger.debug("Test mode active, not sending printer commands")
                    
                return flask.jsonify(success=True)
            except Exception as e:
                self._logger.error("Error processing controller values: %s", str(e))
                return flask.jsonify(error="Error processing controller values")
        
        elif command == "controllerDiscovered":
            controller_id = data.get("id", "Unknown")
            self._logger.info("Controller discovered by frontend: %s", controller_id)
            # Try to reinitialize controller thread
            if not self.controller_initialized:
                self._logger.info("Attempting to connect to controller %s from backend", controller_id)
                self.restart_controller_thread()
            return flask.jsonify(success=True)
            
        return flask.jsonify(error="Unknown command")

    def _process_controller_values(self, data):
        """Process controller values and send commands to printer"""
        try:
            # Only process if printer is operational and not printing
            if not self._printer.is_operational():
                self._logger.debug("Printer not operational, ignoring controller values")
                return
            
            if self._printer.is_printing():
                self._logger.debug("Printer is busy printing, ignoring controller values")
                return
            
            if self.test_mode:
                self._logger.debug("Test mode active, not sending commands")
                return
                
            # X movement (right joystick X)
            x_val = float(data.get("x", 0))
            if abs(x_val) > 0.1:
                # Scale the movement based on the joystick value
                distance = min(abs(x_val) * (self.xy_scale_factor / 100), 10)
                distance = round(distance, 1)
                
                # Send the actual G-code command
                self._logger.info("Sending X jog command: %s", distance if x_val > 0 else -distance)
                self._printer.commands("G91")  # Set to relative positioning
                self._printer.commands("G0 X{} F3000".format(distance if x_val > 0 else -distance))
                self._printer.commands("G90")  # Return to absolute positioning
                    
            # Y movement (right joystick Y)
            y_val = float(data.get("y", 0))
            if abs(y_val) > 0.1:
                distance = min(abs(y_val) * (self.xy_scale_factor / 100), 10)
                distance = round(distance, 1)
                
                self._logger.info("Sending Y jog command: %s", distance if y_val < 0 else -distance)
                self._printer.commands("G91")  # Set to relative positioning
                self._printer.commands("G0 Y{} F3000".format(distance if y_val < 0 else -distance))  # Y is inverted
                self._printer.commands("G90")  # Return to absolute positioning
                    
            # Z movement (triggers)
            z_val = float(data.get("z", 0))
            if abs(z_val) > 0.1:
                distance = min(abs(z_val) * (self.z_scale_factor / 100), 5)  # Z moves should be smaller
                distance = round(distance, 1)
                
                self._logger.info("Sending Z jog command: %s", distance if z_val > 0 else -distance)
                self._printer.commands("G91")  # Set to relative positioning
                self._printer.commands("G0 Z{} F600".format(distance if z_val > 0 else -distance))  # Z should move slowly
                self._printer.commands("G90")  # Return to absolute positioning
                    
            # Extruder movement (left joystick X)
            e_val = float(data.get("e", 0))
            if abs(e_val) > 0.1:
                distance = min(abs(e_val) * (self.e_scale_factor / 100), 3)  # Extrusion should be limited
                distance = round(distance, 1)
                
                self._logger.info("Sending extruder command: %s", distance if e_val > 0 else -distance)
                self._printer.commands("G91")  # Set to relative positioning
                if e_val > 0:
                    self._printer.commands("G1 E{} F300".format(distance))  # Extrude slowly
                else:
                    self._printer.commands("G1 E-{} F1200".format(distance))  # Retract faster
                self._printer.commands("G90")  # Return to absolute positioning
                    
            # Handle buttons
            buttons = data.get("buttons", {})
            for btn_idx, pressed in buttons.items():
                if pressed:
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
        
        # Log pygame version and platform information for debugging
        self._logger.info("Pygame Version: %s", pygame.version.ver)
        self._logger.info("Platform: %s", sys.platform)
        
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
        self._logger.info("Controller thread started")
    
    def controller_worker(self):
        try:
            # Initialize pygame
            self._logger.info("Initializing pygame for controller detection")
            pygame.init()
            pygame.joystick.init()
            
            # Debug information about pygame
            self._logger.info("Pygame initialized. Available joysticks: %d", pygame.joystick.get_count())
            
            # List all available joysticks
            for i in range(pygame.joystick.get_count()):
                try:
                    joy = pygame.joystick.Joystick(i)
                    joy.init()
                    self._logger.info("Found joystick %d: %s with %d axes and %d buttons", 
                                    i, joy.get_name(), joy.get_numaxes(), joy.get_numbuttons())
                    joy.quit()  # Release it for now
                except Exception as e:
                    self._logger.error("Error inspecting joystick %d: %s", i, str(e))
            
            # Set up controller detection loop
            self.controller_initialized = False
            reconnect_attempts = 0
            joystick = None
            
            # Warte auf Controller-Verbindung
            while self.controller_running:
                try:
                    # Re-initialize pygame joystick subsystem periodically to refresh the list
                    if reconnect_attempts % 5 == 0:
                        self._logger.info("Refreshing joystick detection")
                        try:
                            pygame.joystick.quit()
                            pygame.joystick.init()
                        except Exception as e:
                            self._logger.error("Error refreshing joystick subsystem: %s", str(e))
                
                    joystick_count = pygame.joystick.get_count()
                    current_time = time.time()
                    
                    # Check if it's time to re-check for controllers (every 2 seconds)
                    if current_time - self.last_controller_check >= 2:
                        self.last_controller_check = current_time
                        
                        if joystick_count > 0 and not self.controller_initialized:
                            # Controller found - try each connected joystick
                            for i in range(joystick_count):
                                try:
                                    tmp_joystick = pygame.joystick.Joystick(i)
                                    tmp_joystick.init()
                                    controller_name = tmp_joystick.get_name()
                                    
                                    # Check if this is likely an Xbox controller
                                    if "xbox" in controller_name.lower() or "x-box" in controller_name.lower() or \
                                       "microsoft" in controller_name.lower():
                                        self._logger.info("Xbox controller detected! %s", controller_name)
                                        joystick = tmp_joystick
                                        break
                                    else:
                                        # Not an Xbox controller but we'll use it if nothing else
                                        if not joystick:
                                            self._logger.info("Non-Xbox controller found: %s - will use if no Xbox controller is found", 
                                                           controller_name)
                                            joystick = tmp_joystick
                                        else:
                                            tmp_joystick.quit()
                                except Exception as e:
                                    self._logger.error("Error initializing joystick %d: %s", i, str(e))
                            
                            # If we found and initialized a controller
                            if joystick:
                                controller_name = joystick.get_name()
                                self._logger.info("Controller connected: %s with %d axes and %d buttons", 
                                                controller_name, joystick.get_numaxes(), joystick.get_numbuttons())
                                
                                # Send success message to frontend
                                self._plugin_manager.send_plugin_message(self._identifier, 
                                                                     {"type": "status", "status": "Verbunden: " + controller_name})
                                self.controller_initialized = True
                                reconnect_attempts = 0
                        
                        elif joystick_count == 0 and self.controller_initialized:
                            # Controller was disconnected
                            self._logger.info("Controller disconnected")
                            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Nicht verbunden"})
                            self.controller_initialized = False
                            if joystick:
                                try:
                                    joystick.quit()
                                except:
                                    pass
                            joystick = None
                        
                        elif joystick_count == 0 and not self.controller_initialized:
                            # No controller connected yet, log periodically
                            reconnect_attempts += 1
                            if reconnect_attempts % 15 == 0:  # Log every 30 seconds to avoid spam
                                self._logger.info("Waiting for controller... (attempt %d)", reconnect_attempts)
                                self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Warte auf Controller..."})
                
                    # If controller is active, read inputs
                    if self.controller_initialized and joystick:
                        try:
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
                            
                            # Apply threshold to avoid noise/drift
                            right_x = right_x if abs(right_x) > 0.05 else 0
                            right_y = right_y if abs(right_y) > 0.05 else 0
                            left_x = left_x if abs(left_x) > 0.05 else 0
                            z_value = (right_trigger - left_trigger)
                            z_value = z_value if abs(z_value) > 0.05 else 0
                            
                            # Daten für die UI
                            controller_data = {
                                "type": "controller_values",
                                "x": right_x,
                                "y": right_y,
                                "z": z_value,
                                "e": left_x  # Extruder-Bewegung
                            }
                            
                            # Always send values for the UI, regardless of test mode
                            if abs(right_x) > 0.05 or abs(right_y) > 0.05 or abs(z_value) > 0.05 or abs(left_x) > 0.05:
                                self._plugin_manager.send_plugin_message(self._identifier, controller_data)
                                self._logger.debug("Sending controller values to UI: %s", controller_data)
                            
                            # Process values for printer movement only if not in test mode
                            if not self.test_mode:
                                if abs(right_x) > 0.05 or abs(right_y) > 0.05 or abs(z_value) > 0.05 or abs(left_x) > 0.05:
                                    self._process_controller_values({
                                        "x": right_x,
                                        "y": right_y,
                                        "z": z_value,
                                        "e": left_x
                                    })
                                
                                # Process buttons
                                for i in range(joystick.get_numbuttons()):
                                    if joystick.get_button(i):
                                        self.handle_button_press(i)
                                        
                        except Exception as e:
                            self._logger.error("Error reading controller: %s", str(e))
                            # If we hit an error reading the controller, try to recover
                            if "Invalid joystick device number" in str(e):
                                self.controller_initialized = False
                                self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Fehler: Controller nicht erreichbar"})
                    
                    time.sleep(0.1)  # Kurze Pause, um CPU-Last zu reduzieren
                
                except Exception as e:
                    self._logger.error("Error in controller thread: %s", str(e))
                    self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Fehler: " + str(e)})
            
        finally:
            try:
                if joystick:
                    joystick.quit()
                pygame.joystick.quit()
                pygame.quit()
                self._logger.info("Pygame resources released")
            except Exception as e:
                self._logger.error("Error shutting down pygame: %s", str(e))
            
            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Nicht verbunden"})

    def restart_controller_thread(self):
        """Restart the controller thread to force reconnection"""
        self._logger.info("Restarting controller thread")
        if self.controller_thread and self.controller_thread.is_alive():
            self.controller_running = False
            self.controller_thread.join(timeout=1.0)
        
        self.controller_running = True
        self.controller_thread = threading.Thread(target=self.controller_worker)
        self.controller_thread.daemon = True
        self.controller_thread.start()
        self._logger.info("Controller thread restarted")

    def move_printer(self, axis, distance):
        """Bewegt den Drucker in der angegebenen Achse um die angegebene Distanz"""
        if not self._printer.is_operational() or self._printer.is_printing():
            return
        
        # Distanz auf eine Dezimalstelle runden
        distance = round(distance, 1)
        
        # Jog-Befehl senden
        self._printer.jog({axis: distance})
    
    def handle_button_press(self, button_index):
        """Processes controller button presses"""
        if self.test_mode:
            self._logger.debug("Test mode active, not processing button %s", button_index)
            return
            
        try:
            if button_index == 0:  # A-Taste
                self._logger.info("Sending Home X/Y command")
                self._printer.commands("G28 X Y")
            elif button_index == 1:  # B-Taste
                self._logger.info("Sending Home All command")
                self._printer.commands("G28")
        except Exception as e:
            self._logger.error("Error handling button press: %s", str(e))

__plugin_name__ = "Xbox Controller Plugin"
__plugin_identifier__ = "xbox_controller"
__plugin_version__ = "0.1.0"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()


def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation__
