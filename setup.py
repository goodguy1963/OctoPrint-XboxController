# coding=utf-8
import os
import sys
from setuptools import setup
from setuptools.command.install import install

# Custom install command that sets up proper permissions
class CustomInstall(install):
    def run(self):
        install.run(self)
        # Only run permission setup on Linux systems
        if sys.platform.startswith('linux'):
            self.setup_linux_permissions()

    def setup_linux_permissions(self):
        try:
            import subprocess
            print("Setting up USB permissions for Xbox controller...")
            
            # Create udev rule for Xbox controllers
            rule_path = "/etc/udev/rules.d/99-xbox-controller.rules"
            rule_content = """# Xbox controller permissions
SUBSYSTEM=="input", GROUP="input", MODE="0666"
KERNEL=="js*", GROUP="input", MODE="0666"
KERNEL=="event*", GROUP="input", MODE="0666"
# Xbox controller specific rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", MODE="0666", GROUP="input"
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", MODE="0666", GROUP="input"
"""
            
            # Check if we have permission to write to the udev rules directory
            if os.access("/etc/udev/rules.d", os.W_OK):
                with open(rule_path, "w") as f:
                    f.write(rule_content)
                print(f"Created udev rule: {rule_path}")
                
                # Apply the new rules
                subprocess.call(["udevadm", "control", "--reload-rules"])
                subprocess.call(["udevadm", "trigger"])
                print("USB permissions applied")
            else:
                print("Cannot write to /etc/udev/rules.d - insufficient permissions")
                print("To manually set up USB permissions, run:")
                print("sudo bash -c 'cat > /etc/udev/rules.d/99-xbox-controller.rules << EOL")
                print(rule_content)
                print("EOL'")
                print("sudo udevadm control --reload-rules")
                print("sudo udevadm trigger")
                
            # Try to add current user to input group
            try:
                user = subprocess.check_output(['whoami']).decode('utf-8').strip()
                print(f"Adding user {user} to input group...")
                subprocess.call(["usermod", "-a", "-G", "input", user])
                print(f"Added {user} to input group. A system reboot is recommended.")
            except Exception as e:
                print(f"Could not add user to input group: {str(e)}")
                print("To manually add your user to the input group, run:")
                print("sudo usermod -a -G input $USER")
                print("Then reboot your system")
                
        except Exception as e:
            print(f"Error setting up permissions: {str(e)}")
            print("You may need to manually set up permissions for USB devices")

setup(
    name="OctoPrint-XboxController",
    version="0.1.0",
    description="Ein OctoPrint Plugin zur Steuerung des 3D-Druckers mit einem Xbox-Controller",
    author="3DOffice",
    author_email="postmaster@3doffice.at",
    license="MIT",
    packages=["octoprint_xbox_controller"],
    include_package_data=True,
    cmdclass={
        'install': CustomInstall,
    },
    install_requires=[
        "octoprint>=1.3.0",
        "xbox360controller",
        "pygame>=2.0.0",  # Ensure newer pygame version
        "pyusb",  # Additional USB support
        "evdev",  # Linux input device support
    ],
    entry_points={
        "octoprint.plugin": [
            "octoprint_xbox_controller = octoprint_xbox_controller:XboxControllerPlugin"
        ]
    },
    zip_safe=False,
)
