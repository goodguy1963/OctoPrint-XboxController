# 🎮 OctoPrint Xbox Controller Plugin

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.x-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Control your 3D printer directly with an Xbox controller through OctoPrint!

![Xbox Controller Plugin](https://raw.githubusercontent.com/goodguy1963/OctoPrint-XboxController/main/assets/controller_banner.png)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Controller Mapping](#controller-mapping)
- [Configuration](#configuration)
- [Test Mode](#test-mode)
- [Troubleshooting](#troubleshooting)
- [Known Issues](#known-issues)
- [Contributing](#contributing)
- [License](#license)

## 📌 Overview

This plugin provides intuitive control of your 3D printer using an Xbox controller connected to your OctoPrint server. Enjoy precise movements, variable speed control, and customizable settings for a seamless printing experience.

## ✨ Features

- **Intuitive Movement Control**: Control X, Y, Z axes with joysticks and triggers
- **Extruder Control**: Manage filament extrusion with the left joystick
- **Variable Speed**: Movement speed adjusts based on joystick position (up to 10mm)
- **One-Touch Homing**: Quick homing functions with dedicated buttons
- **Test Mode**: Verify controller inputs without sending commands to the printer
- **Customizable Sensitivity**: Adjust response curves for different control styles

## 🔧 Requirements

- OctoPrint 1.3.0 or newer
- Python 3.x
- Xbox controller or compatible gamepad
- Pygame library (automatically installed with the plugin)

## 📥 Installation

### Method 1: OctoPrint Plugin Manager

1. Open OctoPrint in your browser
2. Navigate to Settings → Plugin Manager → Get More...
3. Enter `XboxController` in the search box or paste this URL:
   ```
   https://github.com/goodguy1963/OctoPrint-XboxController/archive/BUGFIX.zip
   ```
4. Click "Install"
5. Restart OctoPrint when prompted

### Method 2: Manual Installation

1. Download the plugin from the GitHub repository
2. Extract the downloaded ZIP file
3. Copy the extracted folder to the OctoPrint plugins directory
4. Restart OctoPrint

## 🎮 Controller Mapping

### Movement Control
- **Right Joystick**: X/Y-axis movement
  - Left/Right: X-axis
  - Forward/Backward: Y-axis
- **Trigger Buttons**: Z-axis movement
  - Right Trigger (RT): Z-axis up
  - Left Trigger (LT): Z-axis down
- **Left Joystick**: Extruder control
  - Left/Right: Retract/extrude filament

### Buttons
- **A Button**: Home X/Y axes
- **B Button**: Full auto home (X, Y, Z)

## ⚙️ Configuration

In the plugin settings, you can adjust the following parameters:

- XY Scaling Factor: Affects the sensitivity of X/Y movement
- Z Scaling Factor: Affects the sensitivity of Z movement
- E Scaling Factor: Affects the sensitivity of extruder movement

## 🧪 Test Mode

The test mode can be activated via the "Xbox Controller" tab. In this mode, controller inputs are displayed without sending actual movement commands to the printer.

## 🛠️ Troubleshooting

- **Controller not recognized**: Ensure the controller is properly connected and recognized by your system.
- **Unexpected movements**: Check joystick calibration and adjust scaling factors.
- **Plugin not starting**: Check OctoPrint logs for error messages.
- **UI elements not displaying**:
  - Clear browser cache and reload the page
  - Check browser console for JavaScript errors (press F12)
  - Ensure JavaScript is enabled in your browser
  - Verify other OctoPrint plugins are functioning correctly
  - Check OctoPrint logs for error messages (Settings > Logs)
  - Restart the OctoPrint server
  - Uninstall and reinstall the plugin
  - Try a different browser

## 🐞 Known Issues

- **Missing UI elements**: In some cases, UI elements may not display correctly. The current BUGFIX version addresses this issue with improved template binding and debug outputs.
- **Settings not loading**: The BUGFIX version includes more robust error handling when loading settings.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## 📜 License

This project is licensed under the MIT License.