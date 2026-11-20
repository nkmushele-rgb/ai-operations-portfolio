"""Local model access through Ollama, with a hard fallback to rules.

Design choice: routing and scoring in these projects are decided by
deterministic, auditable rules. The model is only asked to write prose.
That keeps behaviour reproducible and testable, and means every workflow
still completes when no model is running.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("AIOPS_MODEL", "qwen3:8b")
MODE = os.environ.get("AIOPS_LLM", "auto").lower()  # auto | on | off
TIMEOUT = float(os.environ.get("AIOPS_LLM_TIMEOUT", "90"))

_probe: bool | None = None
_last_error: str | None = None

_THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


def enabled() -> bool:
    return MODE != "off"


def reset_probe() -> None:
    """Forget a cached availability probe (used by tests)."""
    global _probe
    _probe = None


def available() -> bool:
    global _probe, _last_error
    if not enabled():
        return False
    if _probe is not None:
        return _probe
    try:
        with urllib.request.urlopen(f"{HOST}/api/tags", timeout=1.5) as response:
            data = json.loads(response.read().decode("utf-8"))
        names = {m.get("name", "") for m in data.get("models", [])}
        family = MODEL.split(":")[0]
        _probe = MODEL in names or any(n.split(":")[0] == family for n in names)
        if not _probe:
            _last_error = f"model {MODEL} is not installed"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _probe = False
        _last_error = f"Ollama unreachable: {exc}"
    return _probe


def generate(prompt: str, system: str = "", max_tokens: int = 320,
             timeout: float | None = None) -> str | None:
    """Return model text, or None if the model is unavailable or fails."""
    global _last_error
    if not enabled() or not available():
        return None
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": max_tokens},
    }
    if system:
        payload["system"] = system
    request = urllib.request.Request(
        f"{HOST}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout or TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _last_error = f"generation failed: {exc}"
        return None
    text = _THINK_RE.sub("", data.get("response") or "").strip()
    return text or None


def generate_json(prompt: str, system: str = "", max_tokens: int = 320,
                  timeout: float | None = None) -> dict | None:
    """Ask for JSON and parse it defensively."""
    text = generate(prompt, system=system, max_tokens=max_tokens, timeout=timeout)
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except ValueError:
            return None


def status() -> dict:
    return {
        "mode": MODE,
        "model": MODEL,
        "host": HOST,
        "available": available(),
        "last_error": _last_error,
    }
