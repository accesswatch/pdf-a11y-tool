"""Heuristic and ML-based auto-tagging engine.

This module implements automatic PDF structure tagging using a combination of
geometric heuristics (font size, position, bounding box analysis) and a
scikit-learn classifier trained on tagged PDF features. It is used by Phase 10.

Planned public API:
    AutoTagger       -- Main auto-tagger class with fit() and tag_document() methods.
    TaggingResult    -- Dataclass holding the proposed tag assignments and confidence scores.
    FeatureExtractor -- Extracts feature vectors from PDF text runs for classification.
"""
from __future__ import annotations
