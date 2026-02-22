import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

TOKEN = "8191531749:AAFqEELtLO-XFmvHdf99EZ5WNxwjG9d6LcU"
ADMIN_ID = 8452588697

# DATABASE
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    role TEXT,
    name TEXT,
    region TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT,
    region TEXT,
    status TEXT,
    courier INTEGER
)
""")
conn.commit()

# STATES
ROLE, NAME, REGION = range(3)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["İşletmeyim", "Kuryeyim"]]
    await update.message.reply_text(
        "Hoşgeldin 👋\nRolünü seç:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return ROLE

# ROLE
async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "İşletmeyim":
        context.user_data["role"] = "business"
        await update.message.reply_text("İşletme adını yaz:")
        return NAME

    elif text == "Kuryeyim":
        context.user_data["role"] = "courier"
        await update.message.reply_text("Adını yaz:")
        return NAME

    else:
        await update.message.reply_text("Buton kullan.")
        return ROLE

# NAME
async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Bölgeni yaz:")
    return REGION

# REGION
async def save_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    region = update.message.text
    role = context.user_data["role"]
    name = context.user_data["name"]

    cursor.execute(
        "INSERT OR REPLACE INTO users (telegram_id, role, name, region) VALUES (?, ?, ?, ?)",
        (user_id, role, name, region),
    )
    conn.commit()

    if role == "business":
        await update.message.reply_text("Kayıt tamam ✅\nSipariş için /siparis yaz")
    else:
        await update.message.reply_text("Kayıt tamam ✅\nPaketler için /paketler yaz")

    return ConversationHandler.END

# SİPARİŞ
async def siparis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    cursor.execute("SELECT role, name, region FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    if not user or user[0] != "business":
        await update.message.reply_text("Sadece işletme sipariş oluşturabilir.")
        return

    cursor.execute(
        "INSERT INTO orders (business_name, region, status) VALUES (?, ?, ?)",
        (user[1], user[2], "bekliyor"),
    )
    conn.commit()

    await update.message.reply_text("Sipariş oluşturuldu ✅")

# PAKETLER
async def paketler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    cursor.execute("SELECT role, region FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    if not user or user[0] != "courier":
        await update.message.reply_text("Sadece kurye görebilir.")
        return

    cursor.execute(
        "SELECT id, business_name FROM orders WHERE region=? AND status='bekliyor'",
        (user[1],),
    )
    orders = cursor.fetchall()

    if not orders:
        await update.message.reply_text("Bu bölgede paket yok.")
        return

    text = "📦 Bekleyen Paketler:\n"
    for o in orders:
        text += f"No: {o[0]} - {o[1]}\n"

    await update.message.reply_text(text)

# ADMIN
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("Yetkin yok.")
        return

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='business'")
    b = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='courier'")
    c = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders")
    o = cursor.fetchone()[0]

    await update.message.reply_text(
        f"📊 ADMIN PANEL\n\nİşletme: {b}\nKurye: {c}\nToplam Sipariş: {o}"
    )

# APP
app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_region)],
    },
    fallbacks=[],
)

app.add_handler(conv)
app.add_handler(CommandHandler("siparis", siparis))
app.add_handler(CommandHandler("paketler", paketler))
app.add_handler(CommandHandler("admin", admin))

print("Bot çalışıyor...")
app.run_polling()
