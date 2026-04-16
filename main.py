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
    # Admin states
    ADMIN_NAV,
    ADMIN_INPUT,
    ADMIN_DELETE_CONFIRM,
    # User states for Qaynoq
    USER_NAV,
    # New user states for Ariza
    ARIZA_DEPARTMENT,
    ARIZA_OFIS_ADDRESS,
    ARIZA_OMBOR_ADDRESS,
    ARIZA_VACANCY,
    ARIZA_DORIXONA_DISTRICT,
    ARIZA_DORIXONA_ADDRESS,
    # Questionnaire states
    APPLY_NAME,
    APPLY_BIRTHDAY,
    APPLY_ADDRESS,
    APPLY_PHONE,
    APPLY_MARITAL,
    APPLY_STUDENT,
    APPLY_STUDY_TIME,
    APPLY_EDUCATION,
    APPLY_EXPERIENCE,
    APPLY_LANG_UZ,
    APPLY_LANG_RU,
    APPLY_LANG_EN,
    APPLY_SALARY,
) = range(24)

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
    buttons = [["ℹ️ Kompaniya haqida", "💼 Bo'sh ish o'rinlari"], ["🔥 Qaynoq ish o'rinlari"]]
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

def ariza_departments_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Ofis", "Dorixona", "Omborxona"], ["❌ Bekor qilish"]], resize_keyboard=True)

def ariza_ofis_address_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Guliston 3 massivi 49A-uy(Guliston 3 poliknikasi)"], ["❌ Bekor qilish"]], resize_keyboard=True)

def ariza_ofis_vacancies_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Zam Direktor", "Buxgalter"], ["Zavxoz(programist)", "Menedjer"], ["Bron", "Shafyor", "HR"], ["❌ Bekor qilish"]], resize_keyboard=True)

def ariza_dorixona_vacancies_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Farmasevt", "Parafarmasevt"], ["❌ Bekor qilish"]], resize_keyboard=True)

def dorixona_districts_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["Navoiy shahar", "Nurota tuman"], 
        ["Karmana tuman", "Muborak Tuman"], 
        ["Gijduvon tuman", "Paxtachi tuman"], 
        ["Narpay tuman", "Xatirchi tuman"],
        ["❌ Bekor qilish"]
    ], resize_keyboard=True)

def dorixona_navoiy_addresses_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["Abdullo Avloniy 16A-uy", "10 daha Tijorat bozori 85-do'kon"],
        ["Abdulla Avloniy ko’chasi 17-2.2-uy", "Ibn Sino ko’chasi 24-uy"],
        ["Guliston 454/1-uy", "G’alaba ko’chasi 188G-uy"],
        ["❌ Bekor qilish"]
    ], resize_keyboard=True)

def dorixona_single_address_kb(addr: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[addr], ["❌ Bekor qilish"]], resize_keyboard=True)

def ariza_omborxona_vacancies_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Zam sklad", "Shafyor", "Reviziyor"], ["❌ Bekor qilish"]], resize_keyboard=True)

def marital_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Uylangan/Turmushga chiqqan"], ["Uylanmagan/Turmushga chiqmagan"], ["❌ Bekor qilish"]], resize_keyboard=True)

def yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Ha", "Yo'q"], ["❌ Bekor qilish"]], resize_keyboard=True)

def study_time_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Kunduzgi", "Kechgi"], ["Sirtqi", "Tuganlanmagan oliy"], ["❌ Bekor qilish"]], resize_keyboard=True)

def education_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["O'rta", "Oliy"], ["O'rta maxsus", "Tuganlanmagan oliy"], ["❌ Bekor qilish"]], resize_keyboard=True)

def lang_level_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["Yomon", "O'rtacha", "Yaxshi"], ["❌ Bekor qilish"]], resize_keyboard=True)

def salary_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["1 500 000 - 1 800 000", "1 800 000 - 2 500 000"], ["2 500 000 - 3 500 000", "3 500 000 - 5 000 000"], ["5 000 000 dan ortiq"], ["❌ Bekor qilish"]], resize_keyboard=True)

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
        f"Assalomu alaykum, {user.first_name}! 👋\nShifo Do'rxona botiga xush kelibsiz.\n\n"
        f"💡 Maslahat: Ishga tezroq joylashish uchun birinchi navbatda *\"🔥 Qaynoq ish o'rinlari\"* bo'limidagi vakansilar bilan tanishib chiqishingizni tavsiya qilamiz.",
        reply_markup=main_menu_kb(user.id),
        parse_mode="Markdown"
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

    if text == "🔥 Qaynoq ish o'rinlari":
        context.user_data["is_general_apply"] = False
        return await user_show_vacancies_first(update, context)

    if text == "💼 Bo'sh ish o'rinlari":
        context.user_data["is_general_apply"] = True
        context.user_data["app_ofis_address"] = ""
        await update.message.reply_text(
            "Bo'limni tanlang:",
            reply_markup=ariza_departments_kb()
        )
        return ARIZA_DEPARTMENT

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

