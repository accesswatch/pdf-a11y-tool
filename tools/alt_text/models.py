"""
models.py — Vision-Capable Model Registry for GitHub Models API
================================================================
Hard-coded allow-list of vision models validated against the GitHub
Models marketplace. Every model ID is checked before API calls.

This file is PERMANENT — do not delete.
"""

# ---------------------------------------------------------------------------
# Vision model registry
# ---------------------------------------------------------------------------

VISION_MODELS: dict[str, dict] = {
    # OpenAI GPT-4.1 family (primary recommended)
    "openai/gpt-4.1": {
        "name": "GPT-4.1",
        "description": "Best quality vision model, highest accuracy for complex images",
        "tier": "low",
        "vision": True,
        "cost": "high",
        "recommended": True,
    },
    "openai/gpt-4.1-mini": {
        "name": "GPT-4.1 Mini",
        "description": "Good quality, lower cost -- best balance for batch processing",
        "tier": "low",
        "vision": True,
        "cost": "medium",
        "recommended": True,
    },
    "openai/gpt-4.1-nano": {
        "name": "GPT-4.1 Nano",
        "description": "Fastest and cheapest -- acceptable for simple images",
        "tier": "low",
        "vision": True,
        "cost": "low",
        "recommended": False,
    },

    # OpenAI GPT-4o family
    "openai/gpt-4o": {
        "name": "GPT-4o",
        "description": "Strong multimodal model, excellent vision capabilities",
        "tier": "low",
        "vision": True,
        "cost": "high",
        "recommended": True,
    },
    "openai/gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "description": "Lightweight multimodal, good for simple images",
        "tier": "low",
        "vision": True,
        "cost": "low",
        "recommended": False,
    },

    # OpenAI GPT-5 family
    "openai/gpt-5": {
        "name": "GPT-5",
        "description": "Latest generation, logic-heavy and multi-step tasks",
        "tier": "high",
        "vision": True,
        "cost": "highest",
        "recommended": False,
    },
    "openai/gpt-5-mini": {
        "name": "GPT-5 Mini",
        "description": "Lightweight GPT-5 for cost-sensitive vision tasks",
        "tier": "high",
        "vision": True,
        "cost": "high",
        "recommended": False,
    },
    "openai/gpt-5-nano": {
        "name": "GPT-5 Nano",
        "description": "Optimized for speed and low latency",
        "tier": "high",
        "vision": True,
        "cost": "medium",
        "recommended": False,
    },

    # Microsoft Phi-4 multimodal
    "microsoft/Phi-4-multimodal-instruct": {
        "name": "Phi-4 Multimodal",
        "description": "Small multimodal model (text + image + audio), efficient",
        "tier": "low",
        "vision": True,
        "cost": "low",
        "recommended": False,
    },
}

DEFAULT_MODEL = "openai/gpt-4.1"
MAX_MODELS_PER_REQUEST = 5


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ModelNotAllowedError(ValueError):
    """Raised when a model ID is not in the vision model registry."""
    pass


def validate_models(models: list[str] | None) -> list[str]:
    """Validate and deduplicate a list of model IDs.

    Args:
        models: List of model identifiers. None or empty = use default.

    Returns:
        Deduplicated list of valid model IDs.

    Raises:
        ModelNotAllowedError: If a model ID is not in VISION_MODELS.
        ValueError: If more than MAX_MODELS_PER_REQUEST models are requested.
    """
    if not models:
        return [DEFAULT_MODEL]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for m in models:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    if len(unique) > MAX_MODELS_PER_REQUEST:
        raise ValueError(
            f"Too many models ({len(unique)}). Maximum is {MAX_MODELS_PER_REQUEST} "
            f"per request to limit API costs."
        )

    invalid = [m for m in unique if m not in VISION_MODELS]
    if invalid:
        valid_list = "\n".join(
            f"  - {mid}: {info['name']} -- {info['description']}"
            for mid, info in VISION_MODELS.items()
            if info.get("vision", False)
        )
        raise ModelNotAllowedError(
            f"Unknown model(s): {', '.join(invalid)}\n\n"
            f"Valid vision models:\n{valid_list}"
        )

    # Verify all are vision-capable
    non_vision = [m for m in unique if not VISION_MODELS[m].get("vision", False)]
    if non_vision:
        raise ModelNotAllowedError(
            f"Model(s) not vision-capable: {', '.join(non_vision)}"
        )

    return unique


def list_models() -> dict:
    """Return the model registry for display."""
    return {
        "default": DEFAULT_MODEL,
        "max_per_request": MAX_MODELS_PER_REQUEST,
        "models": {
            mid: {
                "name": info["name"],
                "description": info["description"],
                "cost": info["cost"],
                "tier": info["tier"],
                "recommended": info["recommended"],
            }
            for mid, info in VISION_MODELS.items()
            if info.get("vision", False)
        },
    }
