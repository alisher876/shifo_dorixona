import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ---------------- Configuration ----------------
# If your volume mount path is /data, use: /data/bot_data.db
DB_PATH = "/data/bot_data.db" 
ADMIN_IDS = [int(i.strip()) for i in os.environ.get('ADMIN_ID', '').split(',') if i.strip()]
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- Database Logic ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT)''')
    conn.commit()
    conn.close()

def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM jobs")
    jobs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jobs

def add_job_db(title):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (title) VALUES (?)", (title,))
    conn.commit()
    conn.close()

def remove_job_db(index):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM jobs LIMIT 1 OFFSET ?", (index,))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM jobs WHERE id = ?", (row[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ---------------- States ----------------
(MENU, VACANCY, NAME, BIRTHDAY, ADDRESS, CITY, EDUCATION, 
 EXPERIENCE, LAST_JOB, MARITAL, SALARY, COMPUTER, PHONE, ADD_JOB, REMOVE_JOB) = range(15)

# ---------------- Keyboards ----------------
def main_menu_keyboard():
    keyboard = [
        ["📝 Ishga ariza topshirish"],
        ["🏢 Kompaniya haqida", "📋 Bo'sh ish o'rinlari"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- Handlers ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Shifo Arzon xizmatiga xush kelibsiz!\nQuyidagi menyudan foydalaning:",
        reply_markup=main_menu_keyboard()
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🏢 Kompaniya haqida":
        await update.message.reply_text(
            "💊 *SHIFO ARZON* — aholiga sifatli va arzon dori vositalarini yetkazuvchi dorixonalar tarmog'i.\n"
            "📍 Manzil: Navoiy shahar, Guliston-3, 49a uy.",
            parse_mode='Markdown'
        )
        return MENU

    elif text == "📋 Bo'sh ish o'rinlari":
        jobs = get_jobs()
        if not jobs:
            msg = "Hozircha bo'sh ish o'rinlari mavjud emas."
        else:
            msg = "🌟 *Bo'sh ish o'rinlari:*\n\n" + "\n".join([f"• {j}" for j in jobs])
        await update.message.reply_text(msg, parse_mode='Markdown')
        return MENU

    elif text == "📝 Ishga ariza topshirish":
        await update.message.reply_text("✨ Qaysi vakansiya (lavozim) bo'yicha ishlamoqchisiz?", reply_markup=ReplyKeyboardRemove())
        return VACANCY

# ---------------- Recruitment Flow ----------------

async def get_vacancy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['vacancy'] = update.message.text
    await update.message.reply_text("👤 Ismingizni kiriting:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("🗓️ Tug‘ilgan sanangiz (kun/oy/yil):")
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['birthday'] = update.message.text
    await update.message.reply_text("📍 Yashash manzilingiz?")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("🏥 Qaysi hududda ishlashni xohlaysiz?")
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("🎓 Ta’lim darajangiz?")
    return EDUCATION

async def get_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['education'] = update.message.text
    await update.message.reply_text("⏳ Ish tajribangiz qancha?")
    return EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['experience'] = update.message.text
    await update.message.reply_text("💼 Oxirgi ish joyingiz?")
    return LAST_JOB

async def get_last_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_job'] = update.message.text
    await update.message.reply_text("💍 Oilaviy holatingiz?")
    return MARITAL

async def get_marital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['marital'] = update.message.text
    await update.message.reply_text("💸 Kutilayotgan maosh?")
    return SALARY

async def get_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['salary'] = update.message.text
    await update.message.reply_text("💻 Kompyuter bilimi (1-4 gacha baholang):")
    return COMPUTER

async def get_computer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['computer'] = update.message.text
    await update.message.reply_text("☎️ Telefon raqamingiz:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    d = context.user_data
    summary = (
        f"📋 *YANGI ARIZA*\n\n👤 Ism: {d['name']}\n✨ Lavozim: {d['vacancy']}\n🗓️ Sana: {d['birthday']}\n"
        f"📍 Manzil: {d['address']}\n🏥 Hudud: {d['city']}\n🎓 Ta'lim: {d['education']}\n⏳ Tajriba: {d['experience']}\n"
        f"💼 Ish: {d['last_job']}\n💍 Holat: {d['marital']}\n💸 Maosh: {d['salary']}\n💻 Komp: {d['computer']}\n☎️ Tel: {d['phone']}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=summary, parse_mode='Markdown')
        except: pass

    await update.message.reply_text("✅ Arizangiz yuborildi!", reply_markup=main_menu_keyboard())
    context.user_data.clear()
    return MENU

# ---------------- Admin Management ----------------

async def add_job_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return MENU
    await update.message.reply_text("Yangi vakansiya nomini yozing:", reply_markup=ReplyKeyboardRemove())
    return ADD_JOB

async def add_job_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_job_db(update.message.text)
    await update.message.reply_text("✅ Qo'shildi!", reply_markup=main_menu_keyboard())
    return MENU

async def remove_job_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return MENU
    jobs = get_jobs()
    if not jobs:
        await update.message.reply_text("Ro'yxat bo'sh.")
        return MENU
    msg = "\n".join([f"{i+1}. {j}" for i, j in enumerate(jobs)])
    await update.message.reply_text(f"O'chirish uchun raqamni yozing:\n\n{msg}", reply_markup=ReplyKeyboardRemove())
    return REMOVE_JOB

async def remove_job_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text) - 1
        if remove_job_db(idx):
            await update.message.reply_text("❌ O'chirildi.", reply_markup=main_menu_keyboard())
        else:
            await update.message.reply_text("Xato raqam.", reply_markup=main_menu_keyboard())
    except:
        await update.message.reply_text("Faqat raqam yozing.", reply_markup=main_menu_keyboard())
    return MENU

# ---------------- Main ----------------

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            VACANCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vacancy)],
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
            ADD_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_job_finish)],
            REMOVE_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_job_finish)],
        },
        fallbacks=[
            CommandHandler("addjob", add_job_start),
            CommandHandler("removejob", remove_job_start),
            CommandHandler("cancel", start)
        ],
    )

    app.add_handler(conv)
    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN, webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    main()
