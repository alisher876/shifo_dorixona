import os
import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
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
    APPLY_NAME,
    APPLY_BIRTHDAY,
    APPLY_ADDRESS,
    APPLY_EDUCATION,
    APPLY_EXPERIENCE,
    APPLY_LAST_JOB,
    APPLY_SALARY,
    APPLY_SKILL,
    APPLY_PHONE,
) = range(14)

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
    buttons = [["ℹ️ Kompaniya haqida", "📝 Ariza qoldirish"], ["🔥 Qaynoq ish o'rinlari", "💼 Bo'sh ish o'rinlari"]]
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

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True)

def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Raqamni yuborish", request_contact=True)], ["❌ Bekor qilish"]],
        resize_keyboard=True
    )

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


# ──────────────────── User navigation logic (Inverted Flow) ────────────────────
async def user_show_vacancies_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "vacancy_title"
    items = db_query("SELECT DISTINCT title, title FROM vacancies")
    
    if not items:
        await update.message.reply_text(
            "😔 Hozircha bo'sh ish o'rinlari yo'q.",
            reply_markup=main_menu_kb(update.effective_user.id)
        )
        return MENU
        
    await update.message.reply_text(
        "💼 Qaysi vakansiya bo'yicha ariza qoldirmoqchisiz?",
        reply_markup=user_nav_kb(items),
    )
    return USER_NAV

async def user_show_filtered_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "vacancy_region"
    title = context.user_data.get("sel_vacancy_title")
    items = db_query("""
        SELECT DISTINCT r.id, r.name 
        FROM regions r
        JOIN districts d ON r.id = d.region_id
        JOIN branches b ON d.id = b.district_id
        JOIN vacancies v ON b.id = v.branch_id
        WHERE v.title = ? COLLATE NOCASE
    """, (title,))
    await update.message.reply_text(
        "📍 Qaysi viloyatda ishlashni xohlaysiz?",
        reply_markup=user_nav_kb(items),
    )
    return USER_NAV

async def user_show_filtered_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "vacancy_district"
    title = context.user_data.get("sel_vacancy_title")
    region_id = context.user_data.get("sel_region_id")
    items = db_query("""
        SELECT DISTINCT d.id, d.name 
        FROM districts d
        JOIN branches b ON d.id = b.district_id
        JOIN vacancies v ON b.id = v.branch_id
        WHERE v.title = ? COLLATE NOCASE AND d.region_id = ?
    """, (title, region_id))
    await update.message.reply_text(
        "🏙 Qaysi tumanda ishlashni xohlaysiz?",
        reply_markup=user_nav_kb(items),
    )
    return USER_NAV

