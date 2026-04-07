# ---------------- Admin Navigation Logic ----------------

async def show_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['level'] = 'region'
    items = db_query("SELECT id, name FROM regions")
    # Using navigation_kb which you defined in your code
    await update.message.reply_text(
        "📍 **Admin: Viloyatlar ro'yxati**",
        reply_markup=navigation_kb(items, "Viloyat"),
        parse_mode='Markdown'
    )
    return ADMIN_NAV

async def show_districts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['level'] = 'district'
    region_id = context.user_data['region_id']
    region_name = context.user_data['region_name']
    items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (region_id,))
    await update.message.reply_text(
        f"🏙 **{region_name} tumanlari**",
        reply_markup=navigation_kb(items, "Tuman"),
        parse_mode='Markdown'
    )
    return ADMIN_NAV

async def show_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['level'] = 'branch'
    district_id = context.user_data['district_id']
    district_name = context.user_data['district_name']
    items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (district_id,))
    await update.message.reply_text(
        f"🏪 **{district_name} filiallari**",
        reply_markup=navigation_kb(items, "Filial"),
        parse_mode='Markdown'
    )
    return ADMIN_NAV

async def show_delete_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates the list of items to delete with trash icons"""
    level = context.user_data.get('level')
    if level == 'region':
        items = db_query("SELECT id, name FROM regions")
    elif level == 'district':
        items = db_query("SELECT id, name FROM districts WHERE region_id = ?", (context.user_data['region_id'],))
    else:
        items = db_query("SELECT id, name FROM branches WHERE district_id = ?", (context.user_data['district_id'],))
    
    kb = [[f"🗑 {i[1]}"] for i in items]
    kb.append(["⬅️ Back"])
    await update.message.reply_text(
        f"O'chirish uchun {level}ni tanlang:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return ADMIN_DELETE_CONFIRM

# ---------------- Handlers ----------------

async def admin_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get('level') 

    if text == "🏠 Main Menu":
        # Fixed: using main_menu_kb as defined in your code
        await update.message.reply_text("Menyuga qaytildi.", reply_markup=main_menu_kb(update.effective_user.id))
        return MENU
    
    if text == "⬅️ Back":
        if level == 'region': 
            await update.message.reply_text("Bekor qilindi.", reply_markup=main_menu_kb(update.effective_user.id))
            return MENU
        if level == 'district': return await show_regions(update, context)
        if level == 'branch': return await show_districts(update, context)

    if text.startswith("➕ Add"):
        await update.message.reply_text(f"✍️ Yangi {level} nomini kiriting:", reply_markup=ReplyKeyboardRemove())
        return ADMIN_INPUT

    if text.startswith("❌ Delete"):
        return await show_delete_options(update, context)

    # Drill down logic
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
            db_execute("INSERT INTO districts (name, region_id) VALUES (?, ?)", (name, context.user_data['region_id']))
        elif level == 'branch':
            db_execute("INSERT INTO branches (name, district_id) VALUES (?, ?)", (name, context.user_data['district_id']))
        await update.message.reply_text(f"✅ {name} qo'shildi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

    # Return to refresh buttons
    if level == 'region': return await show_regions(update, context)
    if level == 'district': return await show_districts(update, context)
    return await show_branches(update, context)

async def admin_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    level = context.user_data.get('level')

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
        await update.message.reply_text(f"❌ Xatolik: {e}")

    if level == 'region': return await show_regions(update, context)
    if level == 'district': return await show_districts(update, context)
    return await show_branches(update, context)
