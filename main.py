import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ---------------- Config ----------------
DB_PATH = "shifo_arzon_final.db"
ADMIN_IDS = [int(i.strip()) for i in os.environ.get('ADMIN_ID', '0').split(',') if i.strip()]
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")

logging.basicConfig(level=logging.INFO)

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.execute('CREATE TABLE IF NOT EXISTS regions (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS districts (id INTEGER PRIMARY KEY, name TEXT, region_id INTEGER, FOREIGN KEY(region_id) REFERENCES regions(id) ON DELETE CASCADE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS branches (id INTEGER PRIMARY KEY, name TEXT, district_id INTEGER, FOREIGN KEY(district_id) REFERENCES districts(id) ON DELETE CASCADE)')
    # Jobs are now directly linked to branches
    cursor.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT, branch_id INTEGER, FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE)')
    conn.commit()
    conn.close()

def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def db_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall()
    conn.close()
    return res

# ---------------- States ----------------
(MENU, ADMIN_NAV, ADMIN_INPUT, ADMIN_DELETE) = range(4)

# ---------------- Keyboards ----------------
def main_kb(user_id):
    kb = [["📋 Available Jobs"]]
    if user_id in ADMIN_IDS: kb.append(["🛠 Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def nav_kb(items, level_name):
    kb = [[item[1]] for item in items]
    kb.append([f"➕ Add {level_name}", f"❌ Delete {level_name}"])
    kb.append(["⬅️ Back", "🏠 Menu"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------------- Navigation Logic ----------------

async def show_regions(update, context):
    context.user_data['level'] = 'region'
    items = db_query("SELECT id, name FROM regions")
    await update.message.reply_text("📍 **Regions (Viloyatlar)**", reply_markup=nav_kb(items, "Region"), parse_mode='Markdown')
    return ADMIN_NAV

async def show_districts(update, context):
    context.user_data['level'] = 'district'
    items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (context.user_data['region_id'],))
    await update.message.reply_text(f"🏙 **Districts in {context.user_data['region_name']}**", reply_markup=nav_kb(items, "District"), parse_mode='Markdown')
    return ADMIN_NAV

async def show_branches(update, context):
    context.user_data['level'] = 'branch'
    items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (context.user_data['district_id'],))
    await update.message.reply_text(f"🏪 **Branches in {context.user_data['district_name']}**", reply_markup=nav_kb(items, "Branch"), parse_mode='Markdown')
    return ADMIN_NAV

async def show_jobs(update, context):
    context.user_data['level'] = 'job'
    items = db_query("SELECT id, title FROM jobs WHERE branch_id = ?", (context.user_data['branch_id'],))
    await update.message.reply_text(f"💼 **Jobs in {context.user_data['branch_name']}**", reply_markup=nav_kb(items, "Job"), parse_mode='Markdown')
    return ADMIN_NAV

# ---------------- Handlers ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome!", reply_markup=main_kb(update.effective_user.id))
    return MENU

async def admin_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get('level')

    if text == "🏠 Menu": return await start(update, context)
    if text == "⬅️ Back":
        if level == 'region': return await start(update, context)
        if level == 'district': return await show_regions(update, context)
        if level == 'branch': return await show_districts(update, context)
        if level == 'job': return await show_branches(update, context)

    if "➕ Add" in text:
        await update.message.reply_text(f"Enter name for the new {level}:", reply_markup=ReplyKeyboardRemove())
        return ADMIN_INPUT

    if "❌ Delete" in text:
        table = {"region":"regions", "district":"districts", "branch":"branches", "job":"jobs"}[level]
        # Query items based on current context
        if level == 'region': items = db_query("SELECT id, name FROM regions")
        elif level == 'district': items = db_query("SELECT id, name FROM districts WHERE region_id=?", (context.user_data['region_id'],))
        elif level == 'branch': items = db_query("SELECT id, name FROM branches WHERE district_id=?", (context.user_data['district_id'],))
        else: items = db_query("SELECT id, title FROM jobs WHERE branch_id=?", (context.user_data['branch_id'],))
        
        kb = [[f"🗑 {i[1]}"] for i in items] + [["⬅️ Back"]]
        await update.message.reply_text(f"Select {level} to delete:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ADMIN_DELETE

    # Drill Down
    if level == 'region':
        res = db_query("SELECT id FROM regions WHERE name=?", (text,))
        if res:
            context.user_data.update({'region_id': res[0][0], 'region_name': text})
            return await show_districts(update, context)
    elif level == 'district':
        res = db_query("SELECT id FROM districts WHERE name=?", (text,))
        if res:
            context.user_data.update({'district_id': res[0][0], 'district_name': text})
            return await show_branches(update, context)
    elif level == 'branch':
        res = db_query("SELECT id FROM branches WHERE name=?", (text,))
        if res:
            context.user_data.update({'branch_id': res[0][0], 'branch_name': text})
            return await show_jobs(update, context)
            
    return ADMIN_NAV

async def admin_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    level = context.user_data['level']
    
    if level == 'region': db_execute("INSERT INTO regions (name) VALUES (?)", (name,))
    elif level == 'district': db_execute("INSERT INTO districts (name, region_id) VALUES (?, ?)", (name, context.user_data['region_id']))
    elif level == 'branch': db_execute("INSERT INTO branches (name, district_id) VALUES (?, ?)", (name, context.user_data['district_id']))
    elif level == 'job': db_execute("INSERT INTO jobs (title, branch_id) VALUES (?, ?)", (name, context.user_data['branch_id']))
    
    await update.message.reply_text(f"✅ Added {name}")
    # REDRAW KEYBOARD
    if level == 'region': return await show_regions(update, context)
    if level == 'district': return await show_districts(update, context)
    if level == 'branch': return await show_branches(update, context)
    if level == 'job': return await show_jobs(update, context)

async def admin_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ Back": return await admin_nav_handler(update, context)
    
    name = text.replace("🗑 ", "")
    level = context.user_data['level']
    table = {"region":"regions", "district":"districts", "branch":"branches", "job":"jobs"}[level]
    col = "title" if level == "job" else "name"
    
    db_execute(f"DELETE FROM {table} WHERE {col} = ?", (name,))
    await update.message.reply_text(f"❌ Deleted {name}")
    
    if level == 'region': return await show_regions(update, context)
    if level == 'district': return await show_districts(update, context)
    if level == 'branch': return await show_branches(update, context)
    return await show_jobs(update, context)

# ---------------- Main ----------------
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex("^🛠 Admin Panel$"), show_regions)],
        states={
            MENU: [MessageHandler(filters.TEXT, admin_nav_handler)],
            ADMIN_NAV: [MessageHandler(filters.TEXT, admin_nav_handler)],
            ADMIN_INPUT: [MessageHandler(filters.TEXT, admin_input_handler)],
            ADMIN_DELETE: [MessageHandler(filters.TEXT, admin_delete_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    ))
    app.run_polling()

if __name__ == "__main__": main()
