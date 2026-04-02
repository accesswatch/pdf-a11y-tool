"""
profiles.py — Alt Text Profiles
=================================
Built-in and custom alt text profiles controlling what kind of
description the LLM generates for different image types.

This file is PERMANENT — do not delete.
"""

# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

BUILT_IN_PROFILES: dict[str, dict] = {
    "auto": {
        "description": "Default. LLM determines the image type and applies the appropriate strategy.",
        "prompt": (
            "Determine whether this image is informative, decorative, functional, "
            "a chart/graph, a text image, or a logo. Apply the appropriate alt text strategy."
        ),
    },
    "informative": {
        "description": "Photos, illustrations that convey content.",
        "prompt": "Describe what this image communicates in its surrounding context.",
    },
    "data": {
        "description": "Charts, graphs, tables, diagrams.",
        "prompt": (
            "Describe the data trend, key takeaway, and axis labels. "
            "Do not enumerate every data point."
        ),
    },
    "decorative": {
        "description": "Borders, spacers, background patterns.",
        "prompt": 'This image is decorative. Return alt="".',
    },
    "functional": {
        "description": "Images inside links or buttons.",
        "prompt": "Describe the action or destination, not the image's appearance.",
    },
    "text": {
        "description": "Images containing readable text.",
        "prompt": "Reproduce the text content visible in the image exactly.",
    },
    "logo": {
        "description": "Brand marks, company logos.",
        "prompt": "Identify the organization. Do not describe the graphic design.",
    },
    "complex": {
        "description": "Infographics, multi-part diagrams.",
        "prompt": (
            "Provide a thorough description of all meaningful visual information. "
            "The detailed description may be longer than usual."
        ),
    },
}


class ProfileNotFoundError(ValueError):
    """Raised when a profile name is not recognized."""
    pass


def resolve_profile(name: str, custom_profiles: dict | None = None) -> dict:
    """Resolve a profile name to its definition.

    Args:
        name: Profile name (built-in or custom).
        custom_profiles: Optional dict of custom profile definitions.

    Returns:
        Profile dict with 'description' and 'prompt' keys.

    Raises:
        ProfileNotFoundError: If the name is not found.
    """
    if not name:
        name = "auto"

    # Check built-in first, then custom
    if name in BUILT_IN_PROFILES:
        return BUILT_IN_PROFILES[name]

    if custom_profiles and name in custom_profiles:
        profile = custom_profiles[name]
        if "prompt" not in profile:
            raise ProfileNotFoundError(
                f"Custom profile '{name}' is missing required 'prompt' field."
            )
        return profile

    all_names = list(BUILT_IN_PROFILES.keys())
    if custom_profiles:
        all_names.extend(custom_profiles.keys())
    raise ProfileNotFoundError(
        f"Unknown profile '{name}'. Available profiles: {', '.join(all_names)}"
    )


def list_profiles(custom_profiles: dict | None = None) -> dict:
    """Return all available profiles for display."""
    result = {}
    for name, info in BUILT_IN_PROFILES.items():
        result[name] = {
            "description": info["description"],
            "type": "built-in",
        }
    if custom_profiles:
        for name, info in custom_profiles.items():
            result[name] = {
                "description": info.get("description", "Custom profile"),
                "type": "custom",
            }
    return result
