import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not TOKEN or not WEBAPP_URL:
    raise SystemExit("Faltan TELEGRAM_BOT_TOKEN o WEBAPP_URL en backend/.env")


def _webapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔎 Abrir DCPI Music", web_app=WebAppInfo(url=WEBAPP_URL))]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *DCPI Music*\n\nTu reproductor musical dentro de Telegram, con letras sincronizadas.",
        parse_mode="Markdown",
        reply_markup=_webapp_keyboard(),
    )


async def music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Abrir DCPI Music", reply_markup=_webapp_keyboard())


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("music", music))
    print("Bot de DCPI Music iniciado (polling)")
    app.run_polling()


if __name__ == "__main__":
    main()
