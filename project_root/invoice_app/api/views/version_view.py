"""
Version endpoint — public, no authentication required.

Returns application version, git SHA, and build date.
"""

import subprocess
from importlib.metadata import PackageNotFoundError, version

from django.http import JsonResponse
from django.views import View


def _get_git_sha():
    """Read git SHA from environment (set at build time) or fall back to git."""
    import os

    # Prefer build-time ENV (set via Dockerfile ARG → ENV)
    sha = os.environ.get("GIT_SHA", "")
    if sha and sha != "unknown":
        return sha

    # Fallback: live git (works outside Docker)
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _get_app_version():
    """Read version from pyproject.toml via importlib.metadata."""
    try:
        return version("erechnung")
    except PackageNotFoundError:
        # Fallback: read directly from pyproject.toml
        import os
        import re
        from pathlib import Path

        # In Docker: /app/pyproject.toml, locally: project root
        candidates = [
            Path(os.environ.get("PYTHONPATH", "/app")) / "pyproject.toml",
            Path(__file__).resolve().parents[5] / "pyproject.toml",
            Path(__file__).resolve().parents[4] / "pyproject.toml",
        ]
        for pyproject in candidates:
            if pyproject.exists():
                match = re.search(r'^version\s*=\s*"(.+?)"', pyproject.read_text(), re.MULTILINE)
                if match:
                    return match.group(1)
        return "unknown"


class VersionView(View):
    """Public endpoint returning application version info."""

    def get(self, request):
        import os

        data = {
            "version": _get_app_version(),
            "git_sha": _get_git_sha(),
            "build_date": os.environ.get("BUILD_DATE", "unknown"),
        }
        return JsonResponse(data)
