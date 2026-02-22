import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("8191531749:AAFqEELtLO-XFmvHdf99EZ5WNxwjG9d6LcU")

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT,
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
    courier TEXT
)
""")
conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["İşletmeyim", "Kuryeyim"]]
    await update.message.reply_text(
        "Hoşgeldin 👋\nRolünü seç:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.message.from_user.id)

    if text == "İşletmeyim":
        cursor.execute("INSERT INTO users (telegram_id, role) VALUES (?, ?)", (user_id, "business"))
        conn.commit()
        await update.message.reply_text("İşletme adını yaz:")
        context.user_data["role"] = "business"

    elif text == "Kuryeyim":
        cursor.execute("INSERT INTO users (telegram_id, role) VALUES (?, ?)", (user_id, "courier"))
        conn.commit()
        await update.message.reply_text("Adını yaz:")
        context.user_data["role"] = "courier"


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if context.user_data.get("role") == "business":
        cursor.execute("UPDATE users SET name=? WHERE telegram_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Bölgeni yaz:")
        context.user_data["role"] = "business_region"

    elif context.user_data.get("role") == "business_region":
        cursor.execute("UPDATE users SET region=? WHERE telegram_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Sipariş oluşturmak için /siparis yaz")
        context.user_data.clear()

    elif context.user_data.get("role") == "courier":
        cursor.execute("UPDATE users SET name=? WHERE telegram_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Bölgeni yaz:")
        context.user_data["role"] = "courier_region"

    elif context.user_data.get("role") == "courier_region":
        cursor.execute("UPDATE users SET region=? WHERE telegram_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Sipariş görmek için /paketler yaz")
        context.user_data.clear()


async def siparis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cursor.execute("SELECT name, region FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    if user:
        cursor.execute("INSERT INTO orders (business_name, region, status) VALUES (?, ?, ?)",
                       (user[0], user[1], "bekliyor"))
        conn.commit()
        await update.message.reply_text("Sipariş oluşturuldu ✅")


async def paketler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cursor.execute("SELECT region FROM users WHERE telegram_id=?", (user_id,))
    region = cursor.fetchone()

    if region:
        cursor.execute("SELECT id, business_name FROM orders WHERE region=? AND status='bekliyor'", (region[0],))
        orders = cursor.fetchall()

        if orders:
            msg = "📦 Bekleyen Siparişler:\n"
            for o in orders:
                msg += f"Sipariş No: {o[0]} - {o[1]}\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Bu bölgede bekleyen sipariş yok.")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("siparis", siparis))
app.add_handler(CommandHandler("paketler", paketler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, role_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling()
