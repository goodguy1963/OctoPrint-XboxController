console.log("Xbox Controller Plugin: JavaScript-Datei wird geladen");

$(function() {
    console.log("Xbox Controller Plugin: DOM bereit");
    
    // Überprüfen, ob die Elemente existieren
    console.log("Tab-Element beim Start:", $("#tab_plugin_xbox_controller").length);
    console.log("Settings-Element beim Start:", $("#settings_plugin_xbox_controller").length);
    
    function XboxControllerViewModel(parameters) {
        var self = this;
        
        // Debug-Ausgabe für die Parameter
        console.log("Xbox Controller Plugin: ViewModel wird initialisiert");
        console.log("Parameter:", parameters);
        
        self.settings = parameters[0];
        self.control = parameters[1];  // Fügen Sie den ControlViewModel hinzu
        
        // Stellen Sie sicher, dass diese Observables korrekt initialisiert werden
        self.controllerStatus = ko.observable("Nicht verbunden");
        self.isTestMode = ko.observable(false);
        
        self.currentX = ko.observable("0.00");
        self.currentY = ko.observable("0.00");
        self.currentZ = ko.observable("0.00");
        self.currentE = ko.observable("0.00");

        // Skalierungsfaktoren
        self.xyScaleFactor = ko.observable(150);
        self.zScaleFactor = ko.observable(150);
        self.eScaleFactor = ko.observable(150);

        // Fügen Sie eine Initialisierungsfunktion hinzu
        self.onBeforeBinding = function() {
            console.log("Xbox Controller Plugin: onBeforeBinding wird aufgerufen");
            // Überprüfen, ob die Einstellungen existieren
            console.log("Settings object:", self.settings);
            
            try {
                // Sicherere Methode zum Zugriff auf die Einstellungen
                if (self.settings && self.settings.settings && 
                    self.settings.settings.plugins && 
                    self.settings.settings.plugins.xbox_controller) {
                    
                    // Laden der Einstellungen aus dem Settings-Objekt
                    self.xyScaleFactor(self.settings.settings.plugins.xbox_controller.xy_scale_factor());
                    self.zScaleFactor(self.settings.settings.plugins.xbox_controller.z_scale_factor());
                    self.eScaleFactor(self.settings.settings.plugins.xbox_controller.e_scale_factor());
                } else {
                    console.warn("Xbox Controller Plugin: Einstellungen nicht verfügbar, verwende Standardwerte");
                }
            } catch (e) {
                console.error("Xbox Controller Plugin: Fehler beim Laden der Einstellungen", e);
                // Verwende Standardwerte
                self.xyScaleFactor(150);
                self.zScaleFactor(150);
                self.eScaleFactor(150);
            }
        };

        self.onAfterBinding = function() {
            console.log("Xbox Controller Plugin: onAfterBinding wird aufgerufen");
            console.log("Tab-Element:", $("#tab_plugin_xbox_controller").length);
            console.log("Settings-Element:", $("#settings_plugin_xbox_controller").length);
            
            // Fügen Sie einen sichtbaren Debug-Hinweis hinzu
            $("#tab_plugin_xbox_controller").prepend("<div style='background-color: yellow; padding: 5px; margin-bottom: 10px;'>Debug: ViewModel wurde gebunden</div>");
        };
        
        self.updateScaleFactor = function(axis, value) {
            $.ajax({
                url: API_BASEURL + "plugin/xbox_controller",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "updateScaleFactor",
                    axis: axis,
                    value: parseInt(value)
                }),
                contentType: "application/json; charset=UTF-8"
            });
        };

        self.toggleTestMode = function() {
            self.isTestMode(!self.isTestMode());
            
            $.ajax({
                url: API_BASEURL + "plugin/xbox_controller",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "toggleTestMode",
                    enabled: self.isTestMode()
                }),
                contentType: "application/json; charset=UTF-8"
            });
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "xbox_controller") return;

            if (data.type === "status") {
                self.controllerStatus(data.status);
            } else if (data.type === "controller_values" && self.isTestMode()) {
                self.currentX(data.x.toFixed(2));
                self.currentY(data.y.toFixed(2));
                self.currentZ(data.z.toFixed(2));
                self.currentE(data.e.toFixed(2));
                
                // Log values to terminal if in test mode
                console.log("Controller Values:", data);
            }
        };

        function setupGamepad() {
            // Prüfe, ob Gamepad API verfügbar ist
            if (!navigator.getGamepads) {
                console.warn("Xbox Controller Plugin: Gamepad API nicht unterstützt");
                return;
            }
            
            console.log("Xbox Controller Plugin: Gamepad-Setup gestartet");
            
            // Status-Variable für den Controller
            var lastTimestamp = 0;
            var requestAnimationId = null;
            var buttonStates = {}; // Speichert den Status der Buttons, um wiederholtes Auslösen zu vermeiden
            
            // Funktion zur kontinuierlichen Prüfung des Gamepad-Status
            function checkGamepadStatus() {
                var gamepads = navigator.getGamepads();
                var gamepad = null;
                
                // Finde den ersten verbundenen Controller
                for (var i = 0; i < gamepads.length; i++) {
                    if (gamepads[i] && gamepads[i].connected) {
                        gamepad = gamepads[i];
                        break;
                    }
                }
                
                if (!gamepad) {
                    // Kein Controller verbunden, versuche es später erneut
                    requestAnimationId = requestAnimationFrame(checkGamepadStatus);
                    return;
                }
                
                // Überprüfe, ob sich der Controller seit dem letzten Frame aktualisiert hat
                if (gamepad.timestamp === lastTimestamp) {
                    requestAnimationId = requestAnimationFrame(checkGamepadStatus);
                    return;
                }
                
                lastTimestamp = gamepad.timestamp;
                
                // Bewegungsfunktionen mit variabler Distanz basierend auf Joystick/Trigger-Position
                function moveX(value) {
                    // Berechne Distanz basierend auf Joystick-Position (max 10mm)
                    var distance = Math.min(Math.abs(value) * 10, 10).toFixed(1);
                    if (value > 0.1) {
                        self.control.sendJogCommand("x", distance);
                    } else if (value < -0.1) {
                        self.control.sendJogCommand("x", -distance);
                    }
                }

                function moveY(value) {
                    // Berechne Distanz basierend auf Joystick-Position (max 10mm)
                    var distance = Math.min(Math.abs(value) * 10, 10).toFixed(1);
                    if (value > 0.1) {
                        self.control.sendJogCommand("y", distance);
                    } else if (value < -0.1) {
                        self.control.sendJogCommand("y", -distance);
                    }
                }

                function moveZ(value) {
                    // Berechne Distanz basierend auf Joystick-Position/Trigger (max 10mm)
                    var distance = Math.min(Math.abs(value) * 10, 10).toFixed(1);
                    if (value > 0.1) {
                        self.control.sendJogCommand("z", distance);
                    } else if (value < -0.1) {
                        self.control.sendJogCommand("z", -distance);
                    }
                }
                
                function moveExtruder(value) {
                    // Berechne Extruder-Distanz (kleiner als bei XYZ)
                    var distance = Math.min(Math.abs(value) * 5, 5).toFixed(1);
                    if (value > 0.1) {
                        self.control.sendExtrudeCommand(distance);
                    } else if (value < -0.1) {
                        self.control.sendExtrudeCommand(-distance);
                    }
                }
                
                // Controller-Inputs verarbeiten
                
                // Linker Joystick für X/Y-Bewegung mit variabler Distanz
                if (Math.abs(gamepad.axes[0]) > 0.1) {
                    moveX(gamepad.axes[0]);
                }
                if (Math.abs(gamepad.axes[1]) > 0.1) {
                    moveY(-gamepad.axes[1]); // Y-Achse ist invertiert
                }

                // Rechter Joystick für Z-Bewegung mit variabler Distanz
                if (Math.abs(gamepad.axes[3]) > 0.1) {
                    moveZ(-gamepad.axes[3]);
                }

                // Trigger für Z-Bewegung mit variabler Distanz
                // Linker Trigger (LT)
                if (gamepad.buttons[6].value > 0.1) {
                    moveZ(-gamepad.buttons[6].value);
                }
                // Rechter Trigger (RT)
                if (gamepad.buttons[7].value > 0.1) {
                    moveZ(gamepad.buttons[7].value);
                }
                
                // Button-Funktionen
                // A-Button - Home X/Y
                if (gamepad.buttons[0].pressed && !buttonStates[0]) {
                    buttonStates[0] = true;
                    self.control.sendHomeCommand(['x', 'y']);
                } else if (!gamepad.buttons[0].pressed) {
                    buttonStates[0] = false;
                }
                
                // B-Button - Home alle Achsen
                if (gamepad.buttons[1].pressed && !buttonStates[1]) {
                    buttonStates[1] = true;
                    self.control.sendHomeCommand(['x', 'y', 'z']);
                } else if (!gamepad.buttons[1].pressed) {
                    buttonStates[1] = false;
                }
                
                // Extruder-Steuerung mit linkem Joystick (X-Achse)
                if (Math.abs(gamepad.axes[0]) > 0.1) {
                    moveExtruder(gamepad.axes[0]);
                }
                
                // Nächster Frame
                requestAnimationId = requestAnimationFrame(checkGamepadStatus);
            }
            
            // Starte die Gamepad-Überwachung
            checkGamepadStatus();
            
            // Event-Listener für Controller-Verbindungen
            window.addEventListener("gamepadconnected", function(e) {
                console.log("Xbox Controller Plugin: Gamepad verbunden:", e.gamepad.id);
            });
            
            window.addEventListener("gamepaddisconnected", function(e) {
                console.log("Xbox Controller Plugin: Gamepad getrennt:", e.gamepad.id);
            });
            
            // Cleanup-Funktion
            return function cleanup() {
                if (requestAnimationId) {
                    cancelAnimationFrame(requestAnimationId);
                }
            };
        }
        
        // Starte das Gamepad-Setup, wenn das DOM bereit ist
        $(document).ready(function() {
            var cleanup = setupGamepad();
            
            // Bereinige beim Verlassen der Seite
            $(window).on('beforeunload', function() {
                if (cleanup && typeof cleanup === 'function') {
                    cleanup();
                }
            });
        });
    }

    // Stellen Sie sicher, dass die ViewModel-Registrierung korrekt ist
    OCTOPRINT_VIEWMODELS.push({
        construct: XboxControllerViewModel,
        dependencies: ["settingsViewModel", "controlViewModel"],
        elements: ["#tab_plugin_xbox_controller", "#settings_plugin_xbox_controller"]
    });
});
