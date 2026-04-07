import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────── Config ───────────────────────────
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS_ENV = os.environ.get("ADMIN_ID", "")
ADMIN_IDS = [int(x) for x in ADMIN_IDS_ENV.split(",") if x.strip().isdigit()]

DB_PATH = "shifo.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

logger.info(f"ADMIN_IDS loaded: {ADMIN_IDS}")

# ───────────────────── Conversation states ─────────────────────
(
    MENU,
    ADMIN_NAV,
    ADMIN_INPUT,
    ADMIN_DELETE_CONFIRM,
    USER_NAV,
    USER_APPLY,
) = range(6)

# ─────────────────────── Database helpers ──────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS regions (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS districts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS branches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            district_id INTEGER REFERENCES districts(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS vacancies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            branch_id   INTEGER REFERENCES branches(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def db_query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return rows


def db_execute(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()


# ─────────────────────── Keyboard helpers ──────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_menu_kb(user_id: int) -> ReplyKeyboardMarkup:
    buttons = [["ℹ️ Kompaniya haqida", "💼 Bo'sh ish o'rinlari"]]
    if is_admin(user_id):
        buttons.append(["⚙️ Admin panel"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def navigation_kb(items, label: str) -> ReplyKeyboardMarkup:
    rows = [[item[1]] for item in items]
    rows.append([f"➕ Add {label}", f"❌ Delete {label}"])
    rows.append(["⬅️ Back", "🏠 Main Menu"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def user_nav_kb(items) -> ReplyKeyboardMarkup:
    rows = [[item[1]] for item in items]
    rows.append(["⬅️ Back", "🏠 Main Menu"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# ──────────────────── Admin navigation logic ────────────────────
async def show_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = "region"
    items = db_query("SELECT id, name FROM regions")
    await update.message.reply_text(
        "📍 Viloyatlar ro'yxati:",
        reply_markup=navigation_kb(items, "Viloyat"),
    )
    return ADMIN_NAV


async def show_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = "district"
    region_id = context.user_data.get("region_id")
    region_name = context.user_data.get("region_name", "?")
    if not region_id:
        await update.message.reply_text(
            "⚠️ Viloyat tanlanmagan. /start dan boshlang.",
            reply_markup=main_menu_kb(update.effective_user.id),
        )
        return MENU
    items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (region_id,))
    await update.message.reply_text(
        f"🏙 {region_name} tumanlari:",
        reply_markup=navigation_kb(items, "Tuman"),
    )
    return ADMIN_NAV


async def show_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = "branch"
    district_id = context.user_data.get("district_id")
    district_name = context.user_data.get("district_name", "?")
    if not district_id:
        await update.message.reply_text(
            "⚠️ Tuman tanlanmagan. /start dan boshlang.",
            reply_markup=main_menu_kb(update.effective_user.id),
        )
        return MENU
    items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (district_id,))
    await update.message.reply_text(
        f"🏪 {district_name} filiallari:",
        reply_markup=navigation_kb(items, "Filial"),
    )
    return ADMIN_NAV

async def show_admin_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = "vacancy"
    branch_id = context.user_data.get("branch_id")
    branch_name = context.user_data.get("branch_name", "?")
    if not branch_id:
        await update.message.reply_text(
            "⚠️ Filial tanlanmagan. /start dan boshlang.",
            reply_markup=main_menu_kb(update.effective_user.id),
        )
        return MENU
    items = db_query("SELECT id, title FROM vacancies WHERE branch_id = ?", (branch_id,))
    await update.message.reply_text(
        f"💼 {branch_name} bo'sh ish o'rinlari:",
        reply_markup=navigation_kb(items, "Vakansiya"),
    )
    return ADMIN_NAV


async def show_delete_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level = context.user_data.get("level")
    if level == "region":
        items = db_query("SELECT id, name FROM regions")
    elif level == "district":
        region_id = context.user_data.get("region_id")
        items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (region_id,)) if region_id else []
    elif level == "branch":
        district_id = context.user_data.get("district_id")
        items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (district_id,)) if district_id else []
    else: # vacancy
        branch_id = context.user_data.get("branch_id")
        items = db_query("SELECT id, title FROM vacancies WHERE branch_id = ?", (branch_id,)) if branch_id else []

    kb = [[f"🗑 {i[1]}"] for i in items]
    kb.append(["⬅️ Back"])
    await update.message.reply_text(
        f"O'chirish uchun {level}ni tanlang:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )
    return ADMIN_DELETE_CONFIRM


# ──────────────────── User navigation logic ────────────────────
async def user_show_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "region"
    items = db_query("SELECT id, name FROM regions")
    await update.message.reply_text(
        "📍 Viloyatni tanlang:",
        reply_markup=user_nav_kb(items),
    )
    return USER_NAV

async def user_show_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "district"
    region_id = context.user_data.get("user_region_id")
    items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (region_id,))
    await update.message.reply_text(
        "🏙 Tumanni tanlang:",
        reply_markup=user_nav_kb(items),
    )
    return USER_NAV

async def user_show_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "branch"
    district_id = context.user_data.get("user_district_id")
    items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (district_id,))
    await update.message.reply_text(
        "🏪 Filialni tanlang:",
        reply_markup=user_nav_kb(items),
    )
    return USER_NAV

async def user_show_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "vacancy"
    branch_id = context.user_data.get("user_branch_id")
    items = db_query("SELECT id, title FROM vacancies WHERE branch_id = ?", (branch_id,))
    
    if not items:
        await update.message.reply_text(
            "😔 Hozircha bu filialda bo'sh ish o'rinlari yo'q.",
            reply_markup=user_nav_kb(items)
        )
    else:
        await update.message.reply_text(
            "💼 Qiziqtirgan vakansiyani tanlang:",
            reply_markup=user_nav_kb(items),
        )
    return USER_NAV

# ───────────────────────── Handlers ────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\nShifo Do'rxona botiga xush kelibsiz.",
        reply_markup=main_menu_kb(user.id),
    )
    return MENU


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "ℹ️ Kompaniya haqida":
        await update.message.reply_text(
            "🏢 *Shifo Dorixona*\n\n"
            "Biz xalqimizga eng sifatli dori vositalarini hamyonbop narxlarda yetkazib berishni maqsad qilgan dorixonalar tizimimiz!\n\n"
            "Ma'lumot uchun raqam: +99899 123-45-67",
            parse_mode="Markdown"
        )
        return MENU

    if text == "💼 Bo'sh ish o'rinlari":
        return await user_show_regions(update, context)

    if text == "⚙️ Admin panel" and is_admin(user_id):
        return await show_regions(update, context)

    return MENU

async def user_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_level = context.user_data.get("user_level")
    user_id = update.effective_user.id

    if text == "🏠 Main Menu":
        await update.message.reply_text("Menyuga qaytildi.", reply_markup=main_menu_kb(user_id))
        return MENU

    if text == "⬅️ Back":
        if user_level == "region":
            await update.message.reply_text("Menyuga qaytildi.", reply_markup=main_menu_kb(user_id))
            return MENU
        if user_level == "district":
            return await user_show_regions(update, context)
        if user_level == "branch":
            return await user_show_districts(update, context)
        if user_level == "vacancy":
            return await user_show_branches(update, context)

    # Drill-down
    if user_level == "region":
        res = db_query("SELECT id FROM regions WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"user_region_id": res[0][0], "user_region_name": text})
            return await user_show_districts(update, context)
        await update.message.reply_text("⚠️ Noto'g'ri tanlov. Iltimos, menyudan tanlang.")
        
    elif user_level == "district":
        res = db_query("SELECT id FROM districts WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"user_district_id": res[0][0], "user_district_name": text})
            return await user_show_branches(update, context)
        await update.message.reply_text("⚠️ Noto'g'ri tanlov. Iltimos, menyudan tanlang.")

    elif user_level == "branch":
        res = db_query("SELECT id FROM branches WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"user_branch_id": res[0][0], "user_branch_name": text})
            return await user_show_vacancies(update, context)
        await update.message.reply_text("⚠️ Noto'g'ri tanlov. Iltimos, menyudan tanlang.")

    elif user_level == "vacancy":
        res = db_query("SELECT id, title FROM vacancies WHERE title = ? AND branch_id = ? COLLATE NOCASE", (text, context.user_data.get("user_branch_id")))
        if res:
            context.user_data.update({"user_vacancy_id": res[0][0], "user_vacancy_name": res[0][1]})
            
            # Start application process
            await update.message.reply_text(
                f"Siz *{context.user_data['user_branch_name']}* filialidagi *{res[0][1]}* vakansiyasini tanladingiz.\n\n"
                "📝 Iltimos, o'zingiz haqingizdagi ma'lumotlarni yuboring:\n"
                "(F.I.SH, telefon raqamingiz, tajribangiz haqida yozing va jo'nating)",
                reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True),
                parse_mode="Markdown"
            )
            return USER_APPLY
        await update.message.reply_text("⚠️ Noto'g'ri tanlov.")

    return USER_NAV

async def user_apply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ Bekor qilish":
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU

    # Send to all admins
    vacancy = context.user_data.get("user_vacancy_name", "Noma'lum")
    branch = context.user_data.get("user_branch_name", "Noma'lum")
    district = context.user_data.get("user_district_name", "Noma'lum")
    region = context.user_data.get("user_region_name", "Noma'lum")
    
    admin_msg = (
        f"📩 *YANGI ARIZA TUSHDI*\n\n"
        f"📍 Viloyat: {region}\n"
        f"🏙 Tuman: {district}\n"
        f"🏪 Filial: {branch}\n"
        f"💼 Vakansiya: {vacancy}\n\n"
        f"👤 Nomzod ma'lumoti:\n{text}\n\n"
        f"Username: @{update.effective_user.username or 'Noma\\'lum'}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send to admin {admin_id}: {e}")

    await update.message.reply_text(
        "✅ Arizangiz muvaffaqiyatli yuborildi! Tez orada siz bilan bog'lanamiz.",
        reply_markup=main_menu_kb(user_id)
    )
    return MENU


async def admin_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get("level")
    user_id = update.effective_user.id

    if text == "🏠 Main Menu":
        await update.message.reply_text("Menyuga qaytildi.", reply_markup=main_menu_kb(user_id))
        return MENU

    if text == "⬅️ Back":
        if level == "region":
            await update.message.reply_text("Bekor qilindi.", reply_markup=main_menu_kb(user_id))
            return MENU
        if level == "district":
            return await show_regions(update, context)
        if level == "branch":
            return await show_districts(update, context)
        if level == "vacancy":
            return await show_branches(update, context)

    if text.startswith("➕ Add"):
        kb = [["❌ Cancel"]]
        await update.message.reply_text(
            f"✍️ Yangi {level} nomini kiriting:",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        )
        return ADMIN_INPUT

    if text.startswith("❌ Delete"):
        return await show_delete_options(update, context)

    # Drill-down
    if level == "region":
        res = db_query("SELECT id FROM regions WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"region_id": res[0][0], "region_name": text})
            return await show_districts(update, context)
        await update.message.reply_text(f"❌ '{text}' topilmadi.\nYangi qo'shish uchun '➕ Add' bosing.")
        return await show_regions(update, context)
    elif level == "district":
        res = db_query("SELECT id FROM districts WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"district_id": res[0][0], "district_name": text})
            return await show_branches(update, context)
        await update.message.reply_text(f"❌ '{text}' topilmadi.\nYangi qo'shish uchun '➕ Add' bosing.")
        return await show_districts(update, context)
    elif level == "branch":
        res = db_query("SELECT id FROM branches WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"branch_id": res[0][0], "branch_name": text})
            return await show_admin_vacancies(update, context)
        await update.message.reply_text(f"❌ '{text}' topilmadi.\nYangi qo'shish uchun '➕ Add' bosing.")
        return await show_branches(update, context)

    return await show_regions(update, context)


async def admin_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    level = context.user_data.get("level")

    if name == "❌ Cancel":
        if level == "region": return await show_regions(update, context)
        if level == "district": return await show_districts(update, context)
        if level == "branch": return await show_branches(update, context)
        if level == "vacancy": return await show_admin_vacancies(update, context)
        await update.message.reply_text("Bekor qilindi.", reply_markup=main_menu_kb(update.effective_user.id))
        return MENU

    # Insert into DB
    inserted = False
    try:
        if level == "region":
            db_execute("INSERT INTO regions (name) VALUES (?)", (name,))
            inserted = True
        elif level == "district":
            region_id = context.user_data.get("region_id")
            if region_id:
                db_execute("INSERT INTO districts (name, region_id) VALUES (?, ?)", (name, region_id))
                inserted = True
        elif level == "branch":
            district_id = context.user_data.get("district_id")
            if district_id:
                db_execute("INSERT INTO branches (name, district_id) VALUES (?, ?)", (name, district_id))
                inserted = True
        elif level == "vacancy":
            branch_id = context.user_data.get("branch_id")
            if branch_id:
                db_execute("INSERT INTO vacancies (title, branch_id) VALUES (?, ?)", (name, branch_id))
                inserted = True
        else:
            await update.message.reply_text("⚠️ Noma'lum holat.", reply_markup=main_menu_kb(update.effective_user.id))
            return MENU
    except Exception as e:
        logger.error(f"DB insert error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Xatolik: {e}")

    if inserted:
        await update.message.reply_text(f"✅ {name} qo'shildi!")

    if level == "region": return await show_regions(update, context)
    if level == "district": return await show_districts(update, context)
    if level == "branch": return await show_branches(update, context)
    return await show_admin_vacancies(update, context)


async def admin_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get("level")

    if text == "⬅️ Back":
        if level == "region": return await show_regions(update, context)
        if level == "district": return await show_districts(update, context)
        if level == "branch": return await show_branches(update, context)
        if level == "vacancy": return await show_admin_vacancies(update, context)
        return MENU

    item_name = text[2:].strip() if text.startswith("🗑") else text
    
    try:
        if level == "region":
            db_execute("DELETE FROM regions WHERE name = ?", (item_name,))
        elif level == "district":
            db_execute("DELETE FROM districts WHERE name = ?", (item_name,))
        elif level == "branch":
            db_execute("DELETE FROM branches WHERE name = ?", (item_name,))
        else:
            db_execute("DELETE FROM vacancies WHERE title = ?", (item_name,))
        
        await update.message.reply_text(f"✅ O'chirildi: {item_name}")
    except Exception as e:
        logger.error(f"DB delete error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Xatolik: {e}")

    if level == "region": return await show_regions(update, context)
    if level == "district": return await show_districts(update, context)
    if level == "branch": return await show_branches(update, context)
    return await show_admin_vacancies(update, context)


# ──────────────────────────── Main ─────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            f"⚠️ Xatolik: {context.error}\n\n/start dan qayta boshlang."
        )


def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            ADMIN_NAV: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_nav_handler)],
            ADMIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_input_handler)],
            ADMIN_DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_handler)],
            USER_NAV: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_nav_handler)],
            USER_APPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_apply_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    logger.info("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
