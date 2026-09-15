"""Answer generation using system prompt + FAQ + optional status JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm import chat_json

ROOT = Path(__file__).resolve().parent

SYSTEM_PROMPT_CANDIDATES = [
    ROOT / "gyandeep_saathi_system_prompt.md",
    ROOT / "prompts" / "gyandeep_saathi_system_prompt.md",
    ROOT / "system-prompt.md",
]
FAQ_CANDIDATES = [
    ROOT / "gyandeep_saathi_FAQ.txt",
    ROOT / "knowledge" / "gyandeep_saathi_FAQ.txt",
    ROOT / "FAQ.txt",
]
MOCK_STATUS_CANDIDATES = [
    ROOT / "mock_status.json",
    ROOT / "data" / "mock_status.json",
    ROOT / "gyandeep_saathi_mock_status.json",
]

FALLBACK_HI = (
    "नमस्कार। मैं ज्ञानदीप साथी हूँ — बिहार आरटीई / ज्ञानदीप पोर्टल हेल्पडेस्क।\n"
    "आप आवेदन स्थिति (जैसे GYAN-2026-1004), सामान्य जानकारी, या शिकायत के बारे में पूछ सकते हैं।\n"
    "पोर्टल: https://gyandeep-rte.bihar.gov.in/"
)


def _first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.is_file():
            return p
    return None


def _read_text(path: Path | None) -> str:
    if not path:
        return ""
    return path.read_text(encoding="utf-8")


def load_mock_status() -> dict[str, Any]:
    path = _first_existing(MOCK_STATUS_CANDIDATES)
    if not path:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"Failed to load mock_status.json: {exc}", flush=True)
        return {}


def lookup_status(application_id: str | None) -> dict[str, Any] | None:
    if not application_id:
        return None
    store = load_mock_status()
    # try exact then upper
    if application_id in store:
        return store[application_id]
    return store.get(application_id.upper())


def _build_injection(route: dict[str, Any], status_data: dict[str, Any] | None) -> str:
    faq = _read_text(_first_existing(FAQ_CANDIDATES))
    domain = route.get("domain") or "Unknown"
    status_json = json.dumps(status_data, ensure_ascii=False, indent=2) if status_data is not None else "null"
    return (
        f"ActiveDomain: {domain}\n\n"
        f"BEGIN_FAQ\n{faq}\nEND_FAQ\n\n"
        f"BEGIN_APPLICATION_STATUS_DATA_JSON\n{status_json}\nEND_APPLICATION_STATUS_DATA_JSON\n\n"
        "Status Response Rules:\n"
        "- Use only the injected Application Status Data for status answers.\n"
        "- If status data is null and user asked status, say status is not available for that ID.\n"
        "- For FAQ, answer only from the FAQ block; do not invent income limits or dates.\n"
        "- For Grievance without a system-issued ticket, explain how to describe the issue; do not invent ticket IDs.\n"
        "- Follow the system prompt Output Format (JSON with user_response).\n"
    )


def generate_reply(user_text: str, route: dict[str, Any]) -> str:
    system_path = _first_existing(SYSTEM_PROMPT_CANDIDATES)
    system_prompt = _read_text(system_path)
    if not system_prompt:
        return FALLBACK_HI

    app_id = route.get("application_id")
    status_data = lookup_status(app_id) if app_id else None
    # Explicit null when STATUS intent but id missing / unknown
    if route.get("intent") == "STATUS" and app_id and status_data is None:
        status_data = None  # keep null in injection

    injection = _build_injection(route, status_data)
    full_system = system_prompt.strip() + "\n\n" + injection

    user_block = (
        f"User message:\n{user_text}\n\n"
        f"Router JSON:\n{json.dumps(route, ensure_ascii=False)}\n"
    )

    result = chat_json(full_system, user_block, temperature=0.3)
    if not result:
        return FALLBACK_HI

    reply = result.get("user_response")
    if isinstance(reply, str) and reply.strip():
        return reply.strip()
    return FALLBACK_HI
