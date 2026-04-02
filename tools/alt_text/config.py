"""
config.py — Alt Text Generator Configuration
==============================================
Loads and merges configuration from file, CLI args, and defaults.

This file is PERMANENT — do not delete.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AltTextConfig:
    """Resolved configuration for an alt text generation run."""
    models: list[str] = field(default_factory=lambda: ["openai/gpt-4.1"])
    profile: str = "auto"
    output_format: str = "native"
    max_alt_length: int = 125
    language: str = "en"
    audience: str = ""
    style_guide: str = ""
    context: str = ""
    image_overrides: dict[str, dict] = field(default_factory=dict)
    custom_profiles: dict = field(default_factory=dict)
    min_image_size: int = 50
    skip_duplicate_images: bool = True
    skip_existing_alt: bool = False


def load_config(config_path: str | Path | None = None) -> AltTextConfig:
    """Load configuration from file with fallback to defaults.

    Search order:
      1. Explicit config_path
      2. ./alt-text-generator.json
      3. ~/.config/alt-text-generator/config.json
      4. Built-in defaults

    Args:
        config_path: Explicit path to config file (optional).

    Returns:
        Resolved AltTextConfig.
    """
    data = {}

    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    else:
        search_paths.append(Path.cwd() / "alt-text-generator.json")
        search_paths.append(
            Path.home() / ".config" / "alt-text-generator" / "config.json"
        )

    for p in search_paths:
        if p.exists() and p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass  # Fall through to defaults
            break

    defaults = data.get("defaults", {})
    extraction = data.get("extraction", {})

    return AltTextConfig(
        models=defaults.get("models", ["openai/gpt-4.1"]),
        profile=defaults.get("profile", "auto"),
        output_format=defaults.get("output_format", "native"),
        max_alt_length=defaults.get("max_alt_length", 125),
        language=defaults.get("language", "en"),
        audience=defaults.get("audience", ""),
        style_guide=defaults.get("style_guide", ""),
        context=defaults.get("context", ""),
        custom_profiles=data.get("profiles", {}),
        min_image_size=extraction.get("min_image_size", 50),
        skip_duplicate_images=extraction.get("skip_duplicate_images", True),
        skip_existing_alt=extraction.get("skip_existing_alt", False),
    )


def merge_config(base: AltTextConfig, **overrides) -> AltTextConfig:
    """Merge overrides into a base config (overrides win)."""
    import dataclasses
    merged = dataclasses.asdict(base)
    for key, val in overrides.items():
        if val is not None and val != "" and key in merged:
            merged[key] = val
    return AltTextConfig(**merged)
