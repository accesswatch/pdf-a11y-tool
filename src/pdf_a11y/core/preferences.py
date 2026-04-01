"""User settings persistence using platformdirs.

This module manages application preferences (veraPDF path, default DPI,
recent files, UI layout, etc.) using a JSON file stored in the platform-
appropriate user configuration directory via platformdirs.

Planned public API:
    Preferences      -- Dataclass with all application settings and their defaults.
    PreferencesStore -- Loads and saves Preferences to/from the config directory.
                        Provides get(key) and set(key, value) helpers.
"""
from __future__ import annotations
