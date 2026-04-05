“””
MiserBot Maximus v100 — Complete Telegram Bot
Combines: Lead capture, AI chat, Astro readings,
Music store, Credits, Premium tiers, Industry radar
“””

import os
import json
import sqlite3
import openai
from datetime import datetime
from contextlib import contextmanager
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

openai.api_key = os.environ.get(“OPENAI_API_KEY”)
BOT_TOKEN      = os.environ.get(“TELEGRAM_BOT_TOKEN”)
DASHBOARD_URL  = os.environ.get(“DASHBOARD_URL”, “https://miserbot.vercel.app”)
OWNER_ID       = int(os.environ.get(“OWNER_TELEGRAM_ID”, “0”))
DB_PATH        = “miserbot.db”

# ─────────────────────────────────────────────────────────

# DATABASE

# ─────────────────────────────────────────────────────────

@contextmanager
def get_db():
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
try:
yield conn
conn.commit()
except Exception:
conn.rollback()
raise
finally:
conn.close()

def init_db():
with get_db() as conn:
conn.executescript(”””
CREATE TABLE IF NOT EXISTS users (
telegram_id   INTEGER PRIMARY KEY,
username      TEXT,
full_name     TEXT,
email         TEXT,
plan          TEXT    DEFAULT ‘free’,
plan_expires  TEXT,
credits       INTEGER DEFAULT 50,
joined_at     TEXT    DEFAULT (datetime(‘now’)),
last_seen     TEXT    DEFAULT (datetime(‘now’))
);

```
        CREATE TABLE IF NOT EXISTS leads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER,
            name        TEXT,
            email       TEXT,
            phone       TEXT,
            source      TEXT    DEFAULT 'bot',
            status      TEXT    DEFAULT 'new',
            notes       TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            product      TEXT,
            amount       REAL,
            stripe_ref   TEXT,
            created_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS catalog (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT,
            price_cents  INTEGER,
            file_id      TEXT,
            duration     TEXT,
            features     TEXT,
            active       INTEGER DEFAULT 1,
            created_at   TEXT    DEFAULT (datetime('now'))
        );
    """)
print("✅ DB ready")
```

# ─────────────────────────────────────────────────────────

# USER HELPERS

# ─────────────────────────────────────────────────────────

def get_or_create_user(tid, username=””, full_name=””) -> dict:
with get_db() as conn:
row = conn.execute(
“SELECT * FROM users WHERE telegram_id=?”, (tid,)
).fetchone()
if row:
conn.execute(
“UPDATE users SET last_seen=datetime(‘now’) WHERE telegram_id=?”, (tid,)
)
return dict(row)
conn.execute(
“INSERT INTO users (telegram_id,username,full_name) VALUES (?,?,?)”,
(tid, username, full_name)
)
return get_user(tid)

def get_user(tid) -> dict:
with get_db() as conn:
row = conn.execute(
“SELECT * FROM users WHERE telegram_id=?”, (tid,)
).fetchone()
return dict(row) if row else {}

def get_balance(tid) -> int:
return get_user(tid).get(“credits”, 0)

def deduct(tid, amount, note=””) -> bool:
bal = get_balance(tid)
if bal < amount:
return False
with get_db() as conn:
conn.execute(
“UPDATE users SET credits=credits-? WHERE telegram_id=?”,
(amount, tid)
)
return True

def add_credits(tid, amount):
with get_db() as conn:
conn.execute(
“UPDATE users SET credits=credits+? WHERE telegram_id=?”,
(amount, tid)
)

def is_premium(tid) -> bool:
user = get_user(tid)
if user.get(“plan”, “free”) == “free”:
return False
exp = user.get(“plan_expires”)
if not exp:
return False
return datetime.fromisoformat(exp) > datetime.utcnow()

# ─────────────────────────────────────────────────────────

# MENUS

# ─────────────────────────────────────────────────────────

def main_menu(user: dict) -> InlineKeyboardMarkup:
bal  = user.get(“credits”, 0)
plan = user.get(“plan”, “free”).title()
keyboard = [
[
InlineKeyboardButton(“🤖 AI Chat”,          callback_data=“m_chat”),
InlineKeyboardButton(“🎯 Capture Lead”,     callback_data=“m_capture”),
],
[
InlineKeyboardButton(“📋 My Leads”,         callback_data=“m_leads”),
InlineKeyboardButton(“🌍 Destiny Reading”,  callback_data=“m_reading”),
],
[
InlineKeyboardButton(“🎵 Music Store”,      callback_data=“m_music”),
InlineKeyboardButton(“📣 Outreach”,         callback_data=“m_outreach”),
],
[
InlineKeyboardButton(f”⭐ Credits ({bal})”, callback_data=“m_credits”),
InlineKeyboardButton(“🚀 Premium”,          callback_data=“m_premium”),
],
[
InlineKeyboardButton(“⚙️ Settings”,        callback_data=“m_settings”),
InlineKeyboardButton(“📊 Dashboard”,        callback_data=“m_dashboard”),
],
]
return InlineKeyboardMarkup(keyboard)

def back_btn(target=“m_main”):
return InlineKeyboardMarkup([
[InlineKeyboardButton(“◀️ Back”, callback_data=target)]
])

def credits_menu(bal: int) -> InlineKeyboardMarkup:
keyboard = [
[InlineKeyboardButton(f”💰 Balance: ⭐{bal}”, callback_data=“noop”)],
[
InlineKeyboardButton(“⭐100 — $4.99”,  callback_data=“buy_credits_100”),
InlineKeyboardButton(“⭐300 — $12.99”, callback_data=“buy_credits_300”),
],
[
InlineKeyboardButton(“⭐700 — $24.99”, callback_data=“buy_credits_700”),
],
[InlineKeyboardButton(“◀️ Back”, callback_data=“m_main”)],
]
return InlineKeyboardMarkup(keyboard)

def premium_menu() -> InlineKeyboardMarkup:
keyboard = [
[InlineKeyboardButton(“👑 Starter — $19/mo”,   callback_data=“sub_starter”)],
[InlineKeyboardButton(“💼 Pro — $49/mo”,        callback_data=“sub_pro”)],
[InlineKeyboardButton(“🏢 Agency — $149/mo”,    callback_data=“sub_agency”)],
[InlineKeyboardButton(“◀️ Back”,                callback_data=“m_main”)],
]
return InlineKeyboardMarkup(keyboard)

def reading_menu() -> InlineKeyboardMarkup:
keyboard = [
[InlineKeyboardButton(“🆓 Free Preview (City #1)”, callback_data=“reading_free”)],
[InlineKeyboardButton(“🔓 Full Reading — $97”,     callback_data=“reading_full”)],
[InlineKeyboardButton(“👑 VIP Reading — $297”,     callback_data=“reading_vip”)],
[InlineKeyboardButton(“◀️ Back”,                   callback_data=“m_main”)],
]
return InlineKeyboardMarkup(keyboard)

# ─────────────────────────────────────────────────────────

# AI CHAT SYSTEM PROMPT

# ─────────────────────────────────────────────────────────

MISERBOT_SYSTEM = “””
You are MiserBot Maximus — an elite AI business automation assistant.
You help entrepreneurs, artists, and independent builders with:

- Business strategy and lead generation
- Music marketing and direct-to-fan monetization
- Astrocartography and relocation strategy
- AI tools and automation
- Marketing, branding, and revenue growth

Tone: Sharp, confident, modern, results-focused.
Always give actionable advice. Never be vague.
Keep responses under 300 words unless asked for more detail.
“””

conversation_histories = {}  # per-user memory

async def ask_ai(user_id: int, message: str, system: str = MISERBOT_SYSTEM) -> str:
if user_id not in conversation_histories:
conversation_histories[user_id] = []

```
conversation_histories[user_id].append({"role": "user", "content": message})

# Keep rolling window of 20 messages
if len(conversation_histories[user_id]) > 20:
    conversation_histories[user_id].pop(0)

messages = [{"role": "system", "content": system}] + conversation_histories[user_id]

response = openai.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    max_tokens=800,
    temperature=0.85,
)

reply = response.choices[0].message.content
conversation_histories[user_id].append({"role": "assistant", "content": reply})
return reply
```

# ─────────────────────────────────────────────────────────

# READING FLOW

# ─────────────────────────────────────────────────────────

READING_STEPS = [“birth_date”, “birth_time”, “birth_city”, “birth_name”]

READING_PROMPTS = {
“birth_date”: (
“🌟 *Astrocartography Destiny Reading*\n\n”
“I’ll map your planetary lines across the globe and reveal where “
“your soul is coded to thrive.\n\n”
“📅 First — send your birthday:\n`MM/DD/YYYY`”
),
“birth_time”: “⏰ Send your birth time:\n`HH:MM AM/PM`\n\nDon’t know? Send `unknown`”,
“birth_city”: “🌍 Where were you born?\n\n_Example: Miami, USA_”,
“birth_name”: “✨ Last thing — what’s your first name?”,
}

async def run_reading_teaser(update, ctx, uid):
data = ctx.user_data.get(“reading_data”, {})

```
prompt = (
    f"You are a luxury astrocartography reading service called MiserBot.\n"
    f"Client info: Name={data.get('name')}, "
    f"Born={data.get('birth_date')} at {data.get('birth_time')} "
    f"in {data.get('birth_city')}.\n\n"
    f"Generate a compelling FREE TEASER reading:\n"
    f"1. State their Sun sign based on birth date\n"
    f"2. Reveal ONE destiny city with its planetary line and meaning\n"
    f"3. Tease 4 more locked cities\n"
    f"4. End with a powerful upsell to the full $97 reading\n\n"
    f"Tone: Luxury, spiritual, confident. Under 200 words."
)

response = await ask_ai(uid, prompt)

keyboard = [
    [InlineKeyboardButton("🔓 Full Reading — $97",    callback_data="reading_full")],
    [InlineKeyboardButton("👑 VIP Reading — $297",    callback_data="reading_vip")],
    [InlineKeyboardButton("🏠 View Listings",         callback_data="reading_listings")],
    [InlineKeyboardButton("◀️ Main Menu",             callback_data="m_main")],
]

await update.message.reply_text(
    f"🌍 *{data.get('name', 'Your')} Destiny Map*\n\n{response}",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

# ─────────────────────────────────────────────────────────

# MUSIC STORE

# ─────────────────────────────────────────────────────────

async def show_music_store(update, ctx, fan):
with get_db() as conn:
tracks = conn.execute(
“SELECT * FROM catalog WHERE active=1 ORDER BY created_at DESC”
).fetchall()

```
if not tracks:
    await update.callback_query.edit_message_text(
        "🎵 *Music Store*\n\n"
        "No tracks yet — catalog coming soon.\n\n"
        "_Subscribe to get notified when music drops._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_btn()
    )
    return

lines = ["🎵 *Direct Music Store*\n_Tap a number to buy & download instantly_\n"]
keyboard = []
row = []

for i, t in enumerate(tracks, 1):
    feat = f" ({t['features']})" if t.get("features") else ""
    dur  = f" {t['duration']}" if t.get("duration") else ""
    price = f"${t['price_cents']/100:.2f}"
    lines.append(f"*{i}.* _{t['title']}{feat}_ — {price}{dur}")
    row.append(InlineKeyboardButton(str(i), callback_data=f"track_{t['id']}"))
    if len(row) == 5:
        keyboard.append(row)
        row = []
if row:
    keyboard.append(row)

keyboard.append([
    InlineKeyboardButton("💿 Full Album Bundle", callback_data="album_bundle"),
    InlineKeyboardButton("◀️ Back",              callback_data="m_main"),
])

await update.callback_query.edit_message_text(
    "\n".join(lines),
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

# ─────────────────────────────────────────────────────────

# /start

# ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
fan  = get_or_create_user(user.id, user.username or “”, user.full_name or “”)
bal  = fan.get(“credits”, 50)

```
await update.message.reply_text(
    f"👑 *Welcome to MiserBot Maximus v100*\n\n"
    f"The sovereign AI platform for business automation, "
    f"astrocartography readings, and direct music commerce.\n\n"
    f"⭐ Your starting credits: *{bal}*\n\n"
    f"No middlemen. No platforms. Pure sovereign power.\n\n"
    f"Choose your move 👇",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=main_menu(fan)
)
```

# ─────────────────────────────────────────────────────────

# /menu

# ─────────────────────────────────────────────────────────

async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
fan = get_or_create_user(update.effective_user.id)
await update.message.reply_text(
“👑 *MiserBot Command Center*”,
parse_mode=ParseMode.MARKDOWN,
reply_markup=main_menu(fan)
)

# ─────────────────────────────────────────────────────────

# /reading

# ─────────────────────────────────────────────────────────

async def cmd_reading(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data[“flow”] = “reading”
ctx.user_data[“reading_step”] = “birth_date”
ctx.user_data[“reading_data”] = {}
await update.message.reply_text(
READING_PROMPTS[“birth_date”],
parse_mode=ParseMode.MARKDOWN
)

# ─────────────────────────────────────────────────────────

# /radar — Industry contact finder

# ─────────────────────────────────────────────────────────

async def cmd_radar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
args = “ “.join(ctx.args).strip() if ctx.args else “”
if args:
await run_radar(update, ctx, args)
else:
ctx.user_data[“flow”] = “radar”
await update.message.reply_text(
“📡 *Royal Radar*\n\nWhich city is His Majesty visiting?”,
parse_mode=ParseMode.MARKDOWN
)

async def run_radar(update, ctx, city: str):
uid = update.effective_user.id
await update.message.reply_text(
f”📡 Scanning {city.title()} music industry…”,
parse_mode=ParseMode.MARKDOWN
)

```
prompt = (
    f"You are a music industry intelligence analyst.\n"
    f"List the 5 most important music industry contacts in {city} "
    f"that an independent Caribbean recording artist should know.\n\n"
    f"Include: promoters, A&Rs, radio DJs, managers, booking agents, "
    f"playlist curators, studio owners.\n\n"
    f"For each person provide ONLY publicly known/verified information:\n"
    f"- Name and title\n"
    f"- Company\n"
    f"- Instagram handle\n"
    f"- Email if public\n"
    f"- One tactical note on how to approach them\n\n"
    f"Format each contact clearly. Be specific and accurate."
)

response = await ask_ai(uid, prompt)

await update.message.reply_text(
    f"📡 *Industry Contacts — {city.title()}*\n\n{response}",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Draft Outreach Email", callback_data=f"draft_email_{city}")],
        [InlineKeyboardButton("📡 Scan Another City",    callback_data="radar_city")],
        [InlineKeyboardButton("◀️ Main Menu",            callback_data="m_main")],
    ])
)
```

# ─────────────────────────────────────────────────────────

# /brief — Daily briefing (owner only)

# ─────────────────────────────────────────────────────────

async def cmd_brief(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid   = update.effective_user.id
today = datetime.now().strftime(”%A, %B %d, %Y”)

```
thinking = await update.message.reply_text("👑 _Preparing royal briefing..._",
                                            parse_mode=ParseMode.MARKDOWN)
prompt = (
    f"Today is {today}. Deliver a daily strategic briefing for a sovereign "
    f"independent recording artist and entrepreneur. Include:\n"
    f"1. Today's #1 priority action\n"
    f"2. One music marketing move to make today\n"
    f"3. One mindset insight\n"
    f"4. One industry trend to watch\n\n"
    f"Address as 'Your Majesty'. Under 250 words. Sharp and actionable."
)

response = await ask_ai(uid, prompt)
await thinking.delete()
await update.message.reply_text(
    f"📜 *Royal Briefing — {today}*\n\n{response}",
    parse_mode=ParseMode.MARKDOWN,
    reply_markup=back_btn("m_main")
)
```

# ─────────────────────────────────────────────────────────

# CALLBACK HANDLER

# ─────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
uid  = update.effective_user.id
fan  = get_or_create_user(uid)
data = query.data

```
# ── MAIN MENU ────────────────────────────────────────
if data == "m_main":
    await query.edit_message_text(
        "👑 *MiserBot Command Center*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(fan)
    )

# ── AI CHAT ──────────────────────────────────────────
elif data == "m_chat":
    ctx.user_data["flow"] = "chat"
    await query.edit_message_text(
        "🤖 *AI Chat — MiserBot Maximus*\n\n"
        "Ask me anything — business, music, marketing, strategy.\n\n"
        "Send your message:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_btn()
    )

# ── LEAD CAPTURE ─────────────────────────────────────
elif data == "m_capture":
    ctx.user_data["flow"] = "capture"
    await query.edit_message_text(
        "🎯 *Capture a Lead*\n\n"
        "Send me the lead info in any format:\n\n"
        "`Name | Email | Phone | Notes`\n\n"
        "_Or just paste their contact info and I'll parse it._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_btn()
    )

# ── LEADS LIST ────────────────────────────────────────
elif data == "m_leads":
    with get_db() as conn:
        leads = conn.execute(
            "SELECT * FROM leads WHERE owner_id=? ORDER BY created_at DESC LIMIT 10",
            (uid,)
        ).fetchall()

    if not leads:
        await query.edit_message_text(
            "📋 *My Leads*\n\nNo leads yet. Start capturing! 🎯",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 Capture Lead", callback_data="m_capture")],
                [InlineKeyboardButton("◀️ Back",          callback_data="m_main")],
            ])
        )
        return

    lines = ["📋 *Recent Leads*\n"]
    for i, lead in enumerate(leads, 1):
        lines.append(
            f"*{i}.* {lead['name']} — {lead['email']}\n"
            f"   📱 {lead['phone'] or '—'} | 🏷 {lead['status']}"
        )

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_btn()
    )

# ── READING ───────────────────────────────────────────
elif data == "m_reading":
    await query.edit_message_text(
        "🌍 *Astrocartography Destiny Reading*\n\n"
        "Discover where on Earth your soul is coded to thrive — "
        "love, money, health, purpose.\n\n"
        "Choose your experience:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reading_menu()
    )

elif data == "reading_free":
    ctx.user_data["flow"] = "reading"
    ctx.user_data["reading_step"] = "birth_date"
    ctx.user_data["reading_data"] = {}
    await query.edit_message_text(
        READING_PROMPTS["birth_date"],
        parse_mode=ParseMode.MARKDOWN
    )

elif data == "reading_full":
    url = f"{DASHBOARD_URL}/checkout/full_reading?uid={uid}"
    await query.edit_message_text(
        "🔓 *Full Destiny Reading — $97*\n\n"
        "• All 5 destiny cities fully explained\n"
        "• Love, career, health & spiritual zones\n"
        "• Curated rental listings in your cities\n"
        "• 30-day relocation action plan\n"
        "• PDF reading delivered instantly\n\n"
        "Tap below to unlock 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay $97 — Unlock Now", url=url)],
            [InlineKeyboardButton("◀️ Back", callback_data="m_reading")],
        ])
    )

elif data == "reading_vip":
    url = f"{DASHBOARD_URL}/checkout/vip_reading?uid={uid}"
    await query.edit_message_text(
        "👑 *VIP Reading — $297*\n\n"
        "• Full personalized astrocartography report\n"
        "• 60-min 1:1 video session\n"
        "• Curated listing search in top 3 cities\n"
        "• 90-day relocation roadmap\n"
        "• 30-day direct access\n\n"
        "The full white-glove experience. 🌟",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Book VIP — $297", url=url)],
            [InlineKeyboardButton("◀️ Back", callback_data="m_reading")],
        ])
    )

# ── MUSIC STORE ───────────────────────────────────────
elif data == "m_music":
    await show_music_store(update, ctx, fan)

# ── CREDITS ───────────────────────────────────────────
elif data == "m_credits":
    bal = get_balance(uid)
    await query.edit_message_text(
        f"⭐ *Your Credits*\n\nBalance: *{bal} credits*\n\n"
        f"Credits power AI chat, readings, and features.\n"
        f"Top up below 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=credits_menu(bal)
    )

elif data.startswith("buy_credits_"):
    pack = data.replace("buy_credits_", "")
    url  = f"{DASHBOARD_URL}/checkout/credits_{pack}?uid={uid}"
    packs = {"100": "$4.99", "300": "$12.99", "700": "$24.99"}
    price = packs.get(pack, "")
    await query.edit_message_text(
        f"⭐ *Buy {pack} Credits — {price}*\n\n"
        f"Tap below to complete payment 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Pay {price}", url=url)],
            [InlineKeyboardButton("◀️ Back", callback_data="m_credits")],
        ])
    )

# ── PREMIUM ───────────────────────────────────────────
elif data == "m_premium":
    await query.edit_message_text(
        "🚀 *MiserBot Premium*\n\n"
        "Unlock all AI models, unlimited leads, "
        "astro readings, bulk outreach, and more.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=premium_menu()
    )

elif data.startswith("sub_"):
    plan = data.replace("sub_", "")
    url  = f"{DASHBOARD_URL}/checkout/{plan}?uid={uid}"
    prices = {"starter": "$19/mo", "pro": "$49/mo", "agency": "$149/mo"}
    price = prices.get(plan, "")
    await query.edit_message_text(
        f"🚀 *{plan.title()} Plan — {price}*\n\n"
        f"[Complete Checkout]({url})",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Subscribe {price}", url=url)],
            [InlineKeyboardButton("◀️ Back", callback_data="m_premium")],
        ])
    )

# ── OUTREACH ──────────────────────────────────────────
elif data == "m_outreach":
    ctx.user_data["flow"] = "outreach"
    await query.edit_message_text(
        "📣 *Bulk Outreach*\n\n"
        "Tell me what you want to send and who to send it to.\n\n"
        "_Example: Send a follow-up to all new leads from this week_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_btn()
    )

# ── DASHBOARD ─────────────────────────────────────────
elif data == "m_dashboard":
    url = f"{DASHBOARD_URL}?uid={uid}"
    await query.edit_message_text(
        f"📊 *Your Dashboard*\n\n[Open Dashboard]({url})",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Open Dashboard", url=url)],
            [InlineKeyboardButton("◀️ Back", callback_data="m_main")],
        ])
    )

# ── SETTINGS ─────────────────────────────────────────
elif data == "m_settings":
    user = get_user(uid)
    await query.edit_message_text(
        f"⚙️ *Settings*\n\n"
        f"👤 Name: {user.get('full_name', '—')}\n"
        f"📧 Email: {user.get('email', 'Not set')}\n"
        f"🎫 Plan: {user.get('plan', 'free').title()}\n"
        f"⭐ Credits: {user.get('credits', 0)}\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📧 Set Email",  callback_data="set_email")],
            [InlineKeyboardButton("◀️ Back",        callback_data="m_main")],
        ])
    )

elif data == "set_email":
    ctx.user_data["flow"] = "set_email"
    await query.edit_message_text(
        "📧 Send your email address:",
        parse_mode=ParseMode.MARKDOWN
    )

elif data == "radar_city":
    ctx.user_data["flow"] = "radar"
    await query.edit_message_text(
        "📡 Which city, Your Majesty?",
        parse_mode=ParseMode.MARKDOWN
    )

elif data.startswith("draft_email_"):
    city = data.replace("draft_email_", "")
    uid  = update.effective_user.id
    prompt = (
        f"Write a short professional cold outreach email from BazraGod, "
        f"a sovereign independent Caribbean recording artist, "
        f"to a music industry contact in {city}. "
        f"Lead with value. Under 100 words. Include subject line."
    )
    response = await ask_ai(uid, prompt)
    await query.edit_message_text(
        f"📧 *Outreach Template — {city.title()}*\n\n```{response}```",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_btn("m_main")
    )

elif data == "noop":
    pass

else:
    await query.edit_message_text(
        "⚙️ Coming soon!",
        reply_markup=back_btn()
    )
```

# ─────────────────────────────────────────────────────────

# MESSAGE HANDLER

# ─────────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid   = update.effective_user.id
text  = update.message.text.strip()
flow  = ctx.user_data.get(“flow”)
fan   = get_or_create_user(uid)

```
# ── AI CHAT ──────────────────────────────────────────
if flow == "chat":
    thinking = await update.message.reply_text(
        "🤖 _Thinking..._", parse_mode=ParseMode.MARKDOWN
    )
    response = await ask_ai(uid, text)
    await thinking.delete()
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Keep Chatting",  callback_data="m_chat")],
            [InlineKeyboardButton("◀️ Main Menu",      callback_data="m_main")],
        ])
    )

# ── READING FLOW ──────────────────────────────────────
elif flow == "reading":
    step = ctx.user_data.get("reading_step")
    rd   = ctx.user_data.get("reading_data", {})

    if step == "birth_date":
        rd["birth_date"] = text
        ctx.user_data["reading_data"] = rd
        ctx.user_data["reading_step"] = "birth_time"
        await update.message.reply_text(
            READING_PROMPTS["birth_time"], parse_mode=ParseMode.MARKDOWN
        )
    elif step == "birth_time":
        rd["birth_time"] = text
        ctx.user_data["reading_data"] = rd
        ctx.user_data["reading_step"] = "birth_city"
        await update.message.reply_text(
            READING_PROMPTS["birth_city"], parse_mode=ParseMode.MARKDOWN
        )
    elif step == "birth_city":
        rd["birth_city"] = text
        ctx.user_data["reading_data"] = rd
        ctx.user_data["reading_step"] = "birth_name"
        await update.message.reply_text(
            READING_PROMPTS["birth_name"], parse_mode=ParseMode.MARKDOWN
        )
    elif step == "birth_name":
        rd["name"] = text.split()[0]
        ctx.user_data["reading_data"] = rd
        ctx.user_data["reading_step"] = None
        ctx.user_data["flow"] = None

        calculating = await update.message.reply_text(
            "🔮 _Calculating your destiny map..._",
            parse_mode=ParseMode.MARKDOWN
        )
        await run_reading_teaser(update, ctx, uid)
        await calculating.delete()

# ── LEAD CAPTURE ──────────────────────────────────────
elif flow == "capture":
    ctx.user_data["flow"] = None
    # Parse with AI
    prompt = (
        f"Extract lead info from this text and return JSON only:\n{text}\n\n"
        f"Return: {{\"name\": \"\", \"email\": \"\", \"phone\": \"\", \"notes\": \"\"}}\n"
        f"Return ONLY the JSON, nothing else."
    )
    response = await ask_ai(uid, prompt)
    try:
        clean = response.replace("```json", "").replace("```", "").strip()
        lead  = json.loads(clean)
    except Exception:
        lead = {"name": text, "email": "", "phone": "", "notes": ""}

    with get_db() as conn:
        conn.execute(
            "INSERT INTO leads (owner_id,name,email,phone,notes) VALUES (?,?,?,?,?)",
            (uid, lead.get("name"), lead.get("email"),
             lead.get("phone"), lead.get("notes"))
        )

    await update.message.reply_text(
        f"✅ *Lead Captured!*\n\n"
        f"👤 {lead.get('name', '—')}\n"
        f"📧 {lead.get('email', '—')}\n"
        f"📱 {lead.get('phone', '—')}\n\n"
        f"Saved to your CRM. 🎯",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 View All Leads", callback_data="m_leads")],
            [InlineKeyboardButton("◀️ Main Menu",      callback_data="m_main")],
        ])
    )

# ── RADAR ─────────────────────────────────────────────
elif flow == "radar":
    ctx.user_data["flow"] = None
    await run_radar(update, ctx, text)

# ── SET EMAIL ─────────────────────────────────────────
elif flow == "set_email":
    ctx.user_data["flow"] = None
    if "@" in text:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET email=? WHERE telegram_id=?", (text, uid)
            )
        await update.message.reply_text(
            f"✅ Email saved: `{text}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_btn("m_settings")
        )
    else:
        await update.message.reply_text("❌ That doesn't look like an email. Try again.")

# ── DEFAULT ───────────────────────────────────────────
else:
    # Smart default — just chat with AI
    thinking = await update.message.reply_text(
        "🤖 _Processing..._", parse_mode=ParseMode.MARKDOWN
    )
    response = await ask_ai(uid, text)
    await thinking.delete()
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Main Menu", callback_data="m_main")]
        ])
    )
```

# ─────────────────────────────────────────────────────────

# BUILD APP

# ─────────────────────────────────────────────────────────

def build_app():
init_db()
app = Application.builder().token(BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start",   cmd_start))
app.add_handler(CommandHandler("menu",    cmd_menu))
app.add_handler(CommandHandler("reading", cmd_reading))
app.add_handler(CommandHandler("radar",   cmd_radar))
app.add_handler(CommandHandler("brief",   cmd_brief))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

return app
```

if **name** == “**main**”:
print(“👑 MiserBot Maximus v100 — ONLINE”)
build_app().run_polling()
