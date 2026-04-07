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
MENU, ADMIN_NAV, ADMIN_INPUT, ADMIN_DELETE_CONFIRM = range(4)

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
    buttons = [["🔍 Qidiruv", "📋 Barcha filiallar"]]
    if is_admin(user_id):
        buttons.append(["⚙️ Admin panel"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def navigation_kb(items, label: str) -> ReplyKeyboardMarkup:
    rows = [[item[1]] for item in items]
    rows.append([f"➕ Add {label}", f"❌ Delete {label}"])
    rows.append(["⬅️ Back", "🏠 Main Menu"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ──────────────────── Admin navigation logic ────────────────────
async def show_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("show_regions called")
    context.user_data["level"] = "region"
    items = db_query("SELECT id, name FROM regions")
    await update.message.reply_text(
        "📍 Viloyatlar ro'yxati:",
        reply_markup=navigation_kb(items, "Viloyat"),
    )
    return ADMIN_NAV


async def show_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("show_districts called")
    context.user_data["level"] = "district"
    region_id = context.user_data.get("region_id")
    region_name = context.user_data.get("region_name", "?")
    if not region_id:
        logger.warning("show_districts: region_id missing!")
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
    logger.info("show_branches called")
    context.user_data["level"] = "branch"
    district_id = context.user_data.get("district_id")
    district_name = context.user_data.get("district_name", "?")
    if not district_id:
        logger.warning("show_branches: district_id missing!")
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


async def show_delete_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level = context.user_data.get("level")
    if level == "region":
        items = db_query("SELECT id, name FROM regions")
    elif level == "district":
        region_id = context.user_data.get("region_id")
        items = db_query(
            "SELECT id, name FROM districts WHERE region_id = ?", (region_id,)
        ) if region_id else []
    else:
        district_id = context.user_data.get("district_id")
        items = db_query(
            "SELECT id, name FROM branches WHERE district_id = ?", (district_id,)
        ) if district_id else []

    kb = [[f"🗑 {i[1]}"] for i in items]
    kb.append(["⬅️ Back"])
    await update.message.reply_text(
        f"O'chirish uchun {level}ni tanlang:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )
    return ADMIN_DELETE_CONFIRM


# ───────────────────────── Handlers ────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"start: user_id={user.id}, is_admin={is_admin(user.id)}")
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\nShifo Do'rxona botiga xush kelibsiz.",
        reply_markup=main_menu_kb(user.id),
    )
    return MENU


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    logger.info(f"menu_handler: user_id={user_id}, text={text!r}")

    if text == "🔍 Qidiruv":
        await update.message.reply_text(
            "🔍 Filial nomini kiriting:", reply_markup=ReplyKeyboardRemove()
        )
        return MENU

    if text == "📋 Barcha filiallar":
        branches = db_query(
            """SELECT b.name, d.name, r.name
               FROM branches b
               JOIN districts d ON b.district_id = d.id
               JOIN regions r ON d.region_id = r.id
               ORDER BY r.name, d.name, b.name"""
        )
        if not branches:
            await update.message.reply_text(
                "Hozircha filiallar yo'q.", reply_markup=main_menu_kb(user_id)
            )
        else:
            lines = [f"🏪 {b[0]} — {b[1]}, {b[2]}" for b in branches]
            await update.message.reply_text(
                "📋 Barcha filiallar:\n\n" + "\n".join(lines),
                reply_markup=main_menu_kb(user_id),
            )
        return MENU

    if text == "⚙️ Admin panel" and is_admin(user_id):
        return await show_regions(update, context)

    # Free-text search
    results = db_query("SELECT name FROM branches WHERE name LIKE ?", (f"%{text}%",))
    msg = ("Topildi:\n" + "\n".join(f"🏪 {r[0]}" for r in results)) if results else "❌ Hech narsa topilmadi."
    await update.message.reply_text(msg, reply_markup=main_menu_kb(user_id))
    return MENU


async def admin_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get("level")
    user_id = update.effective_user.id
    logger.info(f"admin_nav_handler: level={level!r}, text={text!r}")

    if text == "🏠 Main Menu":
        await update.message.reply_text(
            "Menyuga qaytildi.", reply_markup=main_menu_kb(user_id)
        )
        return MENU

    if text == "⬅️ Back":
        if level == "region":
            await update.message.reply_text(
                "Bekor qilindi.", reply_markup=main_menu_kb(user_id)
            )
            return MENU
        if level == "district":
            return await show_regions(update, context)
        if level == "branch":
            return await show_districts(update, context)

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
        res = db_query("SELECT id FROM regions WHERE name = ?", (text,))
        if res:
            context.user_data.update({"region_id": res[0][0], "region_name": text})
            return await show_districts(update, context)
    elif level == "district":
        res = db_query("SELECT id FROM districts WHERE name = ?", (text,))
        if res:
            context.user_data.update({"district_id": res[0][0], "district_name": text})
            return await show_branches(update, context)

    logger.info(f"admin_nav_handler: no match, staying in ADMIN_NAV")
    return ADMIN_NAV


async def admin_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    level = context.user_data.get("level")
    logger.info(f"admin_input_handler: level={level!r}, name={name!r}")

    if name == "❌ Cancel":
        if level == "region":
            return await show_regions(update, context)
        if level == "district":
            return await show_districts(update, context)
        if level == "branch":
            return await show_branches(update, context)
        await update.message.reply_text(
            "Bekor qilindi.", reply_markup=main_menu_kb(update.effective_user.id)
        )
        return MENU

    # Insert into DB
    inserted = False
    try:
        if level == "region":
            db_execute("INSERT INTO regions (name) VALUES (?)", (name,))
            inserted = True
        elif level == "district":
            region_id = context.user_data.get("region_id")
            if not region_id:
                await update.message.reply_text(
                    "⚠️ Viloyat tanlanmagan. /start dan boshlang.",
                    reply_markup=main_menu_kb(update.effective_user.id),
                )
                return MENU
            db_execute(
                "INSERT INTO districts (name, region_id) VALUES (?, ?)",
                (name, region_id),
            )
            inserted = True
        elif level == "branch":
            district_id = context.user_data.get("district_id")
            if not district_id:
                await update.message.reply_text(
                    "⚠️ Tuman tanlanmagan. /start dan boshlang.",
                    reply_markup=main_menu_kb(update.effective_user.id),
                )
                return MENU
            db_execute(
                "INSERT INTO branches (name, district_id) VALUES (?, ?)",
                (name, district_id),
            )
            inserted = True
        else:
            await update.message.reply_text(
                "⚠️ Noma'lum holat. /start dan boshlang.",
                reply_markup=main_menu_kb(update.effective_user.id),
            )
            return MENU
    except Exception as e:
        logger.error(f"DB insert error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Xatolik: {e}")

    if inserted:
        await update.message.reply_text(f"✅ {name} qo'shildi!")

    # Navigate back to the current level
    if level == "region":
        return await show_regions(update, context)
    if level == "district":
        return await show_districts(update, context)
    return await show_branches(update, context)


async def admin_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get("level")
    logger.info(f"admin_delete_handler: level={level!r}, text={text!r}")

    if text == "⬅️ Back":
        if level == "region":
            return await show_regions(update, context)
        if level == "district":
            return await show_districts(update, context)
        return await show_branches(update, context)

    item_name = text[2:].strip() if text.startswith("🗑") else text
    table = (
        "regions" if level == "region"
        else "districts" if level == "district"
        else "branches"
    )

    try:
        db_execute(f"DELETE FROM {table} WHERE name = ?", (item_name,))
        await update.message.reply_text(f"✅ O'chirildi: {item_name}")
    except Exception as e:
        logger.error(f"DB delete error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Xatolik: {e}")

    if level == "region":
        return await show_regions(update, context)
    if level == "district":
        return await show_districts(update, context)
    return await show_branches(update, context)


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
            ADMIN_DELETE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_handler)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    logger.info("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
