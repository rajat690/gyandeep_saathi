"""Intent / domain router using gyandeep_saathi_intent_prompt.md."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from llm import chat_json

ROOT = Path(__file__).resolve().parent
INTENT_PROMPT_CANDIDATES = [
    ROOT / "gyandeep_saathi_intent_prompt.md",
    ROOT / "prompts" / "gyandeep_saathi_intent_prompt.md",
    ROOT / "intent-prompt.md",
]

GYAN_ID_RE = re.compile(r"\b(GYAN-\d{4}-\d{4})\b", re.IGNORECASE)
GS_ID_RE = re.compile(r"\b(GS-\d{4}-\d{2,4})\b", re.IGNORECASE)


def _load_intent_prompt() -> str:
    for path in INTENT_PROMPT_CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "Intent prompt not found. Expected gyandeep_saathi_intent_prompt.md next to app.py"
    )


def _forced_route_from_id(text: str) -> dict[str, Any] | None:
    """Demo shortcut: bare / clear GYAN or GS IDs skip the router LLM."""
    gyan = GYAN_ID_RE.search(text or "")
    if gyan:
        return {
            "domain": "Status",
            "intent": "STATUS",
            "application_id": gyan.group(1).upper(),
            "explicit_switch": "No",
            "decision_summary": "Detected GYAN application id in message",
            "signals_detected": [gyan.group(1).upper()],
            "confidence": "HIGH",
        }
    gs = GS_ID_RE.search(text or "")
    if gs:
        return {
            "domain": "Grievance",
            "intent": "GRIEVANCE",
            "application_id": gs.group(1).upper(),
            "explicit_switch": "No",
            "decision_summary": "Detected GS grievance ticket id in message",
            "signals_detected": [gs.group(1).upper()],
            "confidence": "HIGH",
        }
    return None


def route_intent(user_text: str) -> dict[str, Any]:
    forced = _forced_route_from_id(user_text)
    if forced:
        return forced

    system = _load_intent_prompt()
    result = chat_json(system, user_text, temperature=0.1)
    if not result:
        return {
            "domain": "Unknown",
            "intent": "GENERAL",
            "application_id": None,
            "explicit_switch": "No",
            "decision_summary": "Router LLM unavailable; defaulting unknown",
            "signals_detected": [],
            "confidence": "LOW",
        }

    # Normalize application_id casing if present
    app_id = result.get("application_id")
    if isinstance(app_id, str) and app_id.strip():
        result["application_id"] = app_id.strip().upper()
    else:
        result["application_id"] = None

    # If LLM missed an embedded id, fill from regex
    if not result.get("application_id"):
        forced = _forced_route_from_id(user_text)
        if forced:
            result["application_id"] = forced["application_id"]
            if result.get("domain") in (None, "Unknown"):
                result["domain"] = forced["domain"]
            if result.get("intent") in (None, "GENERAL") and forced["intent"] != "GENERAL":
                result["intent"] = forced["intent"]

    result.setdefault("domain", "Unknown")
    result.setdefault("intent", "GENERAL")
    result.setdefault("explicit_switch", "No")
    result.setdefault("decision_summary", "")
    result.setdefault("signals_detected", [])
    result.setdefault("confidence", "MEDIUM")
    return result
