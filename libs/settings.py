"""Environment loading and default settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def load_settings(project_root: Path) -> dict[str, Any]:
    """Merge .env into os.environ (without overriding), then build settings dict."""
    for key, value in _parse_env_file(project_root / ".env").items():
        os.environ.setdefault(key, value)

    token = _env("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set (.env or environment)")

    ollama_url = _env("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    if "://" not in ollama_url:
        ollama_url = f"http://{ollama_url}"

    return {
        "project_root": str(project_root),
        "github_token": token,
        "ollama_url": ollama_url,
        "ollama_model": _env("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        "language": _env("LANGUAGE", "Python"),
        "max_stars": int(_env("MAX_STARS", "100")),
        "db_path": str(project_root / _env("DB_PATH", "data/followme.sqlite")),
        "repo_dir": str(project_root / _env("REPO_DIR", "data/repo")),
        "clone_depth": int(_env("CLONE_DEPTH", "1")),
        "request_timeout_seconds": int(_env("HTTP_TIMEOUT", "30")),
        "max_files": int(_env("MAX_FILES", "20")),
        "max_lines_per_file": int(_env("MAX_LINES_PER_FILE", "80")),
        "max_chars_per_file": int(_env("MAX_CHARS_PER_FILE", "4000")),
        "max_total_chars": int(_env("MAX_TOTAL_CHARS", "40000")),
        "max_file_bytes": int(_env("MAX_FILE_BYTES", "262144")),
        "extensions": [
            ext.strip()
            for ext in _env(
                "EXTENSIONS",
                ".py,.pyi,.js,.ts,.tsx,.jsx,.go,.rs,.java,.kt,.c,.h,.cpp,.hpp,"
                ".cs,.php,.rb,.swift,.scala,.lua,.sh,.sql,.yaml,.yml,.toml,.md",
            ).split(",")
            if ext.strip()
        ],
        "fetch_count": int(_env("FETCH_COUNT", "5")),
        "subscribe_threshold": float(_env("SUBSCRIBE_THRESHOLD", "14.0")),
        "star_threshold": float(_env("STAR_THRESHOLD", "16.0")),
        "window_hours": int(_env("WINDOW_HOURS", "24")),
        "dry_run": _env("DRY_RUN", "false").lower() in ("1", "true", "yes"),
    }
