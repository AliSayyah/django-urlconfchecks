"""Configuration loading for django-urlconfchecks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:  # pragma: no cover
        tomllib = None  # type: ignore


CONFIG_ENV_VAR = "URLCONFCHECKS_PYPROJECT"


@dataclass(frozen=True)
class AppConfig:
    """Configuration settings for django-urlconfchecks.

    Attributes:
        quiet: Whether to suppress non-error output.
        format: Output format for results.
        silenced_views: Dictionary mapping view names to silence reasons.
    """

    quiet: Optional[bool] = None
    format: Optional[str] = None
    silenced_views: Optional[Dict[str, str]] = None


def load_config(pyproject_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from pyproject.toml [tool.urlconfchecks]."""
    if tomllib is None:
        return AppConfig()

    path = pyproject_path or _find_pyproject()
    if path is None or not path.is_file():
        return AppConfig()

    try:
        data = tomllib.loads(path.read_text())
    except Exception:  # pragma: no cover - fallback to empty config
        return AppConfig()

    section = _extract_section(data)
    if section is None:
        return AppConfig()

    quiet = section.get("quiet") if isinstance(section.get("quiet"), bool) else None
    fmt = section.get("format") if isinstance(section.get("format"), str) else None

    silenced_views_raw = section.get("silenced_views")
    silenced_views = silenced_views_raw if isinstance(silenced_views_raw, dict) else None

    return AppConfig(quiet=quiet, format=fmt, silenced_views=silenced_views)


def _find_pyproject() -> Optional[Path]:
    """Locate pyproject.toml, honoring explicit env override first."""
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate

    current = Path.cwd()
    for folder in [current, *current.parents]:
        candidate = folder / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None


def _extract_section(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return None
    section = tool.get("urlconfchecks")
    if not isinstance(section, dict):
        return None
    return section
