import os
from flask import Flask, request, jsonify

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
    # Stub only — real Gyandeep logic comes later
    print(request.get_json(silent=True), flush=True)
    return jsonify({"status": "ok"}), 200