async def user_show_filtered_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_level"] = "vacancy_branch"
    title = context.user_data.get("sel_vacancy_title")
    district_id = context.user_data.get("sel_district_id")
    items = db_query("""
        SELECT DISTINCT b.id, b.name 
        FROM branches b
        JOIN vacancies v ON b.id = v.branch_id
        WHERE v.title = ? COLLATE NOCASE AND b.district_id = ?
    """, (title, district_id))
    await update.message.reply_text(
        "🏪 Qaysi filialda ishlashni xohlaysiz?",
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
            "Ma'lumot uchun raqam: +998 91-803-03-03",
            parse_mode="Markdown"
        )
        return MENU

    if text == "💼 Bo'sh ish o'rinlari":
        vacancies = db_query("""
            SELECT v.title, b.name, d.name, r.name 
            FROM vacancies v 
            JOIN branches b ON v.branch_id = b.id 
            JOIN districts d ON b.district_id = d.id 
            JOIN regions r ON d.region_id = r.id
            ORDER BY v.title, r.name, d.name, b.name
        """)
        if not vacancies:
            await update.message.reply_text("😔 Hozircha bo'sh ish o'rinlari yo'q.", reply_markup=main_menu_kb(user_id))
        else:
            lines = [f"🔹 {v[0]} — {v[1]} / {v[2]} / {v[3]}" for v in vacancies]
            msg = "📋 Barcha ochiq vakansiyalar:\n\n" + "\n".join(lines)
            if len(msg) > 4000:
                msg = msg[:4000] + "\n... (va boshqalar)"
            await update.message.reply_text(msg, reply_markup=main_menu_kb(user_id))
        return MENU
        
    if text == "🔥 Qaynoq ish o'rinlari":
        context.user_data["is_general_apply"] = False
        return await user_show_vacancies_first(update, context)

    if text == "📝 Ariza qoldirish":
        context.user_data["is_general_apply"] = True
        await update.message.reply_text(
            "📝 Iltimos, so'rovnomani to'ldiring.\n\n"
            "👤 Ism va familiyangizni kiriting:",
            reply_markup=cancel_kb(),
            parse_mode="Markdown"
        )
        return APPLY_NAME

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
        if user_level == "vacancy_title":
            await update.message.reply_text("Menyuga qaytildi.", reply_markup=main_menu_kb(user_id))
            return MENU
        if user_level == "vacancy_region":
            return await user_show_vacancies_first(update, context)
        if user_level == "vacancy_district":
            return await user_show_filtered_regions(update, context)
        if user_level == "vacancy_branch":
            return await user_show_filtered_districts(update, context)

    # Drill-down
    if user_level == "vacancy_title":
        res = db_query("SELECT id FROM vacancies WHERE title = ? COLLATE NOCASE LIMIT 1", (text,))
        if res:
            context.user_data.update({"sel_vacancy_title": text})
            return await user_show_filtered_regions(update, context)
        await update.message.reply_text("⚠️ Noto'g'ri tanlov. Iltimos, menyudan tanlang.")
        
    elif user_level == "vacancy_region":
        res = db_query("SELECT id FROM regions WHERE name = ? COLLATE NOCASE", (text,))
        if res:
            context.user_data.update({"sel_region_id": res[0][0], "sel_region_name": text})
            return await user_show_filtered_districts(update, context)
        await update.message.reply_text("⚠️ Noto'g'ri tanlov. Iltimos, menyudan tanlang.")

    elif user_level == "vacancy_district":
        res = db_query("SELECT id FROM districts WHERE name = ? COLLATE NOCASE AND region_id = ?", (text, context.user_data.get("sel_region_id")))
        if res:
            context.user_data.update({"sel_district_id": res[0][0], "sel_district_name": text})
            return await user_show_filtered_branches(update, context)
        await update.message.reply_text("⚠️ Noto'g'ri tanlov. Iltimos, menyudan tanlang.")

    elif user_level == "vacancy_branch":
        res = db_query("SELECT id FROM branches WHERE name = ? COLLATE NOCASE AND district_id = ?", (text, context.user_data.get("sel_district_id")))
        if res:
            context.user_data.update({"sel_branch_id": res[0][0], "sel_branch_name": text})
            context.user_data["is_general_apply"] = False
            
            await update.message.reply_text(
                f"Siz *{context.user_data['sel_branch_name']}* filialidagi *{context.user_data['sel_vacancy_title']}* vakansiyasini tanladingiz.\n\n"
                "📝 Iltimos, so'rovnomani to'ldiring.\n\n"
                "👤 Ism va familiyangizni kiriting:",
                reply_markup=cancel_kb(),
                parse_mode="Markdown"
            )
            return APPLY_NAME
        await update.message.reply_text("⚠️ Noto'g'ri tanlov.")

    return USER_NAV

# ──────────────────── Questionnaire Handlers ───────────────────
def check_cancel(text, user_id):
    if text == "❌ Bekor qilish":
        return True
    return False

async def apply_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_name"] = text
    await update.message.reply_text("🗓️ Tug‘ilgan sanangiz (kun/oy/yil):", reply_markup=cancel_kb())
    return APPLY_BIRTHDAY

async def apply_birthday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_birthday"] = text
    
    if context.user_data.get("is_general_apply"):
        await update.message.reply_text("📍 Qayerda va qaysi lavozimda ishlashni xohlaysiz?", reply_markup=cancel_kb())
    else:
        await update.message.reply_text("📍 Yashash manzilingiz?", reply_markup=cancel_kb())
        
    return APPLY_ADDRESS

async def apply_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_address"] = text
    await update.message.reply_text("🎓 Ta’lim darajangiz?", reply_markup=cancel_kb())
    return APPLY_EDUCATION

async def apply_education_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_education"] = text
    await update.message.reply_text("⏳ Ish tajribangiz qancha?(bo'lmasa \"Yo'q\" deb javob bering)", reply_markup=cancel_kb())
    return APPLY_EXPERIENCE

async def apply_experience_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_experience"] = text
    await update.message.reply_text("💼 Oxirgi ish joyingiz va lavozimingiz?(bo'lmasa \"Yo'q\" deb javob bering)", reply_markup=cancel_kb())
    return APPLY_LAST_JOB

async def apply_last_job_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_last_job"] = text
    await update.message.reply_text("💸 Kutilayotgan maosh?", reply_markup=cancel_kb())
    return APPLY_SALARY

