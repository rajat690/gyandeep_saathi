"""WhatsApp Cloud API send helpers (SETU-style)."""

from __future__ import annotations

import os
from typing import Any

import requests

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v23.0")


def _meta_url() -> str:
    return (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    )


def _meta_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def send_text(to_wa_id: str, body: str) -> bool:
    """Send a plain text WhatsApp message. Returns True on HTTP success."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("WhatsApp env missing: WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID", flush=True)
        return False
    if not body or not to_wa_id:
        return False

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }
    try:
        resp = requests.post(
            _meta_url(),
            json=payload,
            headers=_meta_headers(),
            timeout=20,
        )
        if not resp.ok:
            print(f"WhatsApp send failed {resp.status_code}: {resp.text[:500]}", flush=True)
            return False
        return True
    except Exception as exc:
        print(f"WhatsApp send error: {exc}", flush=True)
        return False


def extract_first_text_message(payload: dict[str, Any] | None) -> dict[str, str] | None:
    """Pull first inbound text (or button/list reply title) from a Meta webhook body."""
    if not payload or payload.get("object") != "whatsapp_business_account":
        return None
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            for message in value.get("messages", []) or []:
                wa_id = message.get("from") or ""
                mid = message.get("id") or ""
                mtype = message.get("type")
                text = ""
                if mtype == "text":
                    text = (message.get("text") or {}).get("body") or ""
                elif mtype == "interactive":
                    interactive = message.get("interactive") or {}
                    itype = interactive.get("type")
                    if itype == "button_reply":
                        text = (interactive.get("button_reply") or {}).get("title") or ""
                    elif itype == "list_reply":
                        text = (interactive.get("list_reply") or {}).get("title") or ""
                elif mtype == "button":
                    text = (message.get("button") or {}).get("text") or ""
                text = (text or "").strip()
                if wa_id and text:
                    return {"wa_id": wa_id, "text": text, "message_id": mid}
    return None
