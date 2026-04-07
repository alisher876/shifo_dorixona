import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ---------------- Configuration ----------------
DB_PATH = "shifo_arzon_v3.db"
# Example ADMIN_ID env: "1234567,8901234"
ADMIN_IDS = [int(i.strip()) for i in os.environ.get('ADMIN_ID', '0').split(',') if i.strip()]
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- Database Engine ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Core Tables
    cursor.execute('CREATE TABLE IF NOT EXISTS regions (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS districts (id INTEGER PRIMARY KEY, name TEXT, region_id INTEGER, FOREIGN KEY(region_id) REFERENCES regions(id) ON DELETE CASCADE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS branches (id INTEGER PRIMARY KEY, name TEXT, district_id INTEGER, FOREIGN KEY(district_id) REFERENCES districts(id) ON DELETE CASCADE)')
    cursor.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT UNIQUE)')
    
    # Mapping Table: Defines which branch has which vacancy
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
 ADMIN_MENU, ADMIN_ADD_TYPE, ADMIN_SELECT_PARENT, ADMIN_INPUT_NAME, ADMIN_LINK_JOB) = range(12)

# ---------------- Keyboards ----------------
def main_menu_kb(user_id):
    kb = [["📋 Available Jobs"], ["🏢 About Company"]]
    if user_id in ADMIN_IDS:
        kb.append(["🛠 Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu_kb():
    kb = [["➕ Add Data", "🔗 Link Job to Branch"], ["⬅️ Back to Main Menu"]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------------- User Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "👋 Welcome to Shifo Arzon Career Bot!",
        reply_markup=main_menu_kb(user_id)
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🏢 About Company":
        await update.message.reply_text("Shifo Arzon is a leading pharmacy network providing affordable medicine.")
        return MENU
    
    elif text == "📋 Available Jobs":
        jobs = db_query("SELECT title FROM jobs")
        if not jobs:
            await update.message.reply_text("No active vacancies at the moment.")
            return MENU
        buttons = [[j[0]] for j in jobs]
        await update.message.reply_text("Select a position:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return SELECT_JOB

    elif text == "🛠 Admin Panel" and update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text("Admin Mode Active.", reply_markup=admin_menu_kb())
        return ADMIN_MENU

async def job_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_title = update.message.text
    context.user_data['job'] = job_title
    
    # Filter regions that have this specific job in their branches
    query = """
        SELECT DISTINCT r.name FROM regions r
        JOIN districts d ON r.id = d.region_id
        JOIN branches b ON d.id = b.district_id
        JOIN branch_jobs bj ON b.id = bj.branch_id
        JOIN jobs j ON bj.job_id = j.id
        WHERE j.title = ?
    """
    regions = db_query(query, (job_title,))
    if not regions:
        await update.message.reply_text("No branches currently have this vacancy.")
        return MENU

    buttons = [[r[0]] for r in regions]
    await update.message.reply_text("Select Region:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return SELECT_REGION

async def region_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    region_name = update.message.text
    query = """
        SELECT DISTINCT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        JOIN branches b ON d.id = b.district_id
        JOIN branch_jobs bj ON b.id = bj.branch_id
        JOIN jobs j ON bj.job_id = j.id
        WHERE r.name = ? AND j.title = ?
    """
    districts = db_query(query, (region_name, context.user_data['job']))
    buttons = [[d[0]] for d in districts]
    await update.message.reply_text("Select District:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return SELECT_DISTRICT

async def district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    district_name = update.message.text
    query = """
        SELECT DISTINCT b.name FROM branches b
        JOIN districts d ON b.district_id = d.id
        JOIN branch_jobs bj ON b.id = bj.branch_id
        JOIN jobs j ON bj.job_id = j.id
        WHERE d.name = ? AND j.title = ?
    """
    branches = db_query(query, (district_name, context.user_data['job']))
    buttons = [[b[0]] for b in branches]
    await update.message.reply_text("Select Branch:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return SELECT_BRANCH

async def branch_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['branch'] = update.message.text
    await update.message.reply_text("Enter your Full Name:", reply_markup=ReplyKeyboardRemove())
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['user_name'] = update.message.text
    await update.message.reply_text("Enter your Phone Number:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    d = context.user_data
    summary = f"🆕 **New Application**\nJob: {d['job']}\nBranch: {d['branch']}\nName: {d['user_name']}\nPhone: {phone}"
    
    for admin_id in ADMIN_IDS:
        try: await context.bot.send_message(chat_id=admin_id, text=summary, parse_mode='Markdown')
        except: pass
    
    await update.message.reply_text("✅ Application sent!", reply_markup=main_menu_kb(update.effective_user.id))
    return MENU

# ---------------- Admin Handlers ----------------
async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["Region", "District"], ["Branch", "Job"], ["⬅️ Back"]]
    await update.message.reply_text("What would you like to add?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ADMIN_ADD_TYPE

async def admin_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text
    if target == "⬅️ Back": return await admin_start_redirect(update, context)
    context.user_data['admin_target'] = target.lower()
    
    if target in ["Region", "Job"]:
        await update.message.reply_text(f"Enter name for new {target}:", reply_markup=ReplyKeyboardRemove())
        return ADMIN_INPUT_NAME
    else:
        parent_table = "regions" if target == "District" else "districts"
        parents = db_query(f"SELECT name FROM {parent_table}")
        buttons = [[p[0]] for p in parents]
        await update.message.reply_text(f"Select parent {target}:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return ADMIN_SELECT_PARENT

async def admin_parent_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['parent_name'] = update.message.text
    await update.message.reply_text(f"Enter name for the new entry:", reply_markup=ReplyKeyboardRemove())
    return ADMIN_INPUT_NAME

async def admin_save_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    target = context.user_data['admin_target']
    
    if target == "region":
        db_execute("INSERT INTO regions (name) VALUES (?)", (name,))
    elif target == "job":
        db_execute("INSERT INTO jobs (title) VALUES (?)", (name,))
    elif target == "district":
        p_id = db_query("SELECT id FROM regions WHERE name = ?", (context.user_data['parent_name'],))[0][0]
        db_execute("INSERT INTO districts (name, region_id) VALUES (?, ?)", (name, p_id))
    elif target == "branch":
        p_id = db_query("SELECT id FROM districts WHERE name = ?", (context.user_data['parent_name'],))[0][0]
        db_execute("INSERT INTO branches (name, district_id) VALUES (?, ?)", (name, p_id))
        
    await update.message.reply_text(f"✅ {name} added!", reply_markup=admin_menu_kb())
    return ADMIN_MENU

async def admin_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    branches = db_query("SELECT name FROM branches")
    buttons = [[b[0]] for b in branches]
    await update.message.reply_text("Select Branch to add a job to:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return ADMIN_LINK_JOB

async def admin_link_job_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'link_branch' not in context.user_data:
        context.user_data['link_branch'] = update.message.text
        jobs = db_query("SELECT title FROM jobs")
        buttons = [[j[0]] for j in jobs]
        await update.message.reply_text("Select Job to link:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return ADMIN_LINK_JOB
    else:
        job_title = update.message.text
        branch_name = context.user_data['link_branch']
        b_id = db_query("SELECT id FROM branches WHERE name = ?", (branch_name,))[0][0]
        j_id = db_query("SELECT id FROM jobs WHERE title = ?", (job_title,))[0][0]
        db_execute("INSERT INTO branch_jobs (branch_id, job_id) VALUES (?, ?)", (b_id, j_id))
        context.user_data.pop('link_branch')
        await update.message.reply_text("✅ Job linked to branch!", reply_markup=admin_menu_kb())
        return ADMIN_MENU

async def admin_start_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admin Panel", reply_markup=admin_menu_kb())
    return ADMIN_MENU

# ---------------- Main ----------------
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                MessageHandler(filters.Regex("^🛠 Admin Panel$"), admin_start_redirect),
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
            ],
            # User states
            SELECT_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, job_selected)],
            SELECT_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, region_selected)],
            SELECT_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district_selected)],
            SELECT_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, branch_selected)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            # Admin states
            ADMIN_MENU: [
                MessageHandler(filters.Regex("^➕ Add Data$"), admin_add_start),
                MessageHandler(filters.Regex("^🔗 Link Job to Branch$"), admin_link_start),
                MessageHandler(filters.Regex("^⬅️ Back to Main Menu$"), start)
            ],
            ADMIN_ADD_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_type_selected)],
            ADMIN_SELECT_PARENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_parent_selected)],
            ADMIN_INPUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_data)],
            ADMIN_LINK_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_link_job_selected)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