async def ariza_department_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_department"] = text
    if text == "Ofis":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=ariza_ofis_address_kb())
        return ARIZA_OFIS_ADDRESS
    elif text == "Dorixona":
        await update.message.reply_text("Vakansiyani tanlang:", reply_markup=ariza_dorixona_vacancies_kb())
        return ARIZA_VACANCY
    elif text == "Omborxona":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=ariza_ofis_address_kb())
        return ARIZA_OMBOR_ADDRESS
    else:
        await update.message.reply_text("Iltimos, pastdagi tugmalardan birini tanlang:")
        return ARIZA_DEPARTMENT

async def ariza_ofis_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_ofis_address"] = text
    await update.message.reply_text("Vakansiyani tanlang:", reply_markup=ariza_ofis_vacancies_kb())
    return ARIZA_VACANCY

async def ariza_ombor_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_ofis_address"] = text
    await update.message.reply_text("Vakansiyani tanlang:", reply_markup=ariza_omborxona_vacancies_kb())
    return ARIZA_VACANCY

async def ariza_vacancy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_vacancy"] = text
    
    if context.user_data.get("app_department") == "Dorixona":
        await update.message.reply_text("Tumaningizni tanlang:", reply_markup=dorixona_districts_kb())
        return ARIZA_DORIXONA_DISTRICT
    else:
        await update.message.reply_text("👤 Ism va familiyangizni kiriting:", reply_markup=cancel_kb())
        return APPLY_NAME

async def ariza_dorixona_district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_district"] = text
    if text == "Navoiy shahar":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_navoiy_addresses_kb())
    elif text == "Nurota tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb("Quruvchilar ko’chasi 39-uy"))
    elif text == "Karmana tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb("Mirsaid Baxrom MFY"))
    elif text == "Muborak Tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb("Istiqlol MFY Tibbiyoy ko’chasi 11-uy"))
    elif text == "Gijduvon tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb("Sharq ko’chasi 182-uy"))
    elif text == "Paxtachi tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb("Buston MFY Ilhom-baxsh 76-uy"))
    elif text == "Narpay tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb("Zirbuloq ko’chasi 130-uy"))
    elif text == "Xatirchi tuman":
        await update.message.reply_text("Manzilni tanlang:", reply_markup=dorixona_single_address_kb(" Xo’jaqo’rg’on ko’chasi 12-uy"))
    else:
        await update.message.reply_text("Iltimos, pastdagi tugmalardan birini tanlang:")
        return ARIZA_DORIXONA_DISTRICT
        
    return ARIZA_DORIXONA_ADDRESS

async def ariza_dorixona_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_dorixona_address"] = text
    await update.message.reply_text("👤 Ism va familiyangizni kiriting:", reply_markup=cancel_kb())
    return APPLY_NAME

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
    await update.message.reply_text("📍 Yashash manzilingizni kiriting:", reply_markup=cancel_kb())
    return APPLY_ADDRESS

async def apply_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
        
    context.user_data["app_address"] = text
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
    await update.message.reply_text("Oila qurganmisiz?", reply_markup=marital_kb())
    return APPLY_MARITAL

async def apply_marital_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_marital"] = text
    await update.message.reply_text("Siz talabamisiz?", reply_markup=yes_no_kb())
    return APPLY_STUDENT

async def apply_student_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_student"] = text
    if getattr(text, "lower", lambda: "")() == "ha" or text == "Ha":
        await update.message.reply_text("O'qish vaqtingizni tanlang:", reply_markup=study_time_kb())
        return APPLY_STUDY_TIME
    else:
        context.user_data["app_study_time"] = "-"
        await update.message.reply_text("Sizning ta'lim darajangiz qanday?", reply_markup=education_kb())
        return APPLY_EDUCATION

async def apply_study_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_study_time"] = text
    context.user_data["app_education"] = "Talaba"
    await update.message.reply_text("O'z ish tajribangiz haqida yozing:", reply_markup=cancel_kb())
    return APPLY_EXPERIENCE

