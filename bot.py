"""
MiserBot Maximus v100 — Telegram Bot
Lead capture • AI chat • Credits • Dashboard
"""

import os
import sqlite3
from contextlib import contextmanager

import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode


# ENV
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "https://miserbot.vercel.app")

openai.api_key = OPENAI_API_KEY

DB_PATH = "miserbot.db"


# DATABASE

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
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            email TEXT,
            credits INTEGER DEFAULT 50,
            joined_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            name TEXT,
            email TEXT,
            phone TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
    print("Database ready")


# USER HELPERS

def get_or_create_user(tid, username="", full_name=""):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id=?",
            (tid,)
        ).fetchone()

        if row:
            return dict(row)

        conn.execute(
            "INSERT INTO users (telegram_id,username,full_name) VALUES (?,?,?)",
            (tid, username, full_name)
        )

    return get_user(tid)


def get_user(tid):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id=?",
            (tid,)
        ).fetchone()
        return dict(row) if row else {}


def get_balance(tid):
    user = get_user(tid)
    return user.get("credits", 0)


# AI SYSTEM

SYSTEM_PROMPT = """
You are MiserBot Maximus.

You help entrepreneurs, musicians and creators with:

business strategy
lead generation
marketing
music promotion
automation
growth

Tone: confident and strategic.
Always give actionable advice.
"""


async def ask_ai(user_id, message):

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        max_tokens=600,
        temperature=0.8,
    )

    return response["choices"][0]["message"]["content"]


# MENUS

def main_menu(user):

    bal = user.get("credits", 0)

    keyboard = [

        [
            InlineKeyboardButton("AI Chat", callback_data="chat"),
            InlineKeyboardButton("Capture Lead", callback_data="capture"),
        ],

        [
            InlineKeyboardButton("My Leads", callback_data="leads"),
            InlineKeyboardButton(f"Credits ({bal})", callback_data="credits"),
        ],

        [
            InlineKeyboardButton("Dashboard", url=DASHBOARD_URL)
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


def back_btn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="menu")]
    ])


# COMMANDS

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    fan = get_or_create_user(
        user.id,
        user.username or "",
        user.full_name or ""
    )

    bal = fan.get("credits", 50)

    await update.message.reply_text(
        f"Welcome to MiserBot\n\nCredits: {bal}",
        reply_markup=main_menu(fan)
    )


# CALLBACKS

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    uid = update.effective_user.id
    fan = get_or_create_user(uid)

    data = query.data

    if data == "menu":

        await query.edit_message_text(
            "Command Center",
            reply_markup=main_menu(fan)
        )

    elif data == "chat":

        ctx.user_data["flow"] = "chat"

        await query.edit_message_text(
            "Send your question.",
            reply_markup=back_btn()
        )

    elif data == "capture":

        ctx.user_data["flow"] = "capture"

        await query.edit_message_text(
            "Send: Name | Email | Phone | Notes",
            reply_markup=back_btn()
        )

    elif data == "leads":

        with get_db() as conn:

            leads = conn.execute(
                "SELECT * FROM leads WHERE owner_id=? ORDER BY created_at DESC LIMIT 10",
                (uid,)
            ).fetchall()

        if not leads:

            await query.edit_message_text(
                "No leads yet.",
                reply_markup=back_btn()
            )
            return

        lines = ["Recent Leads:\n"]

        for lead in leads:
            lines.append(f"{lead['name']} - {lead['email']}")

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=back_btn()
        )


# MESSAGE HANDLER

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    text = update.message.text.strip()

    flow = ctx.user_data.get("flow")

    if flow == "chat":

        thinking = await update.message.reply_text("Thinking...")

        response = await ask_ai(uid, text)

        await thinking.delete()

        await update.message.reply_text(
            response,
            reply_markup=back_btn()
        )

    elif flow == "capture":

        ctx.user_data["flow"] = None

        parts = [p.strip() for p in text.split("|")]

        name = parts[0] if len(parts) > 0 else ""
        email = parts[1] if len(parts) > 1 else ""
        phone = parts[2] if len(parts) > 2 else ""
        notes = parts[3] if len(parts) > 3 else ""

        with get_db() as conn:

            conn.execute(
                "INSERT INTO leads (owner_id,name,email,phone,notes) VALUES (?,?,?,?,?)",
                (uid, name, email, phone, notes)
            )

        await update.message.reply_text(
            f"Lead saved\n{name}\n{email}\n{phone}",
            reply_markup=back_btn()
        )

    else:

        response = await ask_ai(uid, text)

        await update.message.reply_text(response)


# BUILD BOT

def build_app():

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))

    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return app


# RUN

if __name__ == "__main__":

    print("MiserBot Online")

    build_app().run_polling()
