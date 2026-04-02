"""AI-assisted remediation bridge for the desktop application.

Connects the wxPython desktop UI to the agentic toolkit's AI capabilities:
  - Vision-LLM alt text generation (GitHub Models API)
  - AI-assisted remediation suggestions
  - Quality scoring for generated alt text

This module is part of the core layer and must not import wx.
It uses the tools/alt_text package for LLM communication and
provides a clean async-friendly interface for the UI layer.

Public API
----------
AiBridge           -- Main integration class; lazy-loads alt_text package.
AltTextRequest     -- Dataclass for requesting alt text generation.
AltTextResponse    -- Dataclass for alt text results with quality scores.
RemediationRequest -- Dataclass for AI remediation guidance requests.
RemediationResponse-- Dataclass for AI remediation results.
is_ai_available()  -- True when the alt_text package and auth are configured.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Locate the tools directory relative to the package root
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"


# ---------------------------------------------------------------------------
# Request / Response dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AltTextRequest:
    """Request to generate alt text for a PDF image."""
    image_bytes: bytes
    mime_type: str = "image/png"
    page_number: int | None = None
    image_index: int = 0
    surrounding_text: str = ""
    existing_alt: str = ""
    model: str = ""
    profile: str = "auto"
    language: str = "en"


@dataclass
class AltTextResponse:
    """Response from AI alt text generation."""
    concise_alt: str
    detailed_description: str
    model: str = ""
    quality_score: int = 0
    quality_flags: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class RemediationRequest:
    """Request for AI-assisted remediation guidance."""
    rule_id: str
    severity: str
    description: str
    element_context: str = ""
    page_number: int | None = None


@dataclass
class RemediationResponse:
    """AI-generated remediation guidance."""
    rule_id: str
    tool_steps: list[str] = field(default_factory=list)
    acrobat_steps: list[str] = field(default_factory=list)
    explanation: str = ""
    confidence: str = "high"
    error: str = ""


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def is_ai_available() -> bool:
    """Check whether the AI alt text package is importable and auth is configured."""
    if str(_TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(_TOOLS_DIR))
    try:
        from alt_text.auth import get_github_token
        get_github_token()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main bridge class
# ---------------------------------------------------------------------------

class AiBridge:
    """Bridge between the desktop app and the AI-powered agentic toolkit.

    Lazily imports the tools/alt_text package so the desktop app works
    without the agents extra installed.  All methods are synchronous
    (suitable for calling from a worker thread; the UI layer should
    use wx.CallAfter / threading to avoid blocking).
    """

    def __init__(self) -> None:
        self._available: bool | None = None
        self._tools_path_added = False

    def _ensure_tools_path(self) -> None:
        """Add the tools directory to sys.path if not already present."""
        if not self._tools_path_added:
            if str(_TOOLS_DIR) not in sys.path:
                sys.path.insert(0, str(_TOOLS_DIR))
            self._tools_path_added = True

    @property
    def available(self) -> bool:
        """True when AI capabilities are configured and reachable."""
        if self._available is None:
            self._available = is_ai_available()
        return self._available

    def generate_alt_text(self, request: AltTextRequest) -> AltTextResponse:
        """Generate alt text for a single image using a vision LLM.

        Args:
            request: AltTextRequest with image bytes and context.

        Returns:
            AltTextResponse with concise alt, detailed description, and quality score.
        """
        self._ensure_tools_path()
        try:
            from alt_text.client import generate_for_image
            from alt_text.models import DEFAULT_MODEL
            from alt_text.scorer import score_alt_text

            model = request.model or DEFAULT_MODEL
            result = generate_for_image(
                image_bytes=request.image_bytes,
                mime_type=request.mime_type,
                model=model,
                profile=request.profile,
                source_format="pdf",
                page_number=request.page_number,
                surrounding_text=request.surrounding_text,
                existing_alt=request.existing_alt,
                language=request.language,
            )

            # Score the generated alt text
            score_result = score_alt_text(result.concise_alt)
            flags = [f.message for f in score_result.flags]

            return AltTextResponse(
                concise_alt=result.concise_alt,
                detailed_description=result.detailed_description,
                model=model,
                quality_score=score_result.score,
                quality_flags=flags,
            )
        except Exception as exc:
            logger.exception("AI alt text generation failed")
            return AltTextResponse(
                concise_alt="",
                detailed_description="",
                error=str(exc),
            )

    def generate_alt_text_for_document(
        self,
        pdf_path: str | Path,
    ) -> list[AltTextResponse]:
        """Generate alt text for all images in a PDF document.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of AltTextResponse objects, one per image found.
        """
        self._ensure_tools_path()
        try:
            from alt_text.client import generate_for_document
            from alt_text.scorer import score_alt_text

            report = generate_for_document(str(pdf_path))
            responses = []
            for img_options in report.images:
                if img_options.options:
                    best = img_options.options[0]
                    score_result = score_alt_text(best.concise_alt)
                    flags = [f.message for f in score_result.flags]
                    responses.append(AltTextResponse(
                        concise_alt=best.concise_alt,
                        detailed_description=best.detailed_description,
                        model=best.model,
                        quality_score=score_result.score,
                        quality_flags=flags,
                    ))
                elif img_options.errors:
                    responses.append(AltTextResponse(
                        concise_alt="",
                        detailed_description="",
                        error=img_options.errors[0].message,
                    ))
            return responses
        except Exception as exc:
            logger.exception("AI document alt text generation failed")
            return [AltTextResponse(concise_alt="", detailed_description="", error=str(exc))]

    def get_remediation_guidance(
        self,
        request: RemediationRequest,
    ) -> RemediationResponse:
        """Get AI-enhanced remediation guidance for a finding.

        This enriches the built-in remediation strings with contextual
        guidance from the fix_tiers module and the remediation knowledge base.

        Args:
            request: RemediationRequest with rule and context info.

        Returns:
            RemediationResponse with tool and Acrobat steps.
        """
        self._ensure_tools_path()
        try:
            from fix_tiers import FIX_TIERS, TIER_LABELS

            tier_info = FIX_TIERS.get(request.rule_id, {})
            tier = tier_info.get("tier", 3)
            tier_label = TIER_LABELS.get(tier, "Unknown")
            note = tier_info.get("note", "")

            tool_steps = []
            acrobat_steps = []

            if tier == 1:
                tool_steps.append(f"Automated fix available: {note}")
                tool_steps.append("Run the MCP fix tool or use fix_pdf.py directly")
            elif tier == 2:
                tool_steps.append(f"Assisted fix: {note}")
                tool_steps.append("Review the automated fix result before accepting")
            else:
                tool_steps.append("Manual fix required")
                tool_steps.append("Use Adobe Acrobat Pro for this repair")

            return RemediationResponse(
                rule_id=request.rule_id,
                tool_steps=tool_steps,
                acrobat_steps=acrobat_steps,
                explanation=f"Tier {tier} ({tier_label}): {note}",
                confidence="high" if tier <= 2 else "medium",
            )
        except Exception as exc:
            logger.exception("Remediation guidance lookup failed")
            return RemediationResponse(
                rule_id=request.rule_id,
                error=str(exc),
            )

    def list_available_models(self) -> dict[str, dict]:
        """Return the registry of available vision models."""
        self._ensure_tools_path()
        try:
            from alt_text.models import VISION_MODELS
            return dict(VISION_MODELS)
        except Exception:
            return {}

    def list_available_profiles(self) -> dict[str, dict]:
        """Return available alt text generation profiles."""
        self._ensure_tools_path()
        try:
            from alt_text.profiles import list_profiles
            return list_profiles()
        except Exception:
            return {}
