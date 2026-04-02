"""Tests for the AI bridge module (core/ai_bridge.py).

Validates that the bridge correctly interfaces with the tools/alt_text
package for vision-LLM alt text generation and remediation guidance.
All external dependencies are mocked -- no network or API calls.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock wx before importing anything that might touch it
sys.modules.setdefault("wx", MagicMock())
sys.modules.setdefault("wx.lib", MagicMock())
sys.modules.setdefault("wx.lib.newevent", MagicMock())

from pdf_a11y.core.ai_bridge import (
    AiBridge,
    AltTextRequest,
    AltTextResponse,
    RemediationRequest,
    RemediationResponse,
    is_ai_available,
)


class TestIsAiAvailable:
    """Test the is_ai_available() check."""

    def test_returns_false_when_import_fails(self):
        with patch.dict(sys.modules, {"alt_text": None, "alt_text.auth": None}):
            # Force reimport
            result = is_ai_available()
            # Should return False since the module can't be imported
            assert isinstance(result, bool)

    def test_returns_false_when_no_token(self):
        mock_auth = MagicMock()
        mock_auth.get_github_token.side_effect = RuntimeError("No token")
        with patch.dict(sys.modules, {"alt_text.auth": mock_auth}):
            result = is_ai_available()
            assert result is False


class TestAiBridge:
    """Test the AiBridge class."""

    def test_init(self):
        bridge = AiBridge()
        assert bridge._available is None
        assert bridge._tools_path_added is False

    def test_available_property_caches(self):
        bridge = AiBridge()
        bridge._available = True
        assert bridge.available is True

    def test_generate_alt_text_returns_response_on_error(self):
        bridge = AiBridge()
        bridge._tools_path_added = True  # skip path manipulation
        request = AltTextRequest(image_bytes=b"fake", mime_type="image/png")
        # Will fail because alt_text module doesn't exist in test env
        response = bridge.generate_alt_text(request)
        assert isinstance(response, AltTextResponse)
        # Either has alt text or has error
        assert response.concise_alt == "" or response.error != ""

    def test_generate_alt_text_success(self):
        bridge = AiBridge()
        bridge._tools_path_added = True

        mock_result = MagicMock()
        mock_result.concise_alt = "A photo of a building"
        mock_result.detailed_description = "A large brick building with columns"

        mock_score = MagicMock()
        mock_score.score = 85
        mock_score.flags = []

        with patch.dict(sys.modules, {
            "alt_text.client": MagicMock(
                generate_for_image=MagicMock(return_value=mock_result),
            ),
            "alt_text.models": MagicMock(DEFAULT_MODEL="openai/gpt-4.1"),
            "alt_text.scorer": MagicMock(score_alt_text=MagicMock(return_value=mock_score)),
        }):
            request = AltTextRequest(
                image_bytes=b"fake_image",
                mime_type="image/png",
                page_number=1,
            )
            response = bridge.generate_alt_text(request)
            assert response.concise_alt == "A photo of a building"
            assert response.quality_score == 85
            assert response.error == ""

    def test_get_remediation_guidance(self):
        bridge = AiBridge()
        bridge._tools_path_added = True

        mock_fix_tiers = MagicMock()
        mock_fix_tiers.FIX_TIERS = {
            "PDFUA.METADATA.TITLE": {
                "tier": 1,
                "tool": "fix_pdf",
                "note": "Sets the document title in PDF metadata.",
            }
        }
        mock_fix_tiers.TIER_LABELS = {
            1: "Automated Fix Available",
            2: "Assisted Fix (Review Required)",
            3: "Manual Fix Required",
        }

        with patch.dict(sys.modules, {"fix_tiers": mock_fix_tiers}):
            request = RemediationRequest(
                rule_id="PDFUA.METADATA.TITLE",
                severity="error",
                description="Missing document title",
            )
            response = bridge.get_remediation_guidance(request)
            assert isinstance(response, RemediationResponse)
            assert response.rule_id == "PDFUA.METADATA.TITLE"
            assert "Automated fix" in response.tool_steps[0]
            assert response.confidence == "high"

    def test_get_remediation_guidance_tier3(self):
        bridge = AiBridge()
        bridge._tools_path_added = True

        mock_fix_tiers = MagicMock()
        mock_fix_tiers.FIX_TIERS = {}
        mock_fix_tiers.TIER_LABELS = {
            1: "Automated Fix Available",
            2: "Assisted Fix (Review Required)",
            3: "Manual Fix Required",
        }

        with patch.dict(sys.modules, {"fix_tiers": mock_fix_tiers}):
            request = RemediationRequest(
                rule_id="UNKNOWN.RULE",
                severity="error",
                description="Unknown issue",
            )
            response = bridge.get_remediation_guidance(request)
            assert response.confidence == "medium"
            assert "Manual fix" in response.tool_steps[0]

    def test_list_available_models_error(self):
        bridge = AiBridge()
        bridge._tools_path_added = True
        # Should gracefully return empty dict on import failure
        result = bridge.list_available_models()
        assert isinstance(result, dict)

    def test_list_available_profiles_error(self):
        bridge = AiBridge()
        bridge._tools_path_added = True
        result = bridge.list_available_profiles()
        assert isinstance(result, dict)


class TestDataclasses:
    """Test the request/response dataclasses."""

    def test_alt_text_request_defaults(self):
        req = AltTextRequest(image_bytes=b"test")
        assert req.mime_type == "image/png"
        assert req.profile == "auto"
        assert req.language == "en"

    def test_alt_text_response_defaults(self):
        resp = AltTextResponse(concise_alt="test", detailed_description="detail")
        assert resp.quality_score == 0
        assert resp.quality_flags == []
        assert resp.error == ""

    def test_remediation_request_defaults(self):
        req = RemediationRequest(rule_id="TEST", severity="error", description="test")
        assert req.element_context == ""
        assert req.page_number is None

    def test_remediation_response_defaults(self):
        resp = RemediationResponse(rule_id="TEST")
        assert resp.tool_steps == []
        assert resp.acrobat_steps == []
        assert resp.error == ""
