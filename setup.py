# coding=utf-8
from setuptools import setup

setup(
    name="OctoPrint-XboxController",
    version="0.1.0",
    description="Ein OctoPrint Plugin zur Steuerung des 3D-Druckers mit einem Xbox-Controller",
    author="3DOffice",
    author_email="postmaster@3doffice.at",
    license="MIT",
    packages=["octoprint_xbox_controller"],
    include_package_data=True,
    install_requires=[
        "octoprint>=1.3.0",
        "xbox360controller",
        "pygame>=2.0.0"  # Ensure newer pygame version
    ],
    entry_points={
        "octoprint.plugin": [
            "octoprint_xbox_controller = octoprint_xbox_controller:XboxControllerPlugin"
        ]
    },
    zip_safe=False,
)
