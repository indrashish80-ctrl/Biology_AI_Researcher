"""
core_utils.py
-------------
Small shared utilities used across the biology research engine:

- robust JSON extraction from AI responses (handles markdown fences,
  surrounding prose, and balanced-brace scanning for embedded JSON)
- project-relative path resolution
- a uniform timing/logging helper

Kept dependency-free (stdlib only) so every module can import it
without creating import cycles.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional


# ==========================================================
# JSON EXTRACTION
# ==========================================================

def strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_balanced_json(text: str) -> Optional[str]:
    """
    Find the first complete JSON object or array in `text`, respecting
    quoted strings and escaped characters. Returns None if nothing
    balanced is found (e.g. the response was truncated mid-object).
    """
    if not text:
        return None

    for start, opener in ((i, ch) for i, ch in enumerate(text) if ch in "{["):
        closer = "}" if opener == "{" else "]"
        depth = 0
        in_string = False
        escaped = False

        for i in range(start, len(text)):
            ch = text[i]

            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    return None


def parse_json_response(text: str) -> Any:
    """
    Parse JSON out of a raw AI response. Handles plain JSON, JSON in
    markdown fences, and JSON embedded in surrounding prose. Does not
    attempt to "repair" truncated JSON -- callers should retry instead.
    """
    if not text or not text.strip():
        raise ValueError("Empty AI response.")

    cleaned = strip_markdown_fences(text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    candidate = extract_balanced_json(cleaned)
    if candidate is None:
        raise ValueError("No complete JSON object/array found in response.")

    return json.loads(candidate)


# ==========================================================
# PATHS
# ==========================================================

def resolve_project_path(value: Optional[str], default_path: Path, base_dir: Path) -> Path:
    if not value:
        return default_path

    p = Path(value)
    if p.is_absolute():
        return p

    cwd_candidate = Path.cwd() / p
    if cwd_candidate.exists():
        return cwd_candidate

    return base_dir / p


# ==========================================================
# TIMING
# ==========================================================

class Timer:
    """Context manager returning elapsed wall-clock seconds via .elapsed"""

    def __enter__(self):
        self._start = time.time()
        self.elapsed = None
        return self

    def __exit__(self, *exc):
        self.elapsed = time.time() - self._start
        return False


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
