import os
import stripe
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(**name**)
CORS(app)

# ─── Keys ────────────────────────────────────────────────

stripe.api_key              = os.environ.get(“STRIPE_SECRET_KEY”)
SENDGRID_API_KEY            = os.environ.get(“SENDGRID_API_KEY”)
TELEGRAM_BOT_TOKEN          = os.environ.get(“TELEGRAM_BOT_TOKEN”)
STRIPE_WEBHOOK_SECRET       = os.environ.get(“STRIPE_WEBHOOK_SECRET”)
SENDGRID_FROM_EMAIL         = os.environ.get(“SENDGRID_FROM_EMAIL”, “hello@miserbot.com”)
SENDGRID_FROM_NAME          = os.environ.get(“SENDGRID_FROM_NAME”, “MiserBot”)

# ─────────────────────────────────────────────────────────

# HOME

# ─────────────────────────────────────────────────────────

@app.route(”/”, methods=[“GET”])
def home():
return “👑 MiserBot Maximus v100 — Live”, 200

# ─────────────────────────────────────────────────────────

# LEAD WEBHOOK  (from Vercel frontend form)

# ─────────────────────────────────────────────────────────

@app.route(”/webhook”, methods=[“POST”])
def webhook():
data = request.json
print(“🔥 WEBHOOK HIT:”, data)

```
if not data:
    return jsonify({"status": "no data"}), 400

name  = data.get("name", "")
email = data.get("email", "")
phone = data.get("phone", "")
source = data.get("source", "website")

if name and email:
    print(f"📩 New Lead → {name} | {email} | {phone} | source: {source}")

    # Send welcome email via SendGrid
    send_welcome_email(name, email)

    # Notify via Telegram
    notify_telegram(
        f"🎯 New Lead!\n\n"
        f"👤 Name: {name}\n"
        f"📧 Email: {email}\n"
        f"📱 Phone: {phone}\n"
        f"🌐 Source: {source}"
    )

    return jsonify({"status": "success"}), 200

return jsonify({"status": "ok"}), 200
```

# ─────────────────────────────────────────────────────────

# STRIPE WEBHOOK  (payment confirmations)

# ─────────────────────────────────────────────────────────

@app.route(”/stripe/webhook”, methods=[“POST”])
def stripe_webhook():
payload   = request.data
sig       = request.headers.get(“Stripe-Signature”)

```
try:
    event = stripe.Webhook.construct_event(
        payload, sig, STRIPE_WEBHOOK_SECRET
    )
except Exception as e:
    print(f"❌ Stripe webhook error: {e}")
    return jsonify({"error": str(e)}), 400

if event["type"] == "checkout.session.completed":
    session     = event["data"]["object"]
    customer_email = session.get("customer_email", "")
    amount      = session.get("amount_total", 0)
    metadata    = session.get("metadata", {})
    telegram_id = metadata.get("telegram_id", "")
    product     = metadata.get("product", "unknown")

    print(f"💰 Payment confirmed: {customer_email} | ${amount/100:.2f} | {product}")

    notify_telegram(
        f"💰 Payment Received!\n\n"
        f"📧 {customer_email}\n"
        f"💵 ${amount/100:.2f}\n"
        f"📦 Product: {product}"
    )

    # Deliver product to Telegram user
    if telegram_id:
        deliver_product(telegram_id, product, metadata)

return jsonify({"status": "ok"}), 200
```

# ─────────────────────────────────────────────────────────

# STRIPE CHECKOUT  (create payment link)

# ─────────────────────────────────────────────────────────

@app.route(”/checkout/<product>”, methods=[“POST”])
def create_checkout(product):
data        = request.json or {}
telegram_id = data.get(“telegram_id”, “”)
email       = data.get(“email”, “”)

```
PRODUCTS = {
    "mini_reading":  {"name": "Mini Astro Reading",     "price": 2900},
    "full_reading":  {"name": "Full Destiny Reading",    "price": 9700},
    "vip_reading":   {"name": "VIP Reading + 1:1",       "price": 29700},
    "royals":        {"name": "Royals Membership",       "price": 499,  "recurring": True},
    "court":         {"name": "Court Membership",        "price": 1999, "recurring": True},
    "inner_circle":  {"name": "Inner Circle",            "price": 9900, "recurring": True},
    "credits_100":   {"name": "100 Credits",             "price": 499},
    "credits_300":   {"name": "300 Credits",             "price": 1299},
    "credits_700":   {"name": "700 Credits",             "price": 2499},
}

if product not in PRODUCTS:
    return jsonify({"error": "Product not found"}), 404

p = PRODUCTS[product]

try:
    if p.get("recurring"):
        # Subscription
        price = stripe.Price.create(
            unit_amount=p["price"],
            currency="usd",
            recurring={"interval": "month"},
            product_data={"name": p["name"]},
        )
    else:
        price = stripe.Price.create(
            unit_amount=p["price"],
            currency="usd",
            product_data={"name": p["name"]},
        )

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price.id, "quantity": 1}],
        mode="subscription" if p.get("recurring") else "payment",
        success_url=f"{os.environ.get('DASHBOARD_URL', 'https://miserbot.vercel.app')}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{os.environ.get('DASHBOARD_URL', 'https://miserbot.vercel.app')}/cancel",
        customer_email=email or None,
        metadata={
            "telegram_id": telegram_id,
            "product":     product,
        }
    )

    return jsonify({"url": session.url}), 200

except Exception as e:
    print(f"❌ Checkout error: {e}")
    return jsonify({"error": str(e)}), 500
```

