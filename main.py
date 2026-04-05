import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "miserbot.ai@gmail.com")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "8741545426"

# in-memory lead storage
LEADS = []


@app.route("/")
def home():
    return "👑 MiserBot v100 backend live"


# ───────── EMAIL ─────────

def send_email(name,email,phone):

    body = {
        "personalizations":[
            {
                "to":[{"email":SENDGRID_FROM_EMAIL}],
                "subject":"🚀 New MiserBot Lead"
            }
        ],
        "from":{
            "email":SENDGRID_FROM_EMAIL,
            "name":"MiserBot"
        },
        "content":[
            {
                "type":"text/html",
                "value":f"""
                <h2>New Lead</h2>
                <p>Name: {name}</p>
                <p>Email: {email}</p>
                <p>Phone: {phone}</p>
                """
            }
        ]
    }

    requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=body,
        headers={
            "Authorization":f"Bearer {SENDGRID_API_KEY}",
            "Content-Type":"application/json"
        }
    )

    print("📧 Email sent")


# ───────── TELEGRAM ─────────

def send_telegram_alert(name,email,phone):

    message=f"""
🚀 New MiserBot Lead

Name: {name}
Email: {email}
Phone: {phone}
"""

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id":TELEGRAM_CHAT_ID,
            "text":message
        }
    )

    print("📲 Telegram alert sent")


# ───────── WEBHOOK ─────────

@app.route("/webhook",methods=["POST"])
def webhook():

    data=request.json

    print("🔥 WEBHOOK HIT:",data)

    name=data.get("name")
    email=data.get("email")
    phone=data.get("phone")

    # save lead
    LEADS.append({
        "name":name,
        "email":email,
        "phone":phone
    })

    send_email(name,email,phone)
    send_telegram_alert(name,email,phone)

    return jsonify({"status":"success"})


# ───────── DASHBOARD ─────────

@app.route("/leads")
def show_leads():

    html="<h1>MiserBot Leads</h1>"

    for lead in LEADS:
        html+=f"""
        <p>
        Name: {lead['name']}<br>
        Email: {lead['email']}<br>
        Phone: {lead['phone']}
        </p>
        <hr>
        """

    return html


if __name__=="__main__":

    port=int(os.environ.get("PORT",3000))

    app.run(host="0.0.0.0",port=port)
