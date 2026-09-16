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


def _post(payload: dict[str, Any]) -> bool:
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print(
            "WhatsApp env missing: WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID",
            flush=True,
        )
        return False
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


def send_text(to_wa_id: str, body: str) -> bool:
    """Send a plain text WhatsApp message. Returns True on HTTP success."""
    if not body or not to_wa_id:
        return False
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }
    return _post(payload)


def send_reply_buttons(to_wa_id: str, body: str, buttons: list[dict[str, str]]) -> bool:
    """Send interactive reply buttons (max 3). Each button: {id, title}."""
    if not to_wa_id or not body:
        return False
    cleaned = []
    for b in (buttons or [])[:3]:
        bid = str(b.get("id") or "").strip()
        title = str(b.get("title") or "").strip()[:20]
        if bid and title:
            cleaned.append({"type": "reply", "reply": {"id": bid[:256], "title": title}})
    if not cleaned:
        return send_text(to_wa_id, body)
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body[:1024]},
            "action": {"buttons": cleaned},
        },
    }
    return _post(payload)


def send_list_message(
    to_wa_id: str,
    body: str,
    button_label: str,
    sections: list[dict[str, Any]],
) -> bool:
    """Send interactive list message. sections: [{title, rows:[{id,title,description?}]}]."""
    if not to_wa_id or not body or not sections:
        return False
    wa_sections: list[dict[str, Any]] = []
    for sec in sections[:10]:
        rows_out = []
        for row in (sec.get("rows") or [])[:10]:
            rid = str(row.get("id") or "").strip()
            title = str(row.get("title") or "").strip()[:24]
            if not rid or not title:
                continue
            item: dict[str, str] = {"id": rid[:200], "title": title}
            desc = str(row.get("description") or "").strip()
            if desc:
                item["description"] = desc[:72]
            rows_out.append(item)
        if not rows_out:
            continue
        block: dict[str, Any] = {"rows": rows_out}
        st = str(sec.get("title") or "").strip()
        if st:
            block["title"] = st[:24]
        wa_sections.append(block)
    if not wa_sections:
        return send_text(to_wa_id, body)
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body[:1024]},
            "action": {
                "button": (button_label or "विकल्प")[:20],
                "sections": wa_sections,
            },
        },
    }
    return _post(payload)


def send_guided_reply(to_wa_id: str, reply: dict[str, Any] | str) -> bool:
    """Dispatch text / buttons / list from a guided handler payload.

    Supports multi-card payloads: {"replies": [payload, ...]} (Feedback 4.0).
    """
    if isinstance(reply, str):
        return send_text(to_wa_id, reply)
    # Separate guided cards (e.g. eligible result + next-action question)
    replies = reply.get("replies")
    if isinstance(replies, list) and replies:
        ok = True
        for card in replies:
            if not send_guided_reply(to_wa_id, card):
                ok = False
        return ok
    text = str(reply.get("text") or "")
    buttons = reply.get("buttons")
    sections = reply.get("list_sections")
    if sections:
        return send_list_message(
            to_wa_id,
            text,
            str(reply.get("list_button_label") or "विकल्प चुनें"),
            sections,
        )
    if buttons:
        return send_reply_buttons(to_wa_id, text, buttons)
    return send_text(to_wa_id, text)


def extract_first_text_message(payload: dict[str, Any] | None) -> dict[str, str] | None:
    """Pull first inbound text / button / list reply from a Meta webhook body.

    Returns wa_id, text (title or body), id (button/list id when present), message_id.
    Prefer id for routing when present; keep title as text for title-only matching.
    """
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
                reply_id = ""
                if mtype == "text":
                    text = (message.get("text") or {}).get("body") or ""
                elif mtype == "interactive":
                    interactive = message.get("interactive") or {}
                    itype = interactive.get("type")
                    if itype == "button_reply":
                        br = interactive.get("button_reply") or {}
                        text = br.get("title") or ""
                        reply_id = br.get("id") or ""
                    elif itype == "list_reply":
                        lr = interactive.get("list_reply") or {}
                        text = lr.get("title") or ""
                        reply_id = lr.get("id") or ""
                elif mtype == "button":
                    text = (message.get("button") or {}).get("text") or ""
                    reply_id = (message.get("button") or {}).get("payload") or ""
                text = (text or "").strip()
                reply_id = (reply_id or "").strip()
                if wa_id and (text or reply_id):
                    return {
                        "wa_id": wa_id,
                        "text": text or reply_id,
                        "id": reply_id,
                        "message_id": mid,
                    }
    return None
