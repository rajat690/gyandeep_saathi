"""Orchestrate route → answer for one inbound user message."""

from __future__ import annotations

from answerer import generate_reply
from router import route_intent


def handle_message(user_text: str) -> str:
    text = (user_text or "").strip()
    if not text:
        return (
            "नमस्कार। कृपया अपना प्रश्न लिखें — स्थिति, जानकारी, या शिकायत।"
        )

    # Simple greeting shortcut (no LLM) for cold start reliability
    lowered = text.lower()
    if lowered in {"hi", "hello", "hey", "namaste", "namaskar", "हैलो", "नमस्ते", "नमस्कार"}:
        return (
            "नमस्कार। मैं ज्ञानदीप साथी हूँ।\n"
            "मैं मदद कर सकता हूँ:\n"
            "1) आवेदन स्थिति (जैसे GYAN-2026-1004)\n"
            "2) आरटीई / ज्ञानदीप सामान्य जानकारी\n"
            "3) शिकायत दर्ज करने का तरीका\n\n"
            "आप क्या जानना चाहते हैं?"
        )

    route = route_intent(text)
    print(f"Router result: {route}", flush=True)
    return generate_reply(text, route)
