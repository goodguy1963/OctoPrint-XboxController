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
        self.control = parameters[1];  // ControlViewModel
        
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
            
            // Prüfen, ob ein gespeicherter Testmodus existiert - NACH dem Laden der Einstellungen
            var savedTestMode = localStorage.getItem('xbox_controller_test_mode');
            console.log("Xbox Controller Plugin: Gespeicherter Testmodus:", savedTestMode);
            if (savedTestMode !== null) {
                var testModeEnabled = savedTestMode === 'true';
                self.isTestMode(testModeEnabled);
                console.log("Xbox Controller Plugin: Testmodus aus localStorage geladen:", testModeEnabled);
                
                // Testmodus auf dem Server aktualisieren
                if (testModeEnabled) {
                    self.updateTestModeOnServer(true);
                }
            }
        };

        self.onAfterBinding = function() {
            console.log("Xbox Controller Plugin: onAfterBinding wird aufgerufen");
            console.log("Tab-Element:", $("#tab_plugin_xbox_controller").length);
            console.log("Settings-Element:", $("#settings_plugin_xbox_controller").length);
            
            // Fügen Sie einen sichtbaren Debug-Hinweis hinzu
            $("#tab_plugin_xbox_controller").prepend("<div style='background-color: yellow; padding: 5px; margin-bottom: 10px;'>Debug: ViewModel wurde gebunden</div>");
            
            // Initialisiere Gamepad-System wenn im Browser verfügbar
            if (navigator.getGamepads) {
                self.setupGamepad();
            } else {
                console.warn("Xbox Controller Plugin: Gamepad API nicht unterstützt");
                self.controllerStatus("Gamepad API nicht unterstützt");
            }
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

        self.updateTestModeOnServer = function(enabled) {
            $.ajax({
                url: API_BASEURL + "plugin/xbox_controller",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "toggleTestMode",
                    enabled: enabled
                }),
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    console.log("Xbox Controller Plugin: Testmodus auf Server aktualisiert:", enabled);
                },
                error: function(xhr, status, error) {
                    console.error("Xbox Controller Plugin: Fehler beim Aktualisieren des Testmodus:", error);
                }
            });
        };

        self.toggleTestMode = function() {
            var newState = !self.isTestMode();
            self.isTestMode(newState);
            
            // Speichere Testmodus-Status im localStorage für Seiten-Reloads
            localStorage.setItem('xbox_controller_test_mode', newState.toString());
            console.log("Xbox Controller Plugin: Testmodus gesetzt auf", newState, "und in localStorage gespeichert");
            
            // Aktualisiere auch den Server
            self.updateTestModeOnServer(newState);
            
            // UI-Feedback
            $("#test_mode_indicator").text(newState ? "Aktiv" : "Inaktiv").css("color", newState ? "green" : "red");
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "xbox_controller") return;

            console.log("Xbox Controller Plugin: Nachricht empfangen:", data);

            if (data.type === "status") {
                self.controllerStatus(data.status);
            } else if (data.type === "controller_values") {
                // Immer Werte aktualisieren, aber nur im Testmodus anzeigen
                self.currentX(data.x.toFixed(2));
                self.currentY(data.y.toFixed(2));
                self.currentZ(data.z.toFixed(2));
                self.currentE(data.e.toFixed(2));
                
                // Log values to terminal if in test mode
                if (self.isTestMode()) {
                    console.log("Controller Values:", data);
                }
            }
        };

        // Gamepad-Setup als Methode des ViewModels für bessere Erreichbarkeit
        self.setupGamepad = function() {
            console.log("Xbox Controller Plugin: Gamepad-Setup gestartet");
            
            // Status-Variable für den Controller
            var lastTimestamp = 0;
            var requestAnimationId = null;
            var buttonStates = {}; // Speichert den Status der Buttons, um wiederholtes Auslösen zu vermeiden
            var lastAxesValues = {}; // Speichert die letzten Joystick-Werte, um Spam zu vermeiden
            var activeGamepad = null;
            var frameCounter = 0;
            
            // Prüfe ob ein Gamepad verbunden ist
            function checkGamepadConnection() {
                var gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
                var connectedGamepad = null;
                
                for (var i = 0; i < gamepads.length; i++) {
                    if (gamepads[i] && gamepads[i].connected) {
                        connectedGamepad = gamepads[i];
                        break;
                    }
                }
                
                // Wenn ein Gamepad verbunden ist oder sich der Status geändert hat
                if (connectedGamepad && !activeGamepad) {
                    activeGamepad = connectedGamepad;
                    self.controllerStatus("Verbunden: " + connectedGamepad.id);
                    console.log("Xbox Controller Plugin: Gamepad verbunden -", connectedGamepad.id);
                    startGamepadLoop(); // Fix: Diese Funktion wurde aufgerufen aber nicht definiert
                } else if (!connectedGamepad && activeGamepad) {
                    activeGamepad = null;
                    self.controllerStatus("Nicht verbunden");
                    console.log("Xbox Controller Plugin: Gamepad getrennt");
                    if (requestAnimationId) {
                        cancelAnimationFrame(requestAnimationId);
                        requestAnimationId = null;
                    }
                }
                
                // Regelmäßig erneut prüfen
                setTimeout(checkGamepadConnection, 1000);
            }
            
            // Starte die Gamepad-Überwachungsschleife
            function startGamepadLoop() {
                if (requestAnimationId) {
                    cancelAnimationFrame(requestAnimationId);
                }
                gamepadLoop();
            }
            
            // Funktion zur kontinuierlichen Prüfung des Gamepad-Status
            function gamepadLoop() {
                var gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
                var gamepad = null;
                
                // Finde den aktiven Controller
                for (var i = 0; i < gamepads.length; i++) {
                    if (gamepads[i] && gamepads[i].connected && 
                        (!activeGamepad || gamepads[i].index === activeGamepad.index)) {
                        gamepad = gamepads[i];
                        activeGamepad = gamepad;
                        break;
                    }
                }
                
                if (!gamepad) {
                    self.controllerStatus("Verbindung verloren");
                    requestAnimationId = requestAnimationFrame(gamepadLoop);
                    return;
                }
                
                // Debug-Log für Gamepad-Status
                if (gamepad.timestamp !== lastTimestamp && frameCounter % 60 === 0) {
                    lastTimestamp = gamepad.timestamp;
                    console.log("Xbox Controller Plugin: Gamepad-Update empfangen, Achsen:", 
                                gamepad.axes.length, "Buttons:", gamepad.buttons.length);
                }
                frameCounter++;
                
                // Sammle Daten für den Testmodus
                var controllerData = {
                    x: 0, y: 0, z: 0, e: 0,
                    buttons: {}
                };
                
                try {
                    // Verarbeite Achsenpositionen
                    if (gamepad.axes && gamepad.axes.length >= 4) {
                        // Rechter Joystick X/Y - Bewegung steuern
                        if (Math.abs(gamepad.axes[2]) > 0.1) {
                            controllerData.x = gamepad.axes[2];
                            
                            if (!lastAxesValues.x || Math.abs(lastAxesValues.x - gamepad.axes[2]) > 0.05) {
                                lastAxesValues.x = gamepad.axes[2];
                                
                                // Berechne X-Distanz basierend auf Joystick-Position
                                var distanceX = Math.min(Math.abs(gamepad.axes[2]) * 10, 10).toFixed(1);
                                if (!self.isTestMode()) { // Nur im Nicht-Testmodus bewegen
                                    if (gamepad.axes[2] > 0.1) {
                                        self.control.sendJogCommand("x", distanceX);
                                        console.log("Xbox Controller: X +", distanceX);
                                    } else if (gamepad.axes[2] < -0.1) {
                                        self.control.sendJogCommand("x", -distanceX);
                                        console.log("Xbox Controller: X -", distanceX);
                                    }
                                }
                            }
                        } else {
                            lastAxesValues.x = 0;
                        }
                        
                        if (Math.abs(gamepad.axes[3]) > 0.1) {
                            controllerData.y = gamepad.axes[3];
                            
                            if (!lastAxesValues.y || Math.abs(lastAxesValues.y - gamepad.axes[3]) > 0.05) {
                                lastAxesValues.y = gamepad.axes[3];
                                
                                // Berechne Y-Distanz basierend auf Joystick-Position
                                var distanceY = Math.min(Math.abs(gamepad.axes[3]) * 10, 10).toFixed(1);
                                if (!self.isTestMode()) { // Nur im Nicht-Testmodus bewegen
                                    if (gamepad.axes[3] > 0.1) {
                                        self.control.sendJogCommand("y", -distanceY); // Y-Achse invertieren
                                        console.log("Xbox Controller: Y -", distanceY);
                                    } else if (gamepad.axes[3] < -0.1) {
                                        self.control.sendJogCommand("y", distanceY); // Y-Achse invertieren
                                        console.log("Xbox Controller: Y +", distanceY);
                                    }
                                }
                            }
                        } else {
                            lastAxesValues.y = 0;
                        }
                        
                        // Linker Joystick X - Extruder steuern
                        if (Math.abs(gamepad.axes[0]) > 0.1) {
                            controllerData.e = gamepad.axes[0];
                            
                            if (!lastAxesValues.e || Math.abs(lastAxesValues.e - gamepad.axes[0]) > 0.05) {
                                lastAxesValues.e = gamepad.axes[0];
                                
                                // Berechne Extruder-Distanz (kleiner als bei XYZ)
                                var distanceE = Math.min(Math.abs(gamepad.axes[0]) * 5, 5).toFixed(1);
                                if (!self.isTestMode()) { // Nur im Nicht-Testmodus bewegen
                                    if (gamepad.axes[0] > 0.1) {
                                        self.control.sendExtrudeCommand(distanceE);
                                        console.log("Xbox Controller: Extruder +", distanceE);
                                    } else if (gamepad.axes[0] < -0.1) {
                                        self.control.sendExtrudeCommand(-distanceE);
                                        console.log("Xbox Controller: Extruder -", distanceE);
                                    }
                                }
                            }
                        } else {
                            lastAxesValues.e = 0;
                        }
                    }
                    
                    // Verarbeite Trigger-Positionen für Z-Achse
                    if (gamepad.buttons && gamepad.buttons.length >= 8) {
                        // Linker Trigger (LT)
                        if (gamepad.buttons[6].value > 0.1) {
                            controllerData.z -= gamepad.buttons[6].value; // Negative z-Richtung
                            
                            if (!lastAxesValues.lt || Math.abs(lastAxesValues.lt - gamepad.buttons[6].value) > 0.05) {
                                lastAxesValues.lt = gamepad.buttons[6].value;
                                
                                // Berechne Z-Distanz basierend auf Trigger-Position
                                var distanceZ = Math.min(Math.abs(gamepad.buttons[6].value) * 10, 10).toFixed(1);
                                if (!self.isTestMode()) { // Nur im Nicht-Testmodus bewegen
                                    self.control.sendJogCommand("z", -distanceZ);
                                    console.log("Xbox Controller: Z -", distanceZ);
                                }
                            }
                        } else {
                            lastAxesValues.lt = 0;
                        }
                        
                        // Rechter Trigger (RT)
                        if (gamepad.buttons[7].value > 0.1) {
                            controllerData.z += gamepad.buttons[7].value; // Positive z-Richtung
                            
                            if (!lastAxesValues.rt || Math.abs(lastAxesValues.rt - gamepad.buttons[7].value) > 0.05) {
                                lastAxesValues.rt = gamepad.buttons[7].value;
                                
                                // Berechne Z-Distanz basierend auf Trigger-Position
                                var distanceZ = Math.min(Math.abs(gamepad.buttons[7].value) * 10, 10).toFixed(1);
                                if (!self.isTestMode()) { // Nur im Nicht-Testmodus bewegen
                                    self.control.sendJogCommand("z", distanceZ);
                                    console.log("Xbox Controller: Z +", distanceZ);
                                }
                            }
                        } else {
                            lastAxesValues.rt = 0;
                        }
                    }
                    
                    // Verarbeite Button-Inputs
                    if (gamepad.buttons && gamepad.buttons.length >= 2) {
                        // A-Button - Home X/Y
                        if (gamepad.buttons[0].pressed && !buttonStates[0]) {
                            buttonStates[0] = true;
                            if (!self.isTestMode()) { // Nur im Nicht-Testmodus ausführen
                                self.control.sendHomeCommand(['x', 'y']);
                                console.log("Xbox Controller: Home X/Y");
                            }
                        } else if (!gamepad.buttons[0].pressed) {
                            buttonStates[0] = false;
                        }
                        
                        // B-Button - Home alle Achsen
                        if (gamepad.buttons[1].pressed && !buttonStates[1]) {
                            buttonStates[1] = true;
                            if (!self.isTestMode()) { // Nur im Nicht-Testmodus ausführen
                                self.control.sendHomeCommand(['x', 'y', 'z']);
                                console.log("Xbox Controller: Home alle Achsen");
                            }
                        } else if (!gamepad.buttons[1].pressed) {
                            buttonStates[1] = false;
                        }
                    }
                    
                    // Immer Daten für Test-/Debugzwecke sammeln und aktualisieren
                    // Wichtig: Dies unabhängig vom Testmodus tun
                    self._plugin_manager.send_plugin_message = self._plugin_manager.send_plugin_message || function() {};
                    self._currentX = controllerData.x;
                    self._currentY = controllerData.y;
                    self._currentZ = controllerData.z;
                    self._currentE = controllerData.e;
                    
                    // Aktualisiere die Anzeige
                    self.currentX(controllerData.x.toFixed(2));
                    self.currentY(controllerData.y.toFixed(2));
                    self.currentZ(controllerData.z.toFixed(2));
                    self.currentE(controllerData.e.toFixed(2));
                    
                    // Debug-Log
                    if (self.isTestMode() && (Math.abs(controllerData.x) > 0.1 || Math.abs(controllerData.y) > 0.1 || 
                        Math.abs(controllerData.z) > 0.1 || Math.abs(controllerData.e) > 0.1)) {
                        console.log("Controller Values:", controllerData);
                    }
                } catch (e) {
                    console.error("Xbox Controller Plugin: Fehler bei der Verarbeitung der Gamepad-Daten", e);
                }
                
                // Nächster Frame
                requestAnimationId = requestAnimationFrame(gamepadLoop);
            }
            
            // Event-Listener für Controller-Verbindungen  
            window.addEventListener("gamepadconnected", function(e) {
                console.log("Xbox Controller Plugin: Gamepad verbunden:", e.gamepad.id);
                self.controllerStatus("Verbunden: " + e.gamepad.id);
                activeGamepad = e.gamepad;
                startGamepadLoop();
            });
            
            window.addEventListener("gamepaddisconnected", function(e) {
                console.log("Xbox Controller Plugin: Gamepad getrennt:", e.gamepad.id);
                self.controllerStatus("Nicht verbunden");
                if (activeGamepad && activeGamepad.index === e.gamepad.index) {
                    activeGamepad = null;
                }
            });
            
            // Initiale Prüfung - wichtig, wenn der Controller bereits verbunden ist
            checkGamepadConnection();
            
            // Cleanup-Funktion
            return function cleanup() {
                if (requestAnimationId) {
                    cancelAnimationFrame(requestAnimationId);
                    requestAnimationId = null;
                }
            };
        };
        
        // Starte das Gamepad-Setup, wenn das DOM bereit ist
        $(document).ready(function() {
            var cleanup = self.setupGamepad();
            
            // Bereinige beim Verlassen der Seite
            $(window).on('beforeunload', function() {
                if (cleanup && typeof cleanup === 'function') {
                    cleanup();
                }
            });
        });
        
        // Starte das Gamepad-Setup, wenn das DOM bereit ist
        self.onStartup = function() {
            console.log("Xbox Controller Plugin: onStartup wird aufgerufen");
        };
    }

    // Stellen Sie sicher, dass die ViewModel-Registrierung korrekt ist
    OCTOPRINT_VIEWMODELS.push({
        construct: XboxControllerViewModel,
        dependencies: ["settingsViewModel", "controlViewModel"],
        elements: ["#tab_plugin_xbox_controller", "#settings_plugin_xbox_controller"]
    });
});
