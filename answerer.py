"""Answer generation using system prompt + FAQ + optional status JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm import chat_json

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent

SYSTEM_PROMPT_CANDIDATES = [
    ROOT / "gyandeep_saathi_system_prompt.md",
    ROOT / "prompts" / "gyandeep_saathi_system_prompt.md",
    ROOT / "system-prompt.md",
    PARENT / "system-prompt.md",
]
FAQ_CANDIDATES = [
    ROOT / "gyandeep_saathi_FAQ.txt",
    ROOT / "knowledge" / "gyandeep_saathi_FAQ.txt",
    ROOT / "FAQ.txt",
    PARENT / "FAQ.txt",
]
MOCK_STATUS_CANDIDATES = [
    ROOT / "mock_status.json",
    ROOT / "data" / "mock_status.json",
    ROOT / "gyandeep_saathi_mock_status.json",
    PARENT / "mock_status.json",
]

FALLBACK_HI = (
    "नमस्कार। मैं ज्ञानदीप साथी हूँ — बिहार आरटीई / ज्ञानदीप पोर्टल हेल्पडेस्क।\n"
    "आप आवेदन स्थिति (जैसे GYAN-2026-1004), सामान्य जानकारी, या शिकायत के बारे में पूछ सकते हैं।\n"
    "पोर्टल: https://gyandeep-rte.bihar.gov.in/"
)

ASK_ID_HI = (
    "कृपया अपना आवेदन संख्या भेजें "
    "(उदाहरण: GYAN-2026-1001)।"
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
        print("mock_status.json not found in candidates", flush=True)
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"Loaded mock status from {path}", flush=True)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"Failed to load mock_status.json: {exc}", flush=True)
        return {}


def lookup_status(application_id: str | None) -> dict[str, Any] | None:
    if not application_id:
        return None
    store = load_mock_status()
    key = application_id.strip()
    if key in store:
        return store[key]
    return store.get(key.upper())


def _looks_like_menu(text: str) -> bool:
    t = (text or "").lower()
    markers = [
        "आप क्या जानना चाहते हैं",
        "मैं ज्ञानदीप साथी हूँ",
        "general जानकारी",
        "what do you want to know",
        "i am gyandeep",
        "helpline desk",
        "हेल्पडेस्क",
        "हेल्पलाइन",
    ]
    return any(m.lower() in t for m in markers)


def format_status_card(status: dict[str, Any]) -> str:
    """Deterministic status card — never a greeting/menu."""
    name = status.get("child_name") or status.get("applicant_name") or "NA"
    app_id = status.get("application_id") or "NA"
    cur = status.get("current_status") or "NA"
    changed = status.get("status_change_date") or "NA"
    school = status.get("allotted_school") or "NA"
    remark = status.get("remark") or "NA"

    summaries = {
        "Registered": (
            "आवेदन/पंजीकरण दर्ज है। पोर्टल पर बाकी चरण पूरे करें और सत्यापन की प्रतीक्षा करें।"
        ),
        "Under verification": (
            "दस्तावेज़/विवरण जाँचे जा रहे हैं। पोर्टल पर निर्देश आने पर सुधार करें।"
        ),
        "Verified — awaiting allotment": (
            "सत्यापन पूरा। स्कूल आवंटन/लॉटरी की प्रतीक्षा करें।"
        ),
        "Verified - awaiting allotment": (
            "सत्यापन पूरा। स्कूल आवंटन/लॉटरी की प्रतीक्षा करें।"
        ),
        "School allotted": (
            "स्कूल आवंटित है। निर्धारित समय में दस्तावेज़ लेकर नामांकन पूरा करें।"
        ),
        "Enrolled": "नामांकन/प्रवेश रिकॉर्ड में पूर्ण दिख रहा है।",
        "Objection / documents pending": (
            "दस्तावेज़/आपत्ति लंबित है। सुधार कर फिर सत्यापन कराएँ।"
        ),
        "Not allotted in lottery": (
            "इस चरण में आवंटन नहीं हुआ। पोर्टल पर आगे के निर्देश देखें।"
        ),
        "Rejected": (
            "आवेदन अस्वीकृत है। कारण पोर्टल पर देखें। ज़रूरत हो तो शिकायत दर्ज करा सकते हैं।"
        ),
    }
    summary = summaries.get(
        str(cur),
        f"आवेदन की वर्तमान स्थिति: {cur}। विवरण पोर्टल पर जाँचें।",
    )

    return (
        f"आवेदक का नाम: {name}\n"
        f"आवेदन संख्या: {app_id}\n"
        f"वर्तमान स्थिति: {cur}\n"
        f"स्थिति परिवर्तन तिथि: {changed}\n"
        f"आवंटित विद्यालय: {school}\n"
        f"टिप्पणी: {remark}\n\n"
        f"सारांश: {summary}\n"
        f"पोर्टल: https://gyandeep-rte.bihar.gov.in/"
    )


def _build_injection(route: dict[str, Any], status_data: dict[str, Any] | None) -> str:
    faq = _read_text(_first_existing(FAQ_CANDIDATES))
    domain = route.get("domain") or "Unknown"
    status_json = (
        json.dumps(status_data, ensure_ascii=False, indent=2)
        if status_data is not None
        else "null"
    )
    return (
        f"ActiveDomain: {domain}\n\n"
        f"BEGIN_FAQ\n{faq}\nEND_FAQ\n\n"
        f"BEGIN_APPLICATION_STATUS_DATA_JSON\n{status_json}\nEND_APPLICATION_STATUS_DATA_JSON\n\n"
        "Status Response Rules:\n"
        "- Use only the injected Application Status Data for status answers.\n"
        "- If status data is null and user asked status WITH an application id, "
        "say status is not available for that ID.\n"
        "- If status intent but no application id yet, ask only for GYAN-… id; "
        "do not say unavailable and do not open main menu.\n"
        "- For FAQ, answer only from the FAQ block; do not invent income limits or dates "
        "beyond the FAQ.\n"
        "- For Grievance without a system-issued ticket, explain how to describe the issue; "
        "do not invent ticket IDs.\n"
        "- If Application Status Data JSON is not null, never send a greeting or main menu.\n"
        "- If user only asked a language switch, do not open main menu.\n"
        "- Follow the system prompt Output Format (JSON with user_response).\n"
    )


def generate_reply(user_text: str, route: dict[str, Any], language: str | None = None) -> str:
    system_path = _first_existing(SYSTEM_PROMPT_CANDIDATES)
    system_prompt = _read_text(system_path)
    if not system_prompt:
        return FALLBACK_HI

    app_id = route.get("application_id")
    if isinstance(app_id, str):
        app_id = app_id.strip().upper() or None
    else:
        app_id = None

    status_data = lookup_status(app_id) if app_id else None

    # Known status row: deterministic card (fixes GYAN-2026-1001 -> menu bug)
    if status_data:
        print(f"Status hit for {app_id}: {status_data}", flush=True)
        return format_status_card(status_data)

    is_status = route.get("intent") == "STATUS" or route.get("domain") == "Status"

    # STATUS but no ID yet: ask for ID only
    if is_status and not app_id:
        return ASK_ID_HI

    # STATUS with ID but nothing in store
    if is_status and app_id and not status_data:
        return (
            f"आवेदन संख्या {app_id} की स्थिति उपलब्ध नहीं है। "
            "कृपया संख्या जाँचें या पोर्टल पर देखें: "
            "https://gyandeep-rte.bihar.gov.in/\n"
            "डेमो आईडी उदाहरण: GYAN-2026-1001"
        )

    injection = _build_injection(route, status_data)
    lang = (language or "").strip().lower()
    lang_rule = ""
    if lang == "en":
        lang_rule = (
            "\nSessionLanguage: en\n"
            "Reply in English for this turn (standing session language).\n"
        )
    elif lang in ("bho", "mai", "hi"):
        label = {"hi": "Hindi (Devanagari)", "bho": "Bhojpuri", "mai": "Maithili"}[lang]
        lang_rule = (
            f"\nSessionLanguage: {lang}\n"
            f"Reply in {label} for this turn (standing session language). "
            "Do not switch to another language unless the user asks.\n"
        )
    full_system = system_prompt.strip() + "\n\n" + injection + lang_rule

    user_block = (
        f"User message:\n{user_text}\n\n"
        f"Router JSON:\n{json.dumps(route, ensure_ascii=False)}\n"
    )

    result = chat_json(full_system, user_block, temperature=0.3)
    if not result:
        return FALLBACK_HI

    reply = result.get("user_response")
    if isinstance(reply, str) and reply.strip():
        reply = reply.strip()
        # Safety net: never let a status-ish turn collapse to the welcome menu
        if _looks_like_menu(reply) and (is_status or app_id):
            if not app_id:
                return ASK_ID_HI
            return (
                f"आवेदन संख्या {app_id} की स्थिति उपलब्ध नहीं है। "
                "https://gyandeep-rte.bihar.gov.in/"
            )
        return reply
    return FALLBACK_HI
