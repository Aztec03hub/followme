"""Minimal Ollama JSON-generation client (stdlib only)."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a senior code reviewer. Given a repository digest, return a STRICT JSON object "
    "with exactly three fields:\n"
    '  "idea":  float in [1.0, 10.0] grading the novelty and usefulness of the project idea,\n'
    '  "skill": float in [1.0, 10.0] grading the engineering skill shown in the code,\n'
    '  "description": one short English sentence summarizing what the repository does.\n'
    "Grade anchors: 1=trivial/junior, 5=ordinary/middle, 9=strong/senior. "
    "Return ONLY the JSON object, no prose."
)


def ensure_available(settings: dict[str, Any]) -> None:
    url = f"{settings['ollama_url']}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=settings["request_timeout_seconds"]) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot reach Ollama at {settings['ollama_url']}: {exc}") from exc
    models = {str(m.get("name", "")).strip() for m in payload.get("models", []) if isinstance(m, dict)}
    if settings["ollama_model"] not in models:
        raise RuntimeError(
            f"Model '{settings['ollama_model']}' not installed in Ollama. Installed: {sorted(models)}"
        )


def evaluate(settings: dict[str, Any], full_name: str, digest: str) -> dict[str, Any]:
    """Ask Ollama for {idea, skill, description}; clamp scores into [1, 10]."""
    user_prompt = f"Repository: {full_name}\nLanguage: {settings['language']}\n\nDigest:\n{digest}\n\nReturn JSON only."
    payload = {
        "model": settings["ollama_model"],
        "system": SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        f"{settings['ollama_url']}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    timeout = max(180, settings["request_timeout_seconds"])
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Ollama HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach Ollama: {exc}") from exc

    parsed = json.loads(raw)
    text = str(parsed.get("response", "")).strip()
    return _parse_json_blob(text)


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_blob(text: str) -> dict[str, Any]:
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise RuntimeError(f"Ollama did not return JSON: {text[:200]!r}")
    data = json.loads(match.group(0))
    idea = _clamp(_safe_float(data.get("idea"), 0.0), 1.0, 10.0)
    skill = _clamp(_safe_float(data.get("skill"), 0.0), 1.0, 10.0)
    description = str(data.get("description", "")).strip()
    return {"idea": idea, "skill": skill, "description": description}


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
