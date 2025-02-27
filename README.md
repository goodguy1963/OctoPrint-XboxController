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
- [Connection Methods](#connection-methods)
- [Controller Detection Methods](#controller-detection-methods)
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
- **Flexible Connection Options**: Use controller connected to your Pi OR through the browser

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

## 🎮 Connection Methods

This plugin is designed with flexibility in mind, providing two ways to use your Xbox controller with OctoPrint:

### 1. Direct Connection to Raspberry Pi/OctoPrint Server (Recommended)

![Direct Connection](https://raw.githubusercontent.com/goodguy1963/OctoPrint-XboxController/main/assets/direct_connection.png)

- **Setup**: Simply plug your Xbox controller directly into a USB port on your Raspberry Pi or OctoPrint server
- **Advantages**:
  - ✅ Works even when the browser is closed
  - ✅ Lower latency for responsive control
  - ✅ Works with any device accessing OctoPrint (phone, tablet, desktop)
  - ✅ No browser compatibility concerns
  - ✅ No need for the controller to be connected to your browsing device
- **USB Permissions**: Automatically set up during installation on Linux systems
- **Best For**: Permanent 3D printer setups where the Pi is easily accessible

### 2. Connection through Browser

![Browser Connection](https://raw.githubusercontent.com/goodguy1963/OctoPrint-XboxController/main/assets/browser_connection.png)

- **Setup**: Connect the Xbox controller to the device that's running your browser
- **How it Works**: Controller inputs are captured by the browser and sent to OctoPrint
- **Advantages**:
  - ✅ No need to physically access the Raspberry Pi/server
  - ✅ Useful for remote operation scenarios
  - ✅ Great when your OctoPrint server isn't easily accessible
  - ✅ Works well for Windows OctoPrint installations
- **Requirements**: Browser with Gamepad API support (Chrome, Firefox, Edge recommended)
- **Best For**: Remote printing management or when physical access to the server is limited

### Using Both Methods Simultaneously

The plugin automatically detects which connection method is active and will prioritize them accordingly. You can seamlessly switch between methods without changing any settings.

## 🕹️ Controller Detection Methods

This plugin supports multiple ways to detect and connect to your controller:

### Auto Detection (Default)

- The plugin will automatically choose the best detection method for your system
- On Linux/Raspberry Pi: First tries evdev, then falls back to pygame if needed
- On Windows/macOS: Uses pygame for controller detection
- **Best For**: Most users who want a "plug and play" experience

### Evdev (Linux Only)

- Uses Linux's native evdev interface for direct controller access
- **Advantages**:
  - ✅ Low-level access with minimal overhead
  - ✅ Better support for a variety of controllers
  - ✅ Reliable reconnection if controller is unplugged
- **Requirements**: Python evdev package (automatically installed)
- **Best For**: Linux/Raspberry Pi users who need maximum reliability

### PyGame

- Uses the pygame library for controller detection and input
- **Advantages**:
  - ✅ Cross-platform support (Windows, macOS, Linux)
  - ✅ Wide controller compatibility
- **Best For**: Windows and macOS users, or when evdev isn't available

### XBoxDrv (Experimental)

- Uses the xboxdrv driver specifically for Xbox controllers
- **Advantages**:
  - ✅ Specialized support for Xbox controllers
  - ✅ May support controllers that other methods don't
- **Requirements**: xboxdrv must be installed on your system
- **Best For**: Advanced users with Xbox controllers that aren't detected by other methods

## 🖥️ Platform Compatibility

### Raspberry Pi / Linux
- Best experience with controllers physically connected to the Raspberry Pi
- USB permissions are automatically configured during installation
- Supports both evdev and pygame detection methods
- Controllers can be detected even if not connected to the browsing device

### Windows
- Supports controllers connected directly to the Windows OctoPrint server
- Browser-based detection provides a reliable fallback option
- Best performance with Xbox branded controllers
- Works with both USB and wireless Xbox controllers

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
- **Max Z Height**: Sets a safety limit for Z axis movement (default: 100mm)
- **Controller Detection Method**: Choose between automatic, evdev (Linux only), or pygame
- **Enable Debug Logging**: Turn on detailed logging for troubleshooting
- **Auto Reconnect**: Automatically try to reconnect to controller if connection is lost

Higher values increase sensitivity, while lower values provide finer control.

## 🧪 Test Mode

The test mode can be activated via the "Xbox Controller" tab. In this mode:
- Controller inputs are displayed in real-time
- No movement commands are sent to the printer
- The mode persists between browser sessions
- Great for testing controller connectivity and response

## 🛠️ Troubleshooting

### Direct USB Connection Issues

#### On Raspberry Pi / Linux:
1. Verify the controller is properly connected:
   ```bash
   # List USB devices
   lsusb
   ```

2. Check user permissions (should be set automatically during installation):
   ```bash
   # Add your user to the input group if needed
   sudo usermod -a -G input $USER
   # Log out and log back in for changes to take effect
   ```

3. Verify device access:
   ```bash
   # List input devices
   ls -l /dev/input/js*
   ls -l /dev/input/event*
   ```

4. Test controller detection directly:
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

### Browser Connection Issues
1. Verify the controller works in other browser applications
2. Try the controller connection test at https://gamepad-tester.com/
3. Ensure you're using a compatible browser (Chrome, Firefox, Edge recommended)
4. Check browser console (F12) for any JavaScript errors related to gamepad
5. Try restarting your browser or using a private/incognito window
6. Allow browser permissions if prompted
7. On Windows, make sure Xbox accessories app isn't interfering

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
- **Multiple Controllers**: The plugin currently works best with a single controller connected per connection method.
- **Wireless Controllers**: Some wireless controllers may have connection issues or increased latency.
- **UI Element Display**: In some cases, UI elements may not display correctly. Clear your browser cache or try a different browser.
- **Settings Loading**: If settings fail to load, try restarting OctoPrint or reinstalling the plugin.

## ❓ FAQ

**Q: Can I use the controller both directly connected to the Pi and through my browser?**  
A: Yes! The plugin will detect both connection methods and show you which one is active.

**Q: Can I use a PlayStation/Generic controller instead of Xbox?**  
A: Yes, most controllers that work with your operating system should work, though button mapping may differ.

**Q: Does this work with OctoPi/OctoPrint on a Raspberry Pi?**  
A: Yes, this is the primary development platform and works best on Raspberry Pi.

**Q: Can I use this while printing?**  
A: The plugin has safety features that prevent movement commands during active printing.

**Q: Will the controller work if connected to my PC instead of the Raspberry Pi?**  
A: Yes, through browser detection. The plugin will automatically use your PC-connected controller to control the printer.

**Q: Do I need to set up USB permissions manually?**  
A: No, the plugin attempts to set up required permissions during installation. Only if that fails would manual setup be needed.

**Q: Which detection method should I use?**  
A: Start with "Auto" and let the plugin decide. If you experience issues, try evdev on Linux or pygame on Windows/macOS.

**Q: Can I adjust how sensitive the controller is?**  
A: Yes, use the Scale Factors in the plugin settings to adjust sensitivity for each axis.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## 📜 License

This project is licensed under the MIT License.