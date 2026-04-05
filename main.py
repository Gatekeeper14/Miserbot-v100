import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "miserbot.ai@gmail.com")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "8741545426"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


@app.route("/", methods=["GET"])
def home():
    return "👑 MiserBot v100 backend live"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ───────── EMAIL TO YOU ─────────

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


# ───────── TELEGRAM ALERT ─────────

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


# ───────── AI FOLLOW UP ─────────

def generate_ai_reply(name):

    response=client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
                "content":"You are MiserBot, a friendly AI assistant that welcomes potential customers and asks what service they need."
            },
            {
                "role":"user",
                "content":f"A new lead named {name} just signed up."
            }
        ]
    )

    return response.choices[0].message.content


def send_ai_email(name,email):

    ai_message=generate_ai_reply(name)

    body = {
        "personalizations":[
            {
                "to":[{"email":email}],
                "subject":"Welcome from MiserBot"
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
                <p>Hi {name},</p>

                <p>{ai_message}</p>

                <p>– MiserBot AI</p>
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

    print("🤖 AI email sent")


# ───────── WEBHOOK ─────────

@app.route("/webhook",methods=["POST"])
def webhook():

    data=request.json

    print("🔥 WEBHOOK HIT:",data)

    name=data.get("name")
    email=data.get("email")
    phone=data.get("phone")

    send_email(name,email,phone)
    send_telegram_alert(name,email,phone)
    send_ai_email(name,email)

    return jsonify({"status":"success"})


if __name__=="__main__":

    port=int(os.environ.get("PORT",3000))

    app.run(host="0.0.0.0",port=port)
