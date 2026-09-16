"""In-memory per-WhatsApp-user session for guided UX."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# wa_id -> session dict
_SESSIONS: dict[str, dict[str, Any]] = {}

# Dummy grievance tickets: GS-2026-0100, then increment
_TICKET_COUNTER = 100

_DEFAULT: dict[str, Any] = {
    "language": None,  # hi | en | bho | mai
    "flow": None,  # language | main | eligibility | apply | status | schools | docs | grievance | others | None
    "eligibility_step": None,  # gate | age | age_typed | class | income | done
    "eligibility_answers": {},
    "apply_step": None,  # 0..5 or None
    "schools_step": None,
    "docs_step": None,
    "grievance_waiting": False,  # waiting for free-text after category 8
    "grievance_category": None,
    "last_topic": None,
    "awaiting_status_id": False,
}


def _blank() -> dict[str, Any]:
    return deepcopy(_DEFAULT)


def get_session(wa_id: str | None) -> dict[str, Any]:
    key = (wa_id or "").strip() or "_anon"
    if key not in _SESSIONS:
        _SESSIONS[key] = _blank()
    return _SESSIONS[key]


def set_fields(wa_id: str | None, **fields: Any) -> dict[str, Any]:
    sess = get_session(wa_id)
    for k, v in fields.items():
        if k == "eligibility_answers" and isinstance(v, dict):
            sess.setdefault("eligibility_answers", {}).update(v)
        else:
            sess[k] = v
    return sess


def clear_flow(wa_id: str | None, keep_language: bool = True) -> dict[str, Any]:
    sess = get_session(wa_id)
    lang = sess.get("language")
    last = sess.get("last_topic")
    sess.clear()
    sess.update(_blank())
    if keep_language:
        sess["language"] = lang
    sess["last_topic"] = last
    return sess


def reset_eligibility(wa_id: str | None) -> dict[str, Any]:
    return set_fields(
        wa_id,
        flow="eligibility",
        eligibility_step="gate",
        eligibility_answers={},
        last_topic="eligibility",
        grievance_waiting=False,
        awaiting_status_id=False,
        apply_step=None,
        schools_step=None,
        docs_step=None,
    )


def next_ticket_id() -> str:
    global _TICKET_COUNTER
    tid = f"GS-2026-{_TICKET_COUNTER:04d}"
    _TICKET_COUNTER += 1
    return tid


def reset_all_sessions_for_tests() -> None:
    """Test helper: wipe memory and ticket counter."""
    global _TICKET_COUNTER
    _SESSIONS.clear()
    _TICKET_COUNTER = 100