async def apply_education_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_education"] = text
    await update.message.reply_text("O'z ish tajribangiz haqida yozing:", reply_markup=cancel_kb())
    return APPLY_EXPERIENCE

async def apply_experience_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_experience"] = text
    await update.message.reply_text("O'zbek tili bilish darajasi?", reply_markup=lang_level_kb())
    return APPLY_LANG_UZ

async def apply_lang_uz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_lang_uz"] = text
    await update.message.reply_text("Rus tili bilish darajasi?", reply_markup=lang_level_kb())
    return APPLY_LANG_RU

async def apply_lang_ru_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_lang_ru"] = text
    await update.message.reply_text("Ingliz tili bilish darajasi?", reply_markup=lang_level_kb())
    return APPLY_LANG_EN

async def apply_lang_en_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_lang_en"] = text
    await update.message.reply_text("Kutilgan ish maoshini darajasini ko'rsating (so'm):", reply_markup=salary_kb())
    return APPLY_SALARY

async def apply_salary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if check_cancel(text, user_id):
        await update.message.reply_text("Ariza bekor qilindi.", reply_markup=main_menu_kb(user_id))
        return MENU
    context.user_data["app_salary"] = text
    
    is_general = context.user_data.get("is_general_apply")
    uname = update.effective_user.username or "Noma'lum"

    info_str = (
        f"👥 *Nomzod Ma'lumotlari:*\n"
        f"👤 Ism: {context.user_data.get('app_name')}\n"
        f"🗓️ Tug'ilgan sana: {context.user_data.get('app_birthday')}\n"
        f"📍 Manzil: {context.user_data.get('app_address')}\n"
        f"☎️ Telefon: {context.user_data.get('app_phone')}\n"
        f"💍 Oila holati: {context.user_data.get('app_marital')}\n"
        f"🎓 Talabami?: {context.user_data.get('app_student')}\n"
        f"⏰ O'qish vaqti: {context.user_data.get('app_study_time')}\n"
        f"📚 Ta'lim darajasi: {context.user_data.get('app_education')}\n"
        f"⏳ Ish tajribasi: {context.user_data.get('app_experience')}\n"
        f"🇺🇿 O'zbek tili: {context.user_data.get('app_lang_uz')}\n"
        f"🇷🇺 Rus tili: {context.user_data.get('app_lang_ru')}\n"
        f"🇬🇧 Ingliz tili: {context.user_data.get('app_lang_en')}\n"
        f"💸 Kutilayotgan maosh: {context.user_data.get('app_salary')}\n\n"
        f"Username: @{uname}"
    )

    if is_general:
        dep = context.user_data.get('app_department', '-')
        if dep == "Dorixona":
            loc_info = (
                f"🏙 Tuman/Shahar: {context.user_data.get('app_district', '-')}\n"
                f"📍 Manzil: {context.user_data.get('app_dorixona_address', '-')}\n"
            )
        else:
            loc_info = f"📍 Manzil (Ofis/Ombor): {context.user_data.get('app_ofis_address', '-')}\n"
            
        admin_msg = (
            f"📩 *YANGI UMUMIY ARIZA*\n\n"
            f"🏢 Bo'lim: {dep}\n"
            f"💼 Kutilayotgan Vakansiya: {context.user_data.get('app_vacancy', '-')}\n"
            + loc_info + "\n"
            + info_str
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
            + info_str
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
            ARIZA_DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ariza_department_handler)],
            ARIZA_OFIS_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ariza_ofis_address_handler)],
            ARIZA_OMBOR_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ariza_ombor_address_handler)],
            ARIZA_VACANCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ariza_vacancy_handler)],
            ARIZA_DORIXONA_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ariza_dorixona_district_handler)],
            ARIZA_DORIXONA_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ariza_dorixona_address_handler)],
            APPLY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_name_handler)],
            APPLY_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_birthday_handler)],
            APPLY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_address_handler)],
            APPLY_PHONE: [MessageHandler(filters.ALL & ~filters.COMMAND, apply_phone_handler)],
            APPLY_MARITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_marital_handler)],
            APPLY_STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_student_handler)],
            APPLY_STUDY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_study_time_handler)],
            APPLY_EDUCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_education_handler)],
            APPLY_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_experience_handler)],
            APPLY_LANG_UZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_lang_uz_handler)],
            APPLY_LANG_RU: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_lang_ru_handler)],
            APPLY_LANG_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_lang_en_handler)],
            APPLY_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_salary_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    logger.info("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
