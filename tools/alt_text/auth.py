"""
auth.py — GitHub Token Retrieval
==================================
Retrieves a GitHub token for the Models API using gh CLI or env var.

This file is PERMANENT — do not delete.
"""

import os
import subprocess


class AuthError(RuntimeError):
    """Raised when GitHub authentication fails."""
    pass


def get_github_token() -> str:
    """Retrieve a GitHub token for the Models API.

    Priority:
      1. GITHUB_TOKEN environment variable
      2. gh auth token (GitHub CLI)

    Returns:
        The token string.

    Raises:
        AuthError: If no token can be obtained.
    """
    # 1. Environment variable
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token

    # 2. GitHub CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            if token:
                return token
        # gh is installed but no token
        raise AuthError(
            "GitHub CLI is installed but returned no token. "
            "Run: gh auth login\n"
            "Then ensure the copilot scope is present: "
            "gh auth refresh --scopes copilot"
        )
    except FileNotFoundError:
        raise AuthError(
            "Cannot authenticate with GitHub Models API.\n"
            "Options:\n"
            "  1. Set GITHUB_TOKEN environment variable\n"
            "  2. Install GitHub CLI (gh) and run: gh auth login\n"
            "     Then: gh auth refresh --scopes copilot"
        )
    except subprocess.TimeoutExpired:
        raise AuthError("GitHub CLI timed out retrieving token.")