async def apply_salary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_salary"] = text
    await update.message.reply_text("💻 Kompyuter bilimi (1-4 gacha baholang):", reply_markup=cancel_kb())
    return APPLY_SKILL

async def apply_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_skill"] = text
    await update.message.reply_text("☎️ Telefon raqamingiz:", reply_markup=phone_kb())
    return APPLY_PHONE

async def apply_phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if they texted Cancel
    if text and check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU

    # Extract phone from contact or text
    phone = ""
    if update.message.contact:
        phone = update.message.contact.phone_number
    elif text:
        phone = text
        
    if not phone:
        await update.message.reply_text("Iltimos, telefon raqamingizni yuboring:", reply_markup=phone_kb())
        return APPLY_PHONE
        
    context.user_data["app_phone"] = phone
    
    # Compile and send
    is_general = context.user_data.get("is_general_apply")
    uname = update.effective_user.username or "Noma'lum"

    if is_general:
        admin_msg = (
            f"📩 *YANGI UMUMIY ARIZA*\n\n"
            f"👥 *Nomzod Ma'lumotlari:*\n"
            f"👤 Ism: {context.user_data.get('app_name')}\n"
            f"🗓️ Tu'gilgan sana: {context.user_data.get('app_birthday')}\n"
            f"📍 Ishlashni xohlagan joyi: {context.user_data.get('app_address')}\n"
            f"🎓 Ta'lim: {context.user_data.get('app_education')}\n"
            f"⏳ Tajriba: {context.user_data.get('app_experience')}\n"
            f"💼 Oxirgi ish joyi: {context.user_data.get('app_last_job')}\n"
            f"💸 Maosh: {context.user_data.get('app_salary')}\n"
            f"💻 Kompyuter bilimi: {context.user_data.get('app_skill')}\n"
            f"☎️ Telefon: {context.user_data.get('app_phone')}\n\n"
            f"Username: @{uname}"
        )
    else:
        vacancy = context.user_data.get("sel_vacancy_title", "Noma'lum")
        branch = context.user_data.get("sel_branch_name", "Noma'lum")
        district = context.user_data.get("sel_district_name", "Noma'lum")
        region = context.user_data.get("sel_region_name", "Noma'lum")
        admin_msg = (
            f"🔥 *QAYNOQ VAKANSIYAGA ARIZA*\n\n"
            f"📍 Viloyat: {region}\n"
            f"🏙 Tuman: {district}\n"
            f"🏪 Filial: {branch}\n"
            f"💼 Vakansiya: {vacancy}\n\n"
            f"👥 *Nomzod Ma'lumotlari:*\n"
            f"👤 Ism: {context.user_data.get('app_name')}\n"
            f"🗓️ Tu'gilgan sana: {context.user_data.get('app_birthday')}\n"
            f"📍 Manzil: {context.user_data.get('app_address')}\n"
            f"🎓 Ta'lim: {context.user_data.get('app_education')}\n"
            f"⏳ Tajriba: {context.user_data.get('app_experience')}\n"
            f"💼 Oxirgi ish joyi: {context.user_data.get('app_last_job')}\n"
            f"💸 Maosh: {context.user_data.get('app_salary')}\n"
            f"💻 Kompyuter bilimi: {context.user_data.get('app_skill')}\n"
            f"☎️ Telefon: {context.user_data.get('app_phone')}\n\n"
            f"Username: @{uname}"
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


# ──────────────────── Admin logic ────────────────────
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
        res = db_query("SELECT id FROM districts WHERE name = ? COLLATE NOCASE AND region_id = ?", (text, context.user_data.get("region_id")))
        if res:
            context.user_data.update({"district_id": res[0][0], "district_name": text})
            return await show_branches(update, context)
        await update.message.reply_text(f"❌ '{text}' topilmadi.\nYangi qo'shish uchun '➕ Add' bosing.")
        return await show_districts(update, context)
    elif level == "branch":
        res = db_query("SELECT id FROM branches WHERE name = ? COLLATE NOCASE AND district_id = ?", (text, context.user_data.get("district_id")))
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
            APPLY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_name_handler)],
            APPLY_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_birthday_handler)],
            APPLY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_address_handler)],
            APPLY_EDUCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_education_handler)],
            APPLY_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_experience_handler)],
            APPLY_LAST_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_last_job_handler)],
            APPLY_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_salary_handler)],
            APPLY_SKILL: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_skill_handler)],
            APPLY_PHONE: [MessageHandler(filters.ALL & ~filters.COMMAND, apply_phone_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    logger.info("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
