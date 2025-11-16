import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from flask import Flask, request

# ------------------ CONFIG ------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
WEBHOOK_URL = f"https://<YOUR_KOYEB_APP_URL>/{BOT_TOKEN}"  # Replace with your Koyeb app URL

# ------------------ STATES ------------------
NAME, BIRTHDAY, ADDRESS, CITY, EDUCATION, EXPERIENCE, LAST_JOB, MARITAL, SALARY, COMPUTER, PHONE = range(11)

# ------------------ TELEGRAM BOT ------------------
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "👋 Salom! Iltimos, ismingizni kiriting:"
    await update.message.reply_text(welcome_text)
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("🗓️ Tug‘ilgan sanangizni kun/oy/yil formatida yozing:")
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['birthday'] = update.message.text
    await update.message.reply_text("📍 Qaysi manzilda yashaysiz?")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("🏥 Qaysi hududda ishlashni xohlaysiz?")
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("🎓 Ta’lim darajangiz (o‘rta maxsus / oliy):")
    return EDUCATION

async def get_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['education'] = update.message.text
    await update.message.reply_text("⏳ Bu sohada qancha vaqt ishlagansiz?")
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = update.message.text
    await update.message.reply_text("💼 Oldingi ish joyingiz?")
    return LAST_JOB

async def get_last_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_job'] = update.message.text
    await update.message.reply_text("💍 Oilaviy holatingiz?")
    return MARITAL

async def get_marital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['marital'] = update.message.text
    await update.message.reply_text("💸 Qancha maosh kutmoqdasiz?")
    return SALARY

async def get_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['salary'] = update.message.text
    await update.message.reply_text(
        "💻 Kompyuter ko‘nikmalari:\n"
        "1 - Hech qachon ishlamaganman\n"
        "2 - Boshlang‘ich\n"
        "3 - O‘rta daraja\n"
        "4 - Juda yaxshi"
    )
    return COMPUTER

async def get_computer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['computer'] = update.message.text
    await update.message.reply_text("☎️ Telefon raqamingizni kiriting:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    data['phone'] = update.message.text

    summary = f"""
📋 Yangi ariza:

👤 Ism: {data['name']}
🗓️ Tug‘ilgan sana: {data['birthday']}
📍 Manzil: {data['address']}
🏥 Hudud: {data['city']}
🎓 Ta’lim: {data['education']}
⏳ Tajriba: {data['experience']}
💼 Oldingi ish: {data['last_job']}
💍 Oilaviy holati: {data['marital']}
💸 Maosh: {data['salary']}
💻 Kompyuter: {data['computer']}
☎️ Telefon: {data['phone']}
"""
    await context.bot.send_message(chat_id=ADMIN_ID, text=summary)
    await update.message.reply_text(f"📋 Siz yuborgan ariza:\n{summary}\n✅ Arizangiz yuborildi!")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Ariza jarayoni bekor qilindi.")
    return ConversationHandler.END

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
        EDUCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_education)],
        EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
        LAST_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_last_job)],
        MARITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_marital)],
        SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_salary)],
        COMPUTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_computer)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app_bot.add_handler(conv)

# ------------------ FLASK ------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running!"

# Telegram webhook route
@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    asyncio.run(app_bot.update_queue.put(update))
    return "OK"

# Set webhook once at startup
async def set_webhook():
    await app_bot.bot.set_webhook(WEBHOOK_URL)

asyncio.run(set_webhook())
