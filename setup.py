"""py2app setup script for Anki Manager macOS app."""

from setuptools import setup

APP = ["anki_ui.py"]
DATA_FILES: list[str] = []
OPTIONS = {
    "argv_emulation": False,
    "packages": ["flet", "flet_core", "flet_desktop"],
    "includes": ["flet", "flet_core", "flet_desktop"],
    "plist": {
        "CFBundleName": "Anki Manager",
        "CFBundleDisplayName": "Anki Manager",
        "CFBundleIdentifier": "com.anki.manager",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
}

setup(
    name="Anki Manager",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
