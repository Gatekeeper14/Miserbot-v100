import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👑 MiserBot v100 AI Online\n\n"
        "Ask me anything about your leads or business."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start\n"
        "/help\n"
        "/status"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ MiserBot AI system running.")

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are MiserBot, an AI assistant helping manage business leads."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        reply = response.choices[0].message.content

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("AI error.")
        print(e)

def main():

    print("🤖 MiserBot AI starting...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    print("🧠 MiserBot AI running...")
    app.run_polling()

if __name__ == "__main__":
    main()
