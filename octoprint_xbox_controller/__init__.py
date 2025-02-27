# coding=utf-8
import time
import threading
import os
import logging
import sys
import subprocess
import glob
import re  # Added for regex pattern matching
import select  # Add missing select module for evdev
import traceback  # Add for better error reporting

import octoprint.plugin
import flask

# Import pygame conditionally to handle potential import issues
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    
try:
    import evdev
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

# Try to import additional USB utilities
try:
    import usb.core
    import usb.util
    USB_UTILS_AVAILABLE = True
except ImportError:
    USB_UTILS_AVAILABLE = False

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
        self.use_evdev = False  # Will be set based on availability and settings
        self.controller_type = "unknown"  # Will store the detected controller type
        self.evdev_device = None  # Will store the evdev device if applicable
        self.detection_method = "auto"  # Can be "auto", "pygame", "evdev", "xboxdrv"
        self.reconnect_timer = None
        self.last_reconnect_attempt = 0
        # Add controller state variables for evdev
        self.evdev_axes = {}  # Store axis values
        self.evdev_buttons = {}  # Store button states
        self.last_send_time = 0  # Rate limit value sending

    def get_template_configs(self):
        return [
            dict(type="tab", template="xbox_controller_tab.jinja2", name="Xbox Controller", custom_bindings=True),
            dict(type="settings", template="xbox_controller_settings.jinja2", name="Xbox Controller", custom_bindings=True),
            dict(type="navbar", template="xbox_controller_navbar.jinja2", custom_bindings=False, replaces=False)  # Updated navbar config
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
            max_z=100,
            use_evdev=EVDEV_AVAILABLE,  # Default to evdev if available
            usb_detection_method="auto",  # Can be "auto", "pygame", "evdev", "xboxdrv"
            debug_logging=True,  # Changed default to True for better diagnostics
            auto_reconnect=True   # Added auto reconnect option
        )

    def get_api_commands(self):
        return dict(
            toggleTestMode=["enabled"],
            updateScaleFactor=["axis", "value"],
            controllerValues=["x", "y", "z", "e"],
            controllerDiscovered=["id", "source"]  # Updated to accept source parameter
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
            source = data.get("source", "unknown")
            self._logger.info("Controller discovered by %s: %s", source, controller_id)
            
            # If this is a browser controller, update the status differently
            if source == "browser":
                self._plugin_manager.send_plugin_message(self._identifier, {
                    "type": "connection_info",
                    "source": "browser",
                    "connected": True,
                    "id": controller_id
                })
            
            # Try to reinitialize controller thread if needed
            if not self.controller_initialized and source != "browser":
                self._logger.info("Attempting to connect to controller %s from backend", controller_id)
                self.restart_controller_thread()
                
            return flask.jsonify(success=True)
            
        return flask.jsonify(error="Unknown command")

    def _process_controller_values(self, data):
        """Process controller values and send commands to printer"""
        try:
            # Enhanced debug logging
            debug_mode = self._settings.get_boolean(["debug_logging"], False)
            if debug_mode:
                self._logger.info("Processing controller values: %s", data)
            
            # Only process if printer is operational and not printing
            if not self._printer.is_operational():
                self._logger.info("Printer not operational (state: %s), ignoring controller values", 
                                 self._printer.get_state_string())
                return
            
            if self._printer.is_printing():
                self._logger.info("Printer is busy printing (state: %s), ignoring controller values", 
                                 self._printer.get_state_string())
                return
            
            if self.test_mode:
                self._logger.info("Test mode active, not sending commands for values: %s", data)
                return
            
            # Log all significant input values
            significant_input = False
                
            # X movement (right joystick X)
            x_val = float(data.get("x", 0))
            if abs(x_val) > 0.1:
                significant_input = True
                # Scale the movement based on the joystick value
                distance = min(abs(x_val) * (self.xy_scale_factor / 100), 10)
                distance = round(distance, 1)
                
                # Send the actual G-code command
                self._logger.info("Sending X jog command: %s", distance if x_val > 0 else -distance)
                try:
                    self._send_movement_command("X", distance if x_val > 0 else -distance, 3000)
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "command_sent", 
                        "axis": "X", 
                        "value": distance if x_val > 0 else -distance
                    })
                except Exception as e:
                    self._logger.error("Error sending X movement command: %s", str(e))
                    self._logger.error(traceback.format_exc())
                    
            # Y movement (right joystick Y)
            y_val = float(data.get("y", 0))
            if abs(y_val) > 0.1:
                significant_input = True
                distance = min(abs(y_val) * (self.xy_scale_factor / 100), 10)
                distance = round(distance, 1)
                
                self._logger.info("Sending Y jog command: %s", distance if y_val < 0 else -distance)
                try:
                    self._send_movement_command("Y", distance if y_val < 0 else -distance, 3000)
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "command_sent", 
                        "axis": "Y", 
                        "value": distance if y_val < 0 else -distance
                    })
                except Exception as e:
                    self._logger.error("Error sending Y movement command: %s", str(e))
                    self._logger.error(traceback.format_exc())
                    
            # Z movement (triggers)
            z_val = float(data.get("z", 0))
            if abs(z_val) > 0.1:
                significant_input = True
                distance = min(abs(z_val) * (self.z_scale_factor / 100), 5)  # Z moves should be smaller
                distance = round(distance, 1)
                
                self._logger.info("Sending Z jog command: %s", distance if z_val > 0 else -distance)
                try:
                    self._send_movement_command("Z", distance if z_val > 0 else -distance, 600)
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "command_sent", 
                        "axis": "Z", 
                        "value": distance if z_val > 0 else -distance
                    })
                except Exception as e:
                    self._logger.error("Error sending Z movement command: %s", str(e))
                    self._logger.error(traceback.format_exc())
                    
            # Extruder movement (left joystick X)
            e_val = float(data.get("e", 0))
            if abs(e_val) > 0.1:
                significant_input = True
                distance = min(abs(e_val) * (self.e_scale_factor / 100), 3)  # Extrusion should be limited
                distance = round(distance, 1)
                
                self._logger.info("Sending extruder command: %s", distance if e_val > 0 else -distance)
                try:
                    # Use direct G-code for extrusion to ensure it works
                    if e_val > 0:
                        self._printer.commands([
                            "G91",  # Relative positioning
                            f"G1 E{distance} F300",  # Extrude slowly
                            "G90"   # Back to absolute positioning
                        ])
                    else:
                        self._printer.commands([
                            "G91",  # Relative positioning
                            f"G1 E-{distance} F1200",  # Retract faster
                            "G90"   # Back to absolute positioning
                        ])
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "command_sent", 
                        "axis": "E", 
                        "value": distance if e_val > 0 else -distance
                    })
                except Exception as e:
                    self._logger.error("Error sending E movement command: %s", str(e))
                    self._logger.error(traceback.format_exc())
                    
            # Handle buttons
            buttons = data.get("buttons", {})
            for btn_idx, pressed in buttons.items():
                if pressed:
                    significant_input = True
                    self.handle_button_press(int(btn_idx))
                    
            if debug_mode and not significant_input:
                self._logger.debug("No significant controller input detected")
                        
        except Exception as e:
            self._logger.error("Error processing controller values: %s", str(e))
            self._logger.error(traceback.format_exc())

    def _send_movement_command(self, axis, distance, speed):
        """Helper method to send a movement command and handle errors"""
        try:
            # Validate parameters
            if not isinstance(axis, str) or axis not in ["X", "Y", "Z", "E"]:
                self._logger.error("Invalid axis: %s", axis)
                return
                
            if not isinstance(distance, (int, float)):
                self._logger.error("Invalid distance: %s", distance)
                return
                
            if not isinstance(speed, (int, float)) or speed <= 0:
                self._logger.error("Invalid speed: %s", speed)
                speed = 1000  # Use a safe default speed
            
            # Send commands as a group to ensure they're executed together
            self._logger.info("Sending %s axis movement: %s at speed %s", axis, distance, speed)
            self._printer.commands([
                "G91",  # Set to relative positioning
                f"G0 {axis}{distance} F{speed}",
                "G90"   # Return to absolute positioning
            ])
            
            return True
        except Exception as e:
            self._logger.error("Error in _send_movement_command: %s", str(e))
            self._logger.error(traceback.format_exc())
            return False

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
        
        # Enhanced controller detection info
        self._logger.info("===== Controller Detection Info =====")
        self._logger.info("Python version: %s", sys.version)
        self._logger.info("Platform: %s", sys.platform)
        self._logger.info("PYGAME_AVAILABLE: %s", PYGAME_AVAILABLE)
        self._logger.info("EVDEV_AVAILABLE: %s", EVDEV_AVAILABLE)
        self._logger.info("USB_UTILS_AVAILABLE: %s", USB_UTILS_AVAILABLE)
        
        # Log pygame version and platform information for debugging
        if PYGAME_AVAILABLE:
            self._logger.info("Pygame Version: %s", pygame.version.ver)
        else:
            self._logger.warning("Pygame not available - controller detection may be limited")
            
        self._logger.info("Platform: %s", sys.platform)
        
        # Log USB detection capabilities
        self._logger.info("EVDEV available: %s", EVDEV_AVAILABLE)
        self._logger.info("USB Utils available: %s", USB_UTILS_AVAILABLE)
        
        # Check for connected USB devices that might be controllers
        self._logger.info("Checking USB devices...")
        self._check_usb_devices()
        
        # Load settings
        self.xy_scale_factor = self._settings.get_int(["xy_scale_factor"], 150)
        self.z_scale_factor = self._settings.get_int(["z_scale_factor"], 150)
        self.e_scale_factor = self._settings.get_int(["e_scale_factor"], 150)
        self.use_evdev = self._settings.get_boolean(["use_evdev"], EVDEV_AVAILABLE)
        self.detection_method = self._settings.get(["usb_detection_method"], "auto")
        
        # More aggressive permission fixes
        self._check_and_fix_permissions()
        
        # Start controller detection
        self.start_controller_thread()
        
        # Schedule periodic reconnection attempts
        if self._settings.get_boolean(["auto_reconnect"], True):
            self._schedule_reconnect()

    def _check_usb_devices(self):
        """Check for USB devices that might be controllers"""
        try:
            # Common Xbox controller vendor IDs
            XBOX_VENDOR_IDS = ['045e', '044f', '046d', '0738', '1532', '0e6f', '24c6']
            
            if sys.platform.startswith('linux'):
                # List USB devices on Linux
                try:
                    lsusb_output = subprocess.check_output(['lsusb']).decode('utf-8')
                    self._logger.info("USB Devices:\n%s", lsusb_output)
                    
                    # Look for common Xbox controller IDs
                    xbox_patterns = ['Microsoft.*Xbox', 'Xbox.*Controller'] + XBOX_VENDOR_IDS
                    for line in lsusb_output.splitlines():
                        for pattern in xbox_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                self._logger.info("⭐ Potential Xbox controller detected: %s", line)
                                # Extract VID:PID and try to match to a known controller
                                match = re.search(r'ID\s+([0-9a-fA-F]+):([0-9a-fA-F]+)', line)
                                if match:
                                    vid, pid = match.groups()
                                    self._logger.info("Controller VID:PID = %s:%s", vid, pid)
                except Exception as e:
                    self._logger.warning("Error running lsusb: %s", str(e))
                
                # Check /dev/input devices
                try:
                    input_devices = glob.glob('/dev/input/js*') + glob.glob('/dev/input/event*')
                    self._logger.info("Input devices: %s", input_devices)
                except Exception as e:
                    self._logger.warning("Error checking input devices: %s", str(e))
            
            # If pyusb is available, try to directly scan USB devices
            if USB_UTILS_AVAILABLE:
                try:
                    self._logger.info("Scanning USB devices with pyusb...")
                    for vid in [int(x, 16) for x in XBOX_VENDOR_IDS]:
                        devices = list(usb.core.find(find_all=True, idVendor=vid))
                        for device in devices:
                            self._logger.info("Found USB device: vendor=%04x product=%04x manufacturer=%s",
                                        device.idVendor, device.idProduct, 
                                        usb.util.get_string(device, device.iManufacturer) if device.iManufacturer else 'Unknown')
                except Exception as e:
                    self._logger.warning("Error scanning USB devices with pyusb: %s", str(e))
                    
        except Exception as e:
            self._logger.error("Error checking USB devices: %s", str(e))

    def _check_and_fix_permissions(self):
        """More aggressively check and fix permissions for USB and input devices"""
        if not sys.platform.startswith('linux'):
            return
            
        try:
            self._logger.info("Checking and fixing device permissions...")
            
            # Check user groups
            try:
                user = subprocess.check_output(['whoami']).decode('utf-8').strip()
                groups = subprocess.check_output(['groups', user]).decode('utf-8')
                
                self._logger.info("User %s is in groups: %s", user, groups)
                
                if 'input' not in groups and 'root' not in groups and 'dialout' not in groups:
                    self._logger.warning("User is not in required groups, attempting to fix...")
                    try:
                        # Try to add user to input and dialout groups
                        subprocess.call(["sudo", "usermod", "-a", "-G", "input", user], 
                                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        subprocess.call(["sudo", "usermod", "-a", "-G", "dialout", user], 
                                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        self._logger.info("Added user to input and dialout groups (requires restart)")
                    except:
                        self._logger.warning("Could not add user to groups - insufficient permissions")
            except Exception as e:
                self._logger.error("Error checking user groups: %s", str(e))
                
            # Fix permissions on all input devices
            try:
                # Try using chmod directly
                for dev_path in ['/dev/input', '/dev/bus/usb']:
                    if os.path.exists(dev_path):
                        subprocess.call(["sudo", "chmod", "-R", "a+rw", dev_path], 
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        
                # Individual device files
                for device in glob.glob('/dev/input/js*') + glob.glob('/dev/input/event*'):
                    subprocess.call(["sudo", "chmod", "a+rw", device], 
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    
                    # Also try changing group
                    subprocess.call(["sudo", "chgrp", "input", device], 
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    
                self._logger.info("Applied permissions to input devices")
                
                # Create udev rule if it doesn't exist
                rule_path = "/etc/udev/rules.d/99-xbox-controller.rules"
                
                if not os.path.exists(rule_path):
                    rule_content = """# Xbox controller permissions
SUBSYSTEM=="input", GROUP="input", MODE="0666"
KERNEL=="js*", GROUP="input", MODE="0666"
KERNEL=="event*", GROUP="input", MODE="0666"
# Xbox controller specific rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", MODE="0666", GROUP="input"
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", MODE="0666", GROUP="input"
# Additional common controller vendors
SUBSYSTEM=="usb", ATTRS{idVendor}=="046d", MODE="0666", GROUP="input" # Logitech
SUBSYSTEM=="usb", ATTRS{idVendor}=="0738", MODE="0666", GROUP="input" # Mad Catz
SUBSYSTEM=="usb", ATTRS{idVendor}=="1532", MODE="0666", GROUP="input" # Razer
SUBSYSTEM=="usb", ATTRS{idVendor}=="0e6f", MODE="0666", GROUP="input" # PDP
SUBSYSTEM=="usb", ATTRS{idVendor}=="24c6", MODE="0666", GROUP="input" # PowerA
"""
                    try:
                        with open("/tmp/99-xbox-controller.rules", "w") as f:
                            f.write(rule_content)
                            
                        # Copy to system directory with sudo
                        subprocess.call(["sudo", "cp", "/tmp/99-xbox-controller.rules", rule_path], 
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        subprocess.call(["sudo", "udevadm", "control", "--reload-rules"], 
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        subprocess.call(["sudo", "udevadm", "trigger"], 
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        
                        self._logger.info("Created udev rule for controllers")
                    except Exception as e:
                        self._logger.error("Error creating udev rule: %s", str(e))
                
            except Exception as e:
                self._logger.error("Error fixing permissions: %s", str(e))
            
            # Try to list USB devices to verify we can see them
            try:
                usb_devices = subprocess.check_output(["lsusb"]).decode("utf-8")
                self._logger.info("USB devices after permission fix:\n%s", usb_devices)
                
                # Look for Xbox controllers specifically
                xbox_pattern = r'(Xbox|Microsoft.*Controller|045e)'
                if re.search(xbox_pattern, usb_devices, re.IGNORECASE):
                    self._logger.info("Xbox controller device found in USB list!")
            except Exception as e:
                self._logger.error("Error listing USB devices: %s", str(e))
                
        except Exception as e:
            self._logger.error("Error in permission check and fix: %s", str(e))

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt if needed"""
        if self.reconnect_timer:
            return
            
        def attempt_reconnect():
            current_time = time.time()
            # Only try to reconnect every 60 seconds
            if current_time - self.last_reconnect_attempt > 60:
                self.last_reconnect_attempt = current_time
                self._logger.info("Scheduled reconnection attempt...")
                if not self.controller_initialized:
                    self.restart_controller_thread()
            
            # Reschedule the timer
            self.reconnect_timer = threading.Timer(60, attempt_reconnect)
            self.reconnect_timer.daemon = True
            self.reconnect_timer.start()
            
        # Start the timer
        self.reconnect_timer = threading.Timer(60, attempt_reconnect)
        self.reconnect_timer.daemon = True
        self.reconnect_timer.start()

    ## ShutdownPlugin: Wird beim Herunterfahren von OctoPrint aufgerufen
    def on_shutdown(self):
        self.controller_running = False
        if self.reconnect_timer:
            self.reconnect_timer.cancel()
            self.reconnect_timer = None
            
        if self.controller_thread is not None:
            self.controller_thread.join(timeout=1.0)

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.xy_scale_factor = self._settings.get_int(["xy_scale_factor"], 150)
        self.z_scale_factor = self._settings.get_int(["z_scale_factor"], 150)
        self.e_scale_factor = self._settings.get_int(["e_scale_factor"], 150)
        
        # Check if USB detection method changed
        old_use_evdev = self.use_evdev
        self.use_evdev = self._settings.get_boolean(["use_evdev"], EVDEV_AVAILABLE)
        
        if old_use_evdev != self.use_evdev:
            self._logger.info("USB detection method changed, restarting controller thread")
            self.restart_controller_thread()

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
            # Dynamic method selection based on settings and availability
            detection_method = self._settings.get(["usb_detection_method"], "auto")
            self._logger.info("Using controller detection method: %s", detection_method)
            
            # Always try to fix permissions first on startup
            if sys.platform.startswith('linux'):
                self._check_and_fix_permissions()
            
            if detection_method == "auto":
                # Try multiple methods in order of preference
                if sys.platform.startswith('linux'):
                    # On Linux, try evdev first if available, then pygame
                    if EVDEV_AVAILABLE:
                        self._logger.info("Trying evdev detection first...")
                        if not self._evdev_controller_loop(try_only=False):  # Changed to False to commit to evdev
                            self._logger.info("Evdev detection failed, falling back to pygame...")
                            if PYGAME_AVAILABLE:
                                self._pygame_controller_loop()
                            else:
                                self._logger.error("No controller detection methods available!")
                    elif PYGAME_AVAILABLE:
                        self._logger.info("Evdev not available, using pygame...")
                        self._pygame_controller_loop()
                    else:
                        self._logger.error("No controller detection methods available!")
                else:
                    # On other platforms, pygame is the only option
                    if PYGAME_AVAILABLE:
                        self._logger.info("Using pygame for controller detection...")
                        self._pygame_controller_loop()
                    else:
                        self._logger.error("No controller detection methods available!")
            elif detection_method == "evdev" and EVDEV_AVAILABLE:
                self._logger.info("Using evdev for controller detection (explicit)")
                self._evdev_controller_loop()
            elif detection_method == "pygame" and PYGAME_AVAILABLE:
                self._logger.info("Using pygame for controller detection (explicit)")
                self._pygame_controller_loop()
            elif detection_method == "xboxdrv":
                self._logger.info("Using xboxdrv for controller detection (experimental)")
                self._xboxdrv_controller_loop()
            else:
                self._logger.error("Selected controller detection method %s not available!", detection_method)
                # Fall back to any available method
                if PYGAME_AVAILABLE:
                    self._logger.info("Falling back to pygame...")
                    self._pygame_controller_loop()
                elif EVDEV_AVAILABLE:
                    self._logger.info("Falling back to evdev...")
                    self._evdev_controller_loop()
        finally:
            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Nicht verbunden"})

    def _evdev_controller_loop(self, try_only=False):
        """Controller worker using evdev (Linux only)"""
        if not EVDEV_AVAILABLE:
            self._logger.warning("Evdev not available, cannot use this detection method")
            return False
            
        try:
            self._logger.info("Starting evdev controller detection loop")
            device_found = False
            reconnect_count = 0
            
            # Initial device scan
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            if not devices:
                self._logger.warning("No input devices found with evdev")
                if try_only:
                    return False
                    
            # Log all found devices
            for device in devices:
                self._logger.info("Input device: %s at %s", device.name, device.path)
                # Check file permissions
                if os.path.exists(device.path):
                    try:
                        file_stat = os.stat(device.path)
                        self._logger.info("Device permissions: %o, owner: %d", file_stat.st_mode & 0o777, file_stat.st_uid)
                    except Exception as e:
                        self._logger.error("Cannot check permissions: %s", str(e))
                        
                # Check if it's a game controller or joystick
                if any(keyword in device.name.lower() for keyword in ['xbox', 'controller', 'gamepad', 'joystick', 'joypad']):
                    self._logger.info("⭐ Potential controller device: %s", device.name)
                    self.evdev_device = device
                    controller_device = device
                    self.controller_initialized = True
                    device_found = True
                    self.controller_type = device.name  # Store the specific controller model
                    self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Verbunden"})
                    break
            
            last_scan_time = 0
            
            # Reset controller state
            self.evdev_axes = {}
            self.evdev_buttons = {}
            
            # Define axis and button mappings (common for Xbox controllers)
            # These can vary between controller models - this is a common mapping
            AXIS_MAPPING = {
                0: 'left_x',    # Left stick X
                1: 'left_y',    # Left stick Y (inverted)
                2: 'right_x',   # Right stick X
                3: 'right_y',   # Right stick Y (inverted)
                4: 'lt',        # Left trigger (on some controllers)
                5: 'rt'         # Right trigger (on some controllers)
            }
            
            BUTTON_MAPPING = {
                0: 'a',         # A button
                1: 'b',         # B button
                2: 'x',         # X button
                3: 'y',         # Y button
                4: 'lb',        # Left bumper
                5: 'rb',        # Right bumper
                6: 'back',      # Back/View button
                7: 'start',     # Start/Menu button
                8: 'home',      # Xbox button/Home
                9: 'l_thumb',   # Left stick press
                10: 'r_thumb'   # Right stick press
            }
            
            while self.controller_running:
                current_time = time.time()
                
                # Periodically rescan for devices
                if current_time - last_scan_time > 5:  # Every 5 seconds
                    last_scan_time = current_time
                    try:
                        # Fresh scan for input devices
                        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
                        
                        # Only log if we haven't found a controller yet or every 60 seconds
                        if not self.controller_initialized or reconnect_count % 12 == 0:
                            self._logger.info("Rescanning for input devices, found %d devices", len(devices))
                            for device in devices:
                                caps = device.capabilities(verbose=True)
                                is_joystick = evdev.ecodes.EV_ABS in caps and len(caps.get(evdev.ecodes.EV_ABS, [])) >= 2
                                
                                # Check if it's likely a controller
                                if is_joystick or any(keyword in device.name.lower() for keyword in ['xbox', 'controller', 'gamepad', 'joystick']):
                                    self._logger.info("⭐ Found controller device: %s at %s", device.name, device.path)
                                    self._logger.info("Controller capabilities: %s", caps)
                                    controller_device = device
                                    self.evdev_device = device
                                    self.controller_type = "controller-evdev"
                                    self.controller_initialized = True
                                    device_found = True
                                    
                                    # Send success message to frontend
                                    self._plugin_manager.send_plugin_message(self._identifier, 
                                                                        {"type": "status", "status": "Verbunden: " + device.name})
                                    
                                    # Also send connection info message
                                    self._plugin_manager.send_plugin_message(self._identifier, {
                                        "type": "connection_info",
                                        "source": "backend",
                                        "connected": True,
                                        "id": device.name
                                    })
                                    
                                    # Initialize axis states
                                    for code, name in AXIS_MAPPING.items():
                                        self.evdev_axes[name] = 0.0
                                    
                                    # Initialize button states
                                    for code, name in BUTTON_MAPPING.items():
                                        self.evdev_buttons[name] = False
                                        
                                    break
                    except Exception as e:
                        self._logger.error("Error scanning input devices: %s", str(e))
                
                # If we have an initialized controller, read events
                if self.controller_initialized and controller_device:
                    try:
                        # Try to read events with a timeout
                        r, w, x = select.select([controller_device.fd], [], [], 0.1)
                        
                        if r:
                            for event in controller_device.read():
                                # Process the event and update controller state
                                self._process_evdev_event(event, AXIS_MAPPING, BUTTON_MAPPING)
                            
                            # Send controller values periodically
                            if current_time - self.last_send_time > 0.05:  # 50ms rate limit
                                self.last_send_time = current_time
                                self._send_evdev_controller_values()
                                
                        # Periodically check that device is still available
                        if current_time - last_scan_time > 2:  # Every 2 seconds
                            if not os.path.exists(controller_device.path):
                                self._logger.warning("Controller disconnected: %s", controller_device.path)
                                self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Nicht verbunden"})
                                self.controller_initialized = False
                                controller_device = None
                                self.evdev_device = None
                                break
                                
                    except (OSError, IOError) as e:
                        if e.errno == 19:  # "No such device" error
                            self._logger.warning("Device %s no longer available", controller_device.path)
                            self._plugin_manager.send_plugin_message(self._identifier, {"type": "status", "status": "Nicht verbunden"})
                            self.controller_initialized = False
                            controller_device = None
                            self.evdev_device = None
                        elif e.errno != 11:  # Ignore "resource temporarily unavailable" (expected with non-blocking)
                            self._logger.error("Error reading from device: %s", str(e))
                    except Exception as e:
                        self._logger.error("Unexpected error with evdev: %s", str(e))
                
                time.sleep(0.01)
                reconnect_count += 1
                
            return device_found
                
        except Exception as e:
            self._logger.error("Fatal error in evdev controller worker: %s", str(e))
            self._logger.error(traceback.format_exc())
            if try_only:
                return False
            return False

    def _process_evdev_event(self, event, axis_mapping, button_mapping):
        """Process a single evdev event and update controller state"""
        try:
            if event.type == evdev.ecodes.EV_KEY:  # Button event
                # Get button code and pressed state
                button_code = event.code
                pressed = event.value == 1
                
                # Find the button name if it's in our mapping
                for code, name in button_mapping.items():
                    if button_code == code or button_code == getattr(evdev.ecodes, f'BTN_{name.upper()}', -1):
                        self.evdev_buttons[name] = pressed
                        self._logger.debug("Button %s (code %s) %s", 
                                       name, button_code, "pressed" if pressed else "released")
                        
                        # Handle button press if needed
                        if pressed:
                            if name == 'a':  # A button
                                self.handle_button_press(0)
                            elif name == 'b':  # B button
                
            elif event.type == evdev.ecodes.EV_ABS:  # Axis event
                # Get axis code and value
                axis_code = event.code
                value = event.value
                
                # Find the axis name if it's in our mapping
                for code, name in axis_mapping.items():
                    if axis_code == code or axis_code == getattr(evdev.ecodes, f'ABS_{name.upper()}', -1):
                        # Normalize value to -1.0 to 1.0 range
                        abs_info = self.evdev_device.absinfo(axis_code)
                        if abs_info:
                            min_val, max_val = abs_info.min, abs_info.max
                            range_val = max_val - min_val
                            if range_val > 0:
                                normalized = 2.0 * (value - min_val) / range_val - 1.0
                                
                                # Invert Y axes (they're typically opposite from the expected direction)
                                if name.endswith('_y'):
                                    normalized = -normalized
                                    
                                self.evdev_axes[name] = normalized
                                if abs(normalized) > 0.1:  # Only log significant movements
                                    self._logger.debug("Axis %s (code %s) value: %.2f", 
                                                   name, axis_code, normalized)
        except Exception as e:
            self._logger.error("Error processing evdev event: %s", str(e))

    def _send_evdev_controller_values(self):
        """Send the current controller state to the UI and printer control"""
        try:
            # Skip if no significant input
            if all(abs(v) < 0.1 for v in self.evdev_axes.values()) and not any(self.evdev_buttons.values()):
                return
                
            # Map axes to our expected control values
            x_val = self.evdev_axes.get('right_x', 0.0)
            y_val = self.evdev_axes.get('right_y', 0.0)
            z_val = 0.0
            
            # Map triggers to Z movement
            # Some controllers use axes for triggers, some use buttons
            if 'lt' in self.evdev_axes and 'rt' in self.evdev_axes:
                z_val = self.evdev_axes.get('rt', 0.0) - self.evdev_axes.get('lt', 0.0)
            else:
                # Use buttons as fallback
                rt_pressed = self.evdev_buttons.get('rb', False)
                lt_pressed = self.evdev_buttons.get('lb', False)
                z_val = (1.0 if rt_pressed else 0.0) - (1.0 if lt_pressed else 0.0)
            
            # Map left stick X to extruder control
            e_val = self.evdev_axes.get('left_x', 0.0)
            
            # Construct controller data
            controller_data = {
                "type": "controller_values",
                "x": x_val,
                "y": y_val,
                "z": z_val,
                "e": e_val
            }
            
            # Send to UI
            self._plugin_manager.send_plugin_message(self._identifier, controller_data)
            
            # Process movement if not in test mode
            if not self.test_mode:
                self._process_controller_values({
                    "x": x_val,
                    "y": y_val,
                    "z": z_val,
                    "e": e_val,
                    "buttons": {
                        0: self.evdev_buttons.get('a', False),
                        1: self.evdev_buttons.get('b', False),
                        # Add more button mappings as needed
                    }
                })
        
        except Exception as e:
            self._logger.error("Error sending evdev controller values: %s", str(e))

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
            self._logger.info("Button %s pressed, sending command", button_index)
            
            if button_index == 0:  # A-Taste
                self._logger.info("Sending Home X/Y command")
                try:
                    self._printer.commands("G28 X Y")
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "command_sent",
                        "command": "Home X/Y"
                    })
                except Exception as e:
                    self._logger.error("Error sending Home X/Y command: %s", str(e))
                    self._logger.error(traceback.format_exc())
                    
            elif button_index == 1:  # B-Taste
                self._logger.info("Sending Home All command")
                try:
                    self._printer.commands("G28")
                    self._plugin_manager.send_plugin_message(self._identifier, {
                        "type": "command_sent",
                        "command": "Home All"
                    })
                except Exception as e:
                    self._logger.error("Error sending Home All command: %s", str(e))
                    self._logger.error(traceback.format_exc())
                
        except Exception as e:
            self._logger.error("Error handling button press: %s", str(e))
            self._logger.error(traceback.format_exc())

__plugin_name__ = "Xbox Controller Plugin"
__plugin_identifier__ = "xbox_controller"
__plugin_version__ = "0.1.0"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = XboxControllerPlugin()


def __plugin_load__():
    global __plugin_implementation__
    return __plugin_implementation__
