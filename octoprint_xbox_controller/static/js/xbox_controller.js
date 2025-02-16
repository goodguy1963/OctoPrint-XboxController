$(function() {
    function XboxControllerViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];
        
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

        // Update Handler für Skalierungsfaktoren
        self.xyScaleFactor.subscribe(function(newValue) {
            self.updateScaleFactor('xy', newValue);
        });
        
        self.zScaleFactor.subscribe(function(newValue) {
            self.updateScaleFactor('z', newValue);
        });
        
        self.eScaleFactor.subscribe(function(newValue) {
            self.updateScaleFactor('e', newValue);
        });

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

        // Initialisiere Werte aus den Settings
        self.onSettingsBeforeLoad = function() {
            self.xyScaleFactor(self.settings.settings.plugins.xbox_controller.xy_scale_factor());
            self.zScaleFactor(self.settings.settings.plugins.xbox_controller.z_scale_factor());
            self.eScaleFactor(self.settings.settings.plugins.xbox_controller.e_scale_factor());
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: XboxControllerViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#tab_plugin_xbox_controller"]
    });
});
