import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "miserbot.ai@gmail.com")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "8741545426"

LEADS = []


@app.route("/")
def home():
    return "👑 MiserBot Lead Engine Live"


def send_email(name, email, phone):
    body = {
        "personalizations": [
            {
                "to": [{"email": SENDGRID_FROM_EMAIL}],
                "subject": "🚀 New MiserBot Lead"
            }
        ],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": "MiserBot"
        },
        "content": [
            {
                "type": "text/html",
                "value": f"<h2>New Lead</h2><p>Name: {name}</p><p>Email: {email}</p><p>Phone: {phone}</p>"
            }
        ]
    }

    requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=body,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    print("📧 Email sent")


def send_telegram_alert(name, email, phone):
    message = f"🚀 New MiserBot Lead\n\nName: {name}\nEmail: {email}\nPhone: {phone}"

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
    )

    print("📲 Telegram alert sent")


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("🔥 WEBHOOK HIT:", data)

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")

    LEADS.append({
        "name": name,
        "email": email,
        "phone": phone,
        "status": "NEW"
    })

    send_email(name, email, phone)
    send_telegram_alert(name, email, phone)

    return jsonify({"status": "success"})


@app.route("/dashboard")
def dashboard():

    html = """
    <html>
    <head>
    <title>MiserBot Dashboard</title>
    <style>
    body{font-family:Arial;background:#020617;color:white;padding:40px}
    table{border-collapse:collapse;width:100%}
    th,td{padding:12px;border-bottom:1px solid #333}
    th{background:#111827}
    a{color:#7c3aed;text-decoration:none}
    </style>
    </head>
    <body>

    <h1>👑 MiserBot Lead Engine</h1>

    <p><a href="/export">Download Leads CSV</a></p>

    <table>
    <tr>
    <th>Name</th>
    <th>Email</th>
    <th>Phone</th>
    <th>Status</th>
    </tr>
    """

    for lead in LEADS:
        html += f"""
        <tr>
        <td>{lead['name']}</td>
        <td>{lead['email']}</td>
        <td>{lead['phone']}</td>
        <td>{lead['status']}</td>
        </tr>
        """

    html += """
    </table>
    </body>
    </html>
    """

    return html


@app.route("/export")
def export():

    csv = "name,email,phone,status\n"

    for lead in LEADS:
        csv += f"{lead['name']},{lead['email']},{lead['phone']},{lead['status']}\n"

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=leads.csv"}
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
