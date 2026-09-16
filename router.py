"""Intent / domain router using gyandeep_saathi_intent_prompt.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from llm import chat_json

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent

INTENT_PROMPT_CANDIDATES = [
    ROOT / "gyandeep_saathi_intent_prompt.md",
    ROOT / "prompts" / "gyandeep_saathi_intent_prompt.md",
    ROOT / "intent-prompt.md",
    PARENT / "intent-prompt.md",
]

# Allow punctuation around ids: GYAN-2026-1001. / (GYAN-2026-1001)
GYAN_ID_RE = re.compile(r"(?<![A-Za-z0-9])(GYAN-\d{4}-\d{4})(?![A-Za-z0-9])", re.IGNORECASE)
GS_ID_RE = re.compile(r"(?<![A-Za-z0-9])(GS-\d{4}-\d{2,4})(?![A-Za-z0-9])", re.IGNORECASE)

# Roman Hindi / Hinglish / English / Devanagari STATUS cues (no ID required)
STATUS_PHRASE_RE = re.compile(
    r"""
    \b(
        avedan\s*stith[iy]?
        | aavedan\s*stith[iy]?
        | application\s*status
        | form\s*status
        | status\s*enquiry
        | status\s*inquiry
        | check\s*status
        | mera\s*form\s*kahan
        | form\s*kahan\s*hai
        | allotment\s*(hua|status)?
        | enrollment\s*status
        | admission\s*status
        | school\s*allotment
    )\b
    | आवेदन\s*स्थिति
    | आवेदन\s*की\s*स्थिति
    | फॉर्म\s*स्थिति
    | आवंटन
    | नामांकन\s*स्थिति
    | स्थिति\s*बताओ
    | स्थिति\s*क्या
    """,
    re.IGNORECASE | re.VERBOSE,
)

LANGUAGE_SWITCH_RE = re.compile(
    r"""
    \b(
        (switch\s+to\s+)?english
        | (reply\s+in\s+)?english
        | eng\b
        | (switch\s+to\s+)?(hindi|hindi\s+mein)
        | (switch\s+to\s+)?(bhojpuri|bhojpuri\s+mein)
        | (switch\s+to\s+)?(maithili|maithili\s+mein)
        | give\s+the\s+reply\s+in\s+(english|hindi|bhojpuri|maithili)
        | (english|hindi|bhojpuri|maithili)\s+mein\s+(bataiye|batao|likho)
    )\b
    | हिन्दी|हिंदी|मैथिली|भोजपुरी
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _load_intent_prompt() -> str:
    for path in INTENT_PROMPT_CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "Intent prompt not found. Expected intent-prompt.md next to app or in parent folder."
    )


def _status_route(app_id: str | None, summary: str, signals: list[str]) -> dict[str, Any]:
    return {
        "domain": "Status",
        "intent": "STATUS",
        "application_id": app_id.upper() if app_id else None,
        "explicit_switch": "No",
        "decision_summary": summary[:80],
        "signals_detected": signals[:5],
        "confidence": "HIGH",
    }


def _forced_route_from_id(text: str) -> dict[str, Any] | None:
    """Demo shortcut: bare / clear GYAN or GS IDs skip the router LLM."""
    gyan = GYAN_ID_RE.search(text or "")
    if gyan:
        return _status_route(
            gyan.group(1),
            "Detected GYAN application id in message",
            [gyan.group(1).upper()],
        )
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


def _forced_route_from_status_phrase(text: str) -> dict[str, Any] | None:
    """Force STATUS for common Roman Hindi / English status asks without an ID."""
    if not text or not text.strip():
        return None
    # Language-only messages are not status
    stripped = text.strip()
    if LANGUAGE_SWITCH_RE.fullmatch(stripped) or (
        LANGUAGE_SWITCH_RE.search(stripped)
        and len(stripped.split()) <= 6
        and not STATUS_PHRASE_RE.search(stripped)
        and not GYAN_ID_RE.search(stripped)
    ):
        return None

    m = STATUS_PHRASE_RE.search(text)
    if not m:
        return None
    gyan = GYAN_ID_RE.search(text)
    signal = m.group(0).strip()
    return _status_route(
        gyan.group(1) if gyan else None,
        f"Status phrase matched: {signal}",
        [signal, gyan.group(1).upper()] if gyan else [signal],
    )


def route_intent(user_text: str) -> dict[str, Any]:
    text = user_text or ""

    forced = _forced_route_from_id(text)
    if forced:
        return forced

    forced_phrase = _forced_route_from_status_phrase(text)
    if forced_phrase:
        return forced_phrase

    try:
        system = _load_intent_prompt()
    except FileNotFoundError as exc:
        print(f"Router prompt missing: {exc}", flush=True)
        return {
            "domain": "Unknown",
            "intent": "GENERAL",
            "application_id": None,
            "explicit_switch": "No",
            "decision_summary": "Intent prompt missing; defaulting unknown",
            "signals_detected": [],
            "confidence": "LOW",
        }

    result = chat_json(system, text, temperature=0.1)
    if not result:
        # LLM down: if it still looks like status words, prefer STATUS ask-id path
        if STATUS_PHRASE_RE.search(text):
            return _status_route(None, "LLM down; status phrase fallback", ["status_fallback"])
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
        forced = _forced_route_from_id(text)
        if forced:
            result["application_id"] = forced["application_id"]
            if result.get("domain") in (None, "Unknown"):
                result["domain"] = forced["domain"]
            if result.get("intent") in (None, "GENERAL") and forced["intent"] != "GENERAL":
                result["intent"] = forced["intent"]

    # If LLM marked Unknown/GENERAL but status phrase is clear, upgrade to STATUS
    if STATUS_PHRASE_RE.search(text):
        if result.get("domain") in (None, "Unknown", "FAQ"):
            result["domain"] = "Status"
        if result.get("intent") in (None, "GENERAL"):
            result["intent"] = "STATUS"
        signals = result.get("signals_detected") or []
        if isinstance(signals, list) and "status_phrase" not in signals:
            signals = list(signals) + ["status_phrase"]
            result["signals_detected"] = signals[:5]

    result.setdefault("domain", "Unknown")
    result.setdefault("intent", "GENERAL")
    result.setdefault("explicit_switch", "No")
    result.setdefault("decision_summary", "")
    result.setdefault("signals_detected", [])
    result.setdefault("confidence", "MEDIUM")
    return result
