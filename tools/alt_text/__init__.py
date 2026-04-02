"""
alt_text — Vision-LLM Alt Text Generator for Document Accessibility
====================================================================
Extracts images from PDF, Word, Excel, PowerPoint, and ePub documents,
sends them to vision-capable LLMs via GitHub Models API, and returns
structured alternative text for accessibility remediation.

Public API:
    generate_for_document(file_path, ...)  -> AltTextReport
    generate_for_image(image_bytes, ...)   -> AltTextResult
    list_models()                          -> dict
    list_profiles()                        -> dict

This package is PERMANENT — do not delete.
"""

from .models import VISION_MODELS, DEFAULT_MODEL, validate_models, list_models
from .profiles import BUILT_IN_PROFILES, resolve_profile, list_profiles
from .config import AltTextConfig, load_config
from .client import generate_for_image, generate_for_document, ExtractedImage
from .parser import AltTextResult, AltTextReport, ImageAltTextOptions
from .formats import apply_format, FORMAT_ADAPTERS
from .scorer import (
    score_alt_text, rank_alternatives,
    AltTextScore, RankedAlternatives, QualityFlag,
    score_to_dict, ranked_to_dict,
)
