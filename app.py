"""Gyandeep Saathi WhatsApp webhook - guided UX + intent router + FAQ/status."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

from handler import handle_message
from whatsapp import extract_first_text_message, send_guided_reply

app = Flask(__name__)
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")


@app.get("/")
def health():
    return "Gyandeep Saathi is running", 200


@app.get("/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.post("/webhook")
def receive():
    payload = request.get_json(silent=True)
    print(payload, flush=True)

    try:
        msg = extract_first_text_message(payload)
        if msg:
            print(f"Incoming from {msg['wa_id']}: text={msg.get('text')!r} id={msg.get('id')!r}", flush=True)
            reply = handle_message(
                msg.get("text") or "",
                wa_id=msg["wa_id"],
                button_id=msg.get("id") or None,
            )
            ok = send_guided_reply(msg["wa_id"], reply)
            print(f"Send ok={ok}", flush=True)
    except Exception as exc:
        # Always ack Meta so it does not retry endlessly
        print(f"Webhook processing error: {exc}", flush=True)

    return jsonify({"status": "ok"}), 200
