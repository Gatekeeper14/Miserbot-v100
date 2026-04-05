import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "miserbot.ai@gmail.com")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ─────────────────────────────────────────
# HOME
# ─────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return "👑 MiserBot v100 backend is live", 200


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "live",
        "service": "miserbot-backend"
    }), 200


# ─────────────────────────────────────────
# SEND EMAIL
# ─────────────────────────────────────────

def send_email(name, email, phone):

    if not SENDGRID_API_KEY:
        print("⚠️ SendGrid API key missing")
        return

    body = {
        "personalizations": [{
            "to": [{"email": SENDGRID_FROM_EMAIL}],
            "subject": "🚀 New MiserBot Lead"
        }],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": "MiserBot"
        },
        "content": [{
            "type": "text/html",
            "value": f"""
            <h2>🚀 New Lead</h2>
            <p><b>Name:</b> {name}</p>
            <p><b>Email:</b> {email}</p>
            <p><b>Phone:</b> {phone}</p>
            """
        }]
    }

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=body,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }
        )

        print(f"📧 Email sent → {email} | status {response.status_code}")

    except Exception as e:
        print(f"❌ Email error: {e}")


# ─────────────────────────────────────────
# TELEGRAM ALERT
# ─────────────────────────────────────────

def send_telegram_alert(name, email, phone):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram variables missing")
        return

    message = f"""
🚀 New MiserBot Lead

👤 Name: {name}
📧 Email: {email}
📱 Phone: {phone}
"""

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            }
        )

        print("📲 Telegram alert sent")

    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ─────────────────────────────────────────
# WEBHOOK (FORM SUBMISSION)
# ─────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json
    print("🔥 WEBHOOK HIT:", data)

    if not data:
        return jsonify({"status": "no data"}), 400

    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    source = data.get("source", "website")

    if name and email:

        print(f"📩 New Lead → {name} | {email} | {phone} | source: {source}")

        send_email(name, email, phone)
        send_telegram_alert(name, email, phone)

        return jsonify({
            "status": "success"
        }), 200

    return jsonify({
        "status": "ok"
    }), 200


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
