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
- [Platform Compatibility](#platform-compatibility)
- [Controller Mapping](#controller-mapping)
- [Configuration](#configuration)
- [Test Mode](#test-mode)
- [Troubleshooting](#troubleshooting)
- [Known Issues](#known-issues)
- [FAQ](#faq)
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
- **Multi-Platform Support**: Works on Linux (Raspberry Pi) and Windows systems
- **Dual Detection Methods**: Controller can be detected via browser or directly on the OctoPrint server

## 🔧 Requirements

- OctoPrint 1.3.0 or newer
- Python 3.x
- Xbox controller or compatible gamepad
- Pygame library (automatically installed with the plugin)
- For Linux: `evdev` package (optional but recommended for better controller detection)

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
4. Install the required dependencies:
   ```bash
   pip install pygame
   ```
5. On Linux, install the optional evdev package for better controller support:
   ```bash
   sudo apt-get install python3-evdev
   ```
6. Restart OctoPrint

## 🖥️ Platform Compatibility

### Raspberry Pi / Linux
- Best experience with controllers physically connected to the Raspberry Pi
- Requires proper user permissions (see Troubleshooting section)
- Supports both evdev and pygame detection methods
- Controllers can be detected even if not connected to the browsing device

### Windows
- Supports controllers connected to the OctoPrint server
- Browser-based detection as fallback
- Best performance with Xbox branded controllers

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

- **XY Scaling Factor**: Affects the sensitivity of X/Y movement (default: 150)
- **Z Scaling Factor**: Affects the sensitivity of Z movement (default: 150)
- **E Scaling Factor**: Affects the sensitivity of extruder movement (default: 150)
- **Controller Detection Method**: Choose between automatic, evdev (Linux only), or pygame

Higher values increase sensitivity, while lower values provide finer control.

## 🧪 Test Mode

The test mode can be activated via the "Xbox Controller" tab. In this mode:
- Controller inputs are displayed in real-time
- No movement commands are sent to the printer
- The mode persists between browser sessions
- Great for testing controller connectivity and response

## 🛠️ Troubleshooting

### Controller Not Detected

#### On Raspberry Pi / Linux:
1. Check user permissions:
   ```bash
   # Add your user to the input group
   sudo usermod -a -G input $USER
   # Log out and log back in for changes to take effect
   ```

2. Verify device access:
   ```bash
   # List input devices
   ls -l /dev/input/js*
   ls -l /dev/input/event*
   ```

3. Test controller detection:
   ```bash
   # For evdev
   python3 -c "import evdev; print(evdev.list_devices())"
   # For pygame
   python3 -c "import pygame; pygame.init(); pygame.joystick.init(); print(pygame.joystick.get_count())"
   ```

#### On Windows:
1. Test in Windows Game Controllers panel (Press Win+R, type 'joy.cpl')
2. Ensure controller is recognized by Windows before using with OctoPrint
3. Try a different USB port
4. Update controller drivers

### UI Elements Not Displaying
1. Clear browser cache and reload the page
2. Check browser console for JavaScript errors (press F12)
3. Ensure JavaScript is enabled in your browser
4. Verify other OctoPrint plugins are functioning correctly
5. Check OctoPrint logs for error messages (Settings > Logs)
6. Restart the OctoPrint server
7. Try a different browser

### Movement Issues
1. Verify controller is properly calibrated in your OS
2. Adjust scaling factors in plugin settings
3. Ensure the controller is not in test mode
4. Check if printer is operational and not currently printing
5. Verify printer connection in OctoPrint

## 🐞 Known Issues

- **Browser Compatibility**: Some browsers may have issues with the Gamepad API. Chrome and Firefox are recommended.
- **Controller Reconnection**: Occasionally, a manual restart of OctoPrint may be required after reconnecting a controller.
- **Multiple Controllers**: The plugin currently works best with a single controller connected.
- **Wireless Controllers**: Some wireless controllers may have connection issues or increased latency.
- **UI Element Display**: In some cases, UI elements may not display correctly. Clear your browser cache or try a different browser.
- **Settings Loading**: If settings fail to load, try restarting OctoPrint or reinstalling the plugin.

## ❓ FAQ

**Q: Can I use a PlayStation/Generic controller instead of Xbox?**  
A: Yes, most controllers that work with your operating system should work, though button mapping may differ.

**Q: Does this work with OctoPi/OctoPrint on a Raspberry Pi?**  
A: Yes, this is the primary development platform and works best on Raspberry Pi.

**Q: Can I use this while printing?**  
A: The plugin has safety features that prevent movement commands during active printing.

**Q: Will the controller work if connected to my PC instead of the Raspberry Pi?**  
A: Yes, through browser detection, but for best results connect directly to the OctoPrint server.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## 📜 License

This project is licensed under the MIT License.