# ─────────────────────────────────────────────────────────

# HEALTH CHECK

# ─────────────────────────────────────────────────────────

@app.route(”/health”, methods=[“GET”])
def health():
return jsonify({
“status”:  “live”,
“version”: “maximus-v100”,
“stripe”:  bool(stripe.api_key),
“sendgrid”: bool(SENDGRID_API_KEY),
“telegram”: bool(TELEGRAM_BOT_TOKEN),
}), 200

# ─────────────────────────────────────────────────────────

# HELPERS

# ─────────────────────────────────────────────────────────

def send_welcome_email(name: str, email: str):
if not SENDGRID_API_KEY:
print(“⚠️ No SendGrid key — skipping email”)
return

```
body = {
    "personalizations": [{
        "to": [{"email": email, "name": name}],
        "subject": f"Welcome to MiserBot, {name} 👑"
    }],
    "from": {
        "email": SENDGRID_FROM_EMAIL,
        "name":  SENDGRID_FROM_NAME
    },
    "content": [{
        "type":  "text/html",
        "value": f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto;
                    background:#0D0D0D;color:#F5F0E8;padding:40px;border-radius:12px">
          <h1 style="color:#C9A84C;text-align:center">👑 Welcome, {name}</h1>
          <p style="font-size:16px;line-height:1.8">
            You've just stepped into MiserBot — the sovereign platform for 
            AI-powered business automation, astrocartography readings, and 
            direct artist-to-fan music commerce.
          </p>
          <p style="font-size:16px;line-height:1.8">
            Your journey starts now. No middlemen. No platforms taking your cut.
            Just pure sovereign power.
          </p>
          <div style="text-align:center;margin:30px 0">
            <a href="https://t.me/MiserBot" 
               style="background:#C9A84C;color:#0D0D0D;padding:14px 28px;
                      border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px">
              Open MiserBot on Telegram
            </a>
          </div>
          <p style="color:#888;font-size:12px;text-align:center">
            MiserBot Maximus v100 — The Sovereign Stack
          </p>
        </div>
        """
    }]
}

try:
    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=body,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type":  "application/json"
        }
    )
    print(f"📧 Email sent to {email} — status: {resp.status_code}")
except Exception as e:
    print(f"❌ Email error: {e}")
```

def notify_telegram(message: str):
“”“Send notification to your own Telegram chat.”””
owner_id = os.environ.get(“OWNER_TELEGRAM_ID”)
if not TELEGRAM_BOT_TOKEN or not owner_id:
return
try:
requests.post(
f”https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage”,
json={
“chat_id”:    owner_id,
“text”:       message,
“parse_mode”: “Markdown”
}
)
except Exception as e:
print(f”❌ Telegram notify error: {e}”)

def deliver_product(telegram_id: str, product: str, metadata: dict):
“”“Deliver purchased product to user on Telegram.”””
messages = {
“mini_reading”:  “🔮 Your Mini Astro Reading is being prepared. Use /reading in MiserBot.”,
“full_reading”:  “👑 Your Full Destiny Reading is unlocked! Use /reading in MiserBot.”,
“vip_reading”:   “💎 VIP Reading confirmed! We’ll contact you within 24hrs for your 1:1 session.”,
“royals”:        “👑 Royals membership activated! You now have access to exclusive content.”,
“court”:         “⚜️ Court membership activated! Stems, acapellas and more are now unlocked.”,
“inner_circle”:  “💎 Inner Circle confirmed! Direct access and monthly meet & greet is yours.”,
“credits_100”:   “⭐ 100 credits added to your account!”,
“credits_300”:   “⭐ 300 credits added to your account!”,
“credits_700”:   “⭐ 700 credits added to your account!”,
}

```
msg = messages.get(product, "✅ Purchase confirmed! Thank you.")

try:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id":    telegram_id,
            "text":       msg,
            "parse_mode": "Markdown"
        }
    )
except Exception as e:
    print(f"❌ Delivery error: {e}")
```

# ─────────────────────────────────────────────────────────

# RUN

# ─────────────────────────────────────────────────────────

if **name** == “**main**”:
port = int(os.environ.get(“PORT”, 3000))
app.run(host=“0.0.0.0”, port=port)
