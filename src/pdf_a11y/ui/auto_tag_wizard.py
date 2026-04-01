"""Auto-tagger review wizard dialog.

This multi-step wizard guides the user through the auto-tagging process:
  1. Select auto-tagging options (heuristic only, ML-assisted, etc.)
  2. Run analysis and display the proposed tag assignments with confidence scores
  3. Let the user accept, reject, or manually override each proposed tag
  4. Apply accepted changes as a batch command on the CommandStack

Planned public API:
    AutoTagWizard    -- wx.adv.Wizard subclass with pages for configuration,
                        review, and application of auto-tag results.
"""
from __future__ import annotations
