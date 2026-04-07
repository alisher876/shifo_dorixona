import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ---------------- Configuration ----------------
DB_PATH = "shifo_arzon_v5.db"
# Set your Admin ID here or via Environment Variable
ADMIN_IDS = [int(i.strip()) for i in os.environ.get('ADMIN_ID', '0').split(',') if i.strip()]
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- Database Engine ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.execute('CREATE TABLE IF NOT EXISTS regions (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS districts (id INTEGER PRIMARY KEY, name TEXT, region_id INTEGER, FOREIGN KEY(region_id) REFERENCES regions(id) ON DELETE CASCADE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS branches (id INTEGER PRIMARY KEY, name TEXT, district_id INTEGER, FOREIGN KEY(district_id) REFERENCES districts(id) ON DELETE CASCADE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT UNIQUE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS branch_jobs (branch_id INTEGER, job_id INTEGER, FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE, FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)')
    conn.commit()
    conn.close()

def db_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.close()
    return result

def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# ---------------- States ----------------
(MENU, SELECT_JOB, SELECT_REGION, SELECT_DISTRICT, SELECT_BRANCH, NAME, PHONE,
 ADMIN_NAV, ADMIN_INPUT, ADMIN_DELETE_CONFIRM) = range(10)

# ---------------- Keyboards ----------------
def main_menu_kb(user_id):
    kb = [["📋 Available Jobs"], ["🏢 About Company"]]
    if user_id in ADMIN_IDS: kb.append(["🛠 Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def navigation_kb(items, level_name):
    kb = [[item[1]] for item in items]
    kb.append([f"➕ Add {level_name}", f"❌ Delete {level_name}"])
    kb.append(["⬅️ Back", "🏠 Main Menu"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------------- Admin Navigation Logic ----------------

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for Admin Panel - Shows Viloyatlar"""
    return await show_regions(update, context)

async def show_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['level'] = 'region'
    # Fetch all regions to show as buttons
    items = db_query("SELECT id, name FROM regions")
    await update.message.reply_text(
        "📍 **Admin: Viloyatlar ro'yxati**\n\nViloyatni tanlang yoki yangi qo'shing:",
        reply_markup=nav_kb(items, "Viloyat"),
        parse_mode='Markdown'
    )
    return ADMIN_NAV

async def show_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['level'] = 'district'
    region_id = context.user_data['region_id']
    region_name = context.user_data['region_name']
    items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (region_id,))
    await update.message.reply_text(
        f"🏙 **{region_name} tumanlari**\n\nTumanni tanlang yoki yangi qo'shing:",
        reply_markup=nav_kb(items, "Tuman"),
        parse_mode='Markdown'
    )
    return ADMIN_NAV

async def show_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['level'] = 'branch'
    district_id = context.user_data['district_id']
    district_name = context.user_data['district_name']
    items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (district_id,))
    await update.message.reply_text(
        f"🏪 **{district_name} filiallari**\n\nFilialni tanlang yoki yangi qo'shing:",
        reply_markup=nav_kb(items, "Filial"),
        parse_mode='Markdown'
    )
    return ADMIN_NAV
# ---------------- Interaction Handlers ----------------

async def admin_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Use 'level' consistently everywhere
    level = context.user_data.get('level') 

    if text == "🏠 Menu":
        await update.message.reply_text("Asosiy menyuga qaytildi.", reply_markup=main_kb(update.effective_user.id))
        return MENU
    
    if text == "⬅️ Back":
        if level == 'region': 
            await update.message.reply_text("Bekor qilindi.", reply_markup=main_kb(update.effective_user.id))
            return MENU
        if level == 'district': return await show_regions(update, context)
        if level == 'branch': return await show_districts(update, context)

    if "➕ Add" in text:
        await update.message.reply_text(
            f"✍️ Yangi {level} nomini kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADMIN_INPUT

    if "❌ Delete" in text:
        # Pass level to the delete option function
        return await show_delete_options(update, context)

    # Drilling down logic
    if level == 'region':
        res = db_query("SELECT id FROM regions WHERE name = ?", (text,))
        if res:
            context.user_data.update({'region_id': res[0][0], 'region_name': text})
            return await show_districts(update, context)
    elif level == 'district':
        res = db_query("SELECT id FROM districts WHERE name = ?", (text,))
        if res:
            context.user_data.update({'district_id': res[0][0], 'district_name': text})
            return await show_branches(update, context)
            
    return ADMIN_NAV

async def admin_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    level = context.user_data.get('level')

    try:
        if level == 'region':
            db_execute("INSERT INTO regions (name) VALUES (?)", (name,))
        elif level == 'district':
            db_execute("INSERT INTO districts (name, region_id) VALUES (?, ?)", 
                       (name, context.user_data['region_id']))
        elif level == 'branch':
            db_execute("INSERT INTO branches (name, district_id) VALUES (?, ?)", 
                       (name, context.user_data['district_id']))

        await update.message.reply_text(f"✅ {name} muvaffaqiyatli qo'shildi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

    # Return to the correct navigation level
    if level == 'region': return await show_regions(update, context)
    if level == 'district': return await show_districts(update, context)
    if level == 'branch': return await show_branches(update, context)
    return ADMIN_NAV

async def admin_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get('level') # Use 'level', not 'admin_level'

    if text == "⬅️ Back":
        if level == 'region': return await show_regions(update, context)
        if level == 'district': return await show_districts(update, context)
        return await show_branches(update, context)

    item_name = text.replace("🗑 ", "")
    table = "regions" if level == 'region' else "districts" if level == 'district' else "branches"
    
    try:
        db_execute(f"DELETE FROM {table} WHERE name = ?", (item_name,))
        await update.message.reply_text(f"❌ O'chirildi: {item_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ O'chirishda xatolik: {e}")

    # Refresh the UI
    if level == 'region': return await show_regions(update, context)
    if level == 'district': return await show_districts(update, context)
    return await show_branches(update, context)
# ---------------- Main Flow ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await admin_nav_regions(update, context) if update.effective_user.id in ADMIN_IDS else MENU

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex("^🛠 Admin Panel$"), admin_nav_regions)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_nav_handler)], # Simple redirect
            ADMIN_NAV: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_nav_handler)],
            ADMIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_input_handler)],
            ADMIN_DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
