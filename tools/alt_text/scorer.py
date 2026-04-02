"""
scorer.py -- Alt Text Quality Scoring and Ranking
===================================================
Evaluates alt text quality against WCAG 2.2 guidelines, scores 0-100,
and ranks multiple alternatives from different models.

Scoring criteria:
  - Length (too short < 10 chars, ideal 30-125 chars, too long > 250)
  - Anti-patterns ("image of", "picture of", "photo of" prefixes)
  - Filename/path detection (alt text that is just a filename)
  - Placeholder detection ("alt text", "description", "TODO")
  - Specificity (contains descriptive nouns/adjectives vs vague text)
  - Redundancy with surrounding context
  - Starts with capital letter / proper sentence structure

This file is PERMANENT -- do not delete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

IDEAL_MIN_LENGTH = 30
IDEAL_MAX_LENGTH = 125
HARD_MAX_LENGTH = 250

# Prefixes that screen readers already announce (redundant)
_REDUNDANT_PREFIXES = re.compile(
    r"^(image|picture|photo|graphic|icon|logo|illustration|diagram|"
    r"screenshot|figure|img|pic)\s+(of|showing|depicting|displaying)\s+",
    re.IGNORECASE,
)

# Filenames or paths used as alt text
_FILENAME_PATTERN = re.compile(
    r"^[\w\-./\\]+\.(png|jpg|jpeg|gif|bmp|svg|tiff?|webp|avif|ico)$",
    re.IGNORECASE,
)

# Placeholder / meaningless text
_PLACEHOLDER_PATTERNS = [
    re.compile(r"^(alt\s*text|description|image|photo|picture|graphic|untitled|"
               r"placeholder|todo|tbd|fixme|replace\s+me|insert\s+(alt|description)|"
               r"img_?\d+|image_?\d+|dsc_?\d+|screenshot_?\d+)\.?$", re.IGNORECASE),
    re.compile(r"^\s*$"),  # empty/whitespace
]

# Characters that suggest machine-generated junk
_JUNK_CHARS = re.compile(r"[{}\[\]<>|\\]")

# Words that indicate specificity
_SPECIFICITY_INDICATORS = re.compile(
    r"\b(chart|graph|table|map|form|button|link|menu|"
    r"bar|pie|line|scatter|histogram|"
    r"person|people|student|teacher|staff|"
    r"building|campus|room|office|"
    r"showing|displaying|containing|"
    r"red|blue|green|yellow|orange|purple|black|white|"
    r"left|right|top|bottom|center|"
    r"labeled|titled|heading|section|"
    r"percent|percentage|increase|decrease|trend|comparison)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Quality flags
# ---------------------------------------------------------------------------

@dataclass
class QualityFlag:
    """A single quality observation about an alt text."""
    code: str                # e.g. "TOO_SHORT", "REDUNDANT_PREFIX"
    severity: str            # "error", "warning", "info"
    message: str             # Human-readable explanation
    deduction: int           # Points deducted (0-30)


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

@dataclass
class AltTextScore:
    """Quality assessment for a single alt text string."""
    text: str
    score: int               # 0-100
    flags: list[QualityFlag] = field(default_factory=list)
    model: str = ""
    rank: int = 0            # 1-based rank among alternatives (0 = unranked)


def score_alt_text(
    text: str,
    model: str = "",
    context: str = "",
) -> AltTextScore:
    """Score a single alt text string for WCAG quality.

    Args:
        text: The alt text to evaluate.
        model: Model name that produced this text (for labeling).
        context: Surrounding text (for redundancy checking).

    Returns:
        AltTextScore with score 0-100 and quality flags.
    """
    flags: list[QualityFlag] = []
    score = 100

    stripped = (text or "").strip()

    # -- Empty / missing ------------------------------------------------------
    if not stripped:
        flags.append(QualityFlag("MISSING", "error",
                                 "Alt text is empty or missing.", 100))
        return AltTextScore(text=text, score=0, flags=flags, model=model)

    # -- Placeholder detection ------------------------------------------------
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.match(stripped):
            flags.append(QualityFlag("PLACEHOLDER", "error",
                                     "Alt text appears to be placeholder text.", 60))
            score -= 60
            break

    # -- Filename detection ---------------------------------------------------
    if _FILENAME_PATTERN.match(stripped):
        flags.append(QualityFlag("FILENAME", "error",
                                 "Alt text is a filename, not a description.", 50))
        score -= 50

    # -- Redundant prefix ("image of ...") ------------------------------------
    m = _REDUNDANT_PREFIXES.match(stripped)
    if m:
        flags.append(QualityFlag("REDUNDANT_PREFIX", "warning",
                                 f"Starts with \"{m.group(0).strip()}\" -- "
                                 "screen readers already announce 'image'.", 10))
        score -= 10

    # -- Length checks --------------------------------------------------------
    length = len(stripped)
    if length < 10:
        flags.append(QualityFlag("TOO_SHORT", "warning",
                                 f"Very short ({length} chars). "
                                 "May not convey enough information.", 15))
        score -= 15
    elif length < IDEAL_MIN_LENGTH:
        flags.append(QualityFlag("SHORT", "info",
                                 f"Somewhat short ({length} chars). "
                                 f"Ideal range is {IDEAL_MIN_LENGTH}-{IDEAL_MAX_LENGTH}.", 5))
        score -= 5
    elif length > HARD_MAX_LENGTH:
        flags.append(QualityFlag("TOO_LONG", "warning",
                                 f"Very long ({length} chars). "
                                 "Consider moving detail to a long description.", 10))
        score -= 10
    elif length > IDEAL_MAX_LENGTH:
        flags.append(QualityFlag("LONG", "info",
                                 f"Longer than ideal ({length} chars). "
                                 f"Target is under {IDEAL_MAX_LENGTH}.", 3))
        score -= 3

    # -- Junk characters ------------------------------------------------------
    if _JUNK_CHARS.search(stripped):
        flags.append(QualityFlag("JUNK_CHARS", "warning",
                                 "Contains characters unusual in alt text "
                                 "(brackets, pipes, backslashes).", 10))
        score -= 10

    # -- Specificity bonus / penalty -----------------------------------------
    specificity_matches = len(_SPECIFICITY_INDICATORS.findall(stripped))
    if specificity_matches == 0 and length >= IDEAL_MIN_LENGTH:
        flags.append(QualityFlag("LOW_SPECIFICITY", "info",
                                 "No specific content descriptors detected. "
                                 "May be too vague.", 5))
        score -= 5
    elif specificity_matches >= 3:
        flags.append(QualityFlag("HIGH_SPECIFICITY", "info",
                                 "Good level of descriptive detail.", 0))

    # -- Redundancy with context ---------------------------------------------
    if context and stripped.lower() in context.lower():
        flags.append(QualityFlag("REDUNDANT_CONTEXT", "warning",
                                 "Alt text duplicates surrounding text exactly. "
                                 "Consider a shorter reference or mark decorative.", 15))
        score -= 15

    # -- Sentence structure --------------------------------------------------
    if stripped[0].islower() and length >= 20:
        flags.append(QualityFlag("NO_CAPITAL", "info",
                                 "Does not start with a capital letter.", 2))
        score -= 2

    return AltTextScore(
        text=text,
        score=max(0, min(100, score)),
        flags=flags,
        model=model,
    )


# ---------------------------------------------------------------------------
# Rank and compare multiple alternatives
# ---------------------------------------------------------------------------

@dataclass
class RankedAlternatives:
    """Ranked set of alt text options for a single image."""
    existing: AltTextScore | None = None
    alternatives: list[AltTextScore] = field(default_factory=list)
    recommendation: str = ""


def rank_alternatives(
    existing_alt: str | None,
    alternatives: list[tuple[str, str]],  # [(model, alt_text), ...]
    context: str = "",
) -> RankedAlternatives:
    """Score and rank existing alt text alongside model-generated alternatives.

    Args:
        existing_alt: Current alt text on the image (None if missing).
        alternatives: List of (model_name, alt_text) tuples from different models.
        context: Surrounding text for redundancy checking.

    Returns:
        RankedAlternatives with scored/ranked options and a recommendation.
    """
    result = RankedAlternatives()

    # Score existing
    if existing_alt is not None:
        result.existing = score_alt_text(existing_alt, model="(existing)", context=context)

    # Score alternatives
    scored = []
    for model, alt in alternatives:
        s = score_alt_text(alt, model=model, context=context)
        scored.append(s)

    # Sort by score descending
    scored.sort(key=lambda s: s.score, reverse=True)

    # Assign ranks
    for i, s in enumerate(scored, 1):
        s.rank = i

    result.alternatives = scored

    # Generate recommendation
    if not scored and result.existing:
        if result.existing.score >= 80:
            result.recommendation = "Existing alt text is good quality. No changes needed."
        elif result.existing.score >= 60:
            result.recommendation = "Existing alt text is acceptable but could be improved."
        else:
            result.recommendation = "Existing alt text has quality issues. Consider rewriting."
    elif scored:
        best = scored[0]
        if result.existing and result.existing.score >= best.score:
            result.recommendation = (
                f"Existing alt text (score: {result.existing.score}) is as good or better "
                f"than generated alternatives. Keep the existing text."
            )
        elif result.existing and result.existing.score >= 70 and best.score - result.existing.score < 10:
            result.recommendation = (
                f"Existing alt text (score: {result.existing.score}) is close to the "
                f"best alternative (score: {best.score}). Review both before deciding."
            )
        else:
            existing_note = f" vs existing score {result.existing.score}" if result.existing else ""
            result.recommendation = (
                f"Best alternative from {best.model} (score: {best.score}{existing_note}). "
                f"Consider adopting this version."
            )

    return result


# ---------------------------------------------------------------------------
# Serialize for JSON (report pipeline)
# ---------------------------------------------------------------------------

def score_to_dict(s: AltTextScore) -> dict:
    """Convert an AltTextScore to a JSON-safe dict."""
    return {
        "text": s.text,
        "score": s.score,
        "model": s.model,
        "rank": s.rank,
        "flags": [
            {"code": f.code, "severity": f.severity, "message": f.message}
            for f in s.flags
        ],
    }


def ranked_to_dict(r: RankedAlternatives) -> dict:
    """Convert RankedAlternatives to a JSON-safe dict."""
    return {
        "existing": score_to_dict(r.existing) if r.existing else None,
        "alternatives": [score_to_dict(a) for a in r.alternatives],
        "recommendation": r.recommendation,
    }
