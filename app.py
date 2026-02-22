import sqlite3
import logging
from telegram import *
from telegram.ext import *
import asyncio

TOKEN = "8229950774:AAGO63nQ_NfYnznbO8a4Qm_B-cCOGxESvQM"
ADMIN_ID = 8452588697

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# ------------------ DATABASE ------------------

cursor.execute("""CREATE TABLE IF NOT EXISTS regions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT UNIQUE)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS couriers(
id INTEGER PRIMARY KEY,
active INTEGER DEFAULT 1)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS courier_regions(
courier_id INTEGER,
region_id INTEGER)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS businesses(
id INTEGER PRIMARY KEY,
name TEXT,
region_id INTEGER,
active INTEGER DEFAULT 1)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
business_id INTEGER,
region_id INTEGER,
photo TEXT,
courier_id INTEGER,
status TEXT DEFAULT 'waiting')""")

conn.commit()

# ------------------ HELPERS ------------------

def get_role(user_id):
    if user_id == ADMIN_ID:
        return "admin"
    cursor.execute("SELECT * FROM couriers WHERE id=?", (user_id,))
    if cursor.fetchone():
        return "courier"
    cursor.execute("SELECT * FROM businesses WHERE id=?", (user_id,))
    if cursor.fetchone():
        return "business"
    return None

def least_busy_courier(region_id):
    cursor.execute("""
    SELECT couriers.id, COUNT(orders.id) as total
    FROM couriers
    JOIN courier_regions ON couriers.id=courier_regions.courier_id
    LEFT JOIN orders ON orders.courier_id=couriers.id AND orders.status!='delivered'
    WHERE courier_regions.region_id=?
    GROUP BY couriers.id
    ORDER BY total ASC
    LIMIT 1
    """, (region_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# ------------------ START ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_role(user_id)

    if role == "admin":
        keyboard = [
            [KeyboardButton("👤 Kurye Yönet"), KeyboardButton("🏪 İşletme Yönet")],
            [KeyboardButton("🗺 Bölge Yönet"), KeyboardButton("📦 Tüm Siparişler")]
        ]
        await update.message.reply_text("👑 ADMIN PANEL", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif role == "courier":
        keyboard = [
            [KeyboardButton("📥 Yeni Atananlar"), KeyboardButton("📦 Aktif Teslimatlarım")],
            [KeyboardButton("🔎 Fiş Sorgu")]
        ]
        await update.message.reply_text("🚚 KURYE PANELİ", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif role == "business":
        keyboard = [
            [KeyboardButton("📦 Yeni Sipariş"), KeyboardButton("📋 Aktif Siparişlerim")],
            [KeyboardButton("🔎 Fiş Sorgu")]
        ]
        await update.message.reply_text("🏪 İŞLETME PANELİ", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    else:
        await update.message.reply_text("Yetkiniz yok.")

# ------------------ ORDER FLOW ------------------

async def new_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Fiş fotoğrafını gönder.")
    context.user_data["await_photo"] = True

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("await_photo"):
        user_id = update.effective_user.id
        photo_id = update.message.photo[-1].file_id

        cursor.execute("SELECT region_id FROM businesses WHERE id=?", (user_id,))
        region = cursor.fetchone()
        if not region:
            await update.message.reply_text("Bölge bulunamadı.")
            return

        courier = least_busy_courier(region[0])
        if not courier:
            await update.message.reply_text("⚠️ Bu bölgede aktif kurye yok.")
            return

        cursor.execute("INSERT INTO orders(business_id,region_id,photo,courier_id) VALUES(?,?,?,?)",
                       (user_id, region[0], photo_id, courier))
        conn.commit()

        order_id = cursor.lastrowid

        await update.message.reply_text(f"✅ Sipariş #{order_id} oluşturuldu.")

        await context.bot.send_photo(
            chat_id=courier,
            photo=photo_id,
            caption=f"📦 Yeni Sipariş #{order_id}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 Siparişi Aldım", callback_data=f"take_{order_id}")]
            ])
        )

        context.user_data["await_photo"] = False

# ------------------ CALLBACK ------------------

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("take_"):
        order_id = int(data.split("_")[1])
        cursor.execute("UPDATE orders SET status='taken' WHERE id=?", (order_id,))
        conn.commit()

        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Teslim Ettim", callback_data=f"deliver_{order_id}")]
        ]))

    elif data.startswith("deliver_"):
        order_id = int(data.split("_")[1])
        cursor.execute("UPDATE orders SET status='delivered' WHERE id=?", (order_id,))
        conn.commit()

        cursor.execute("SELECT business_id FROM orders WHERE id=?", (order_id,))
        business_id = cursor.fetchone()[0]

        await context.bot.send_message(business_id, f"✅ Sipariş #{order_id} teslim edildi.")

        await query.edit_message_text(f"✅ Sipariş #{order_id} teslim edildi.")

# ------------------ HANDLER ------------------

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📦 Yeni Sipariş":
        await new_order(update, context)

    elif text == "📦 Aktif Teslimatlarım":
        user_id = update.effective_user.id
        cursor.execute("SELECT id FROM orders WHERE courier_id=? AND status!='delivered'", (user_id,))
        orders = cursor.fetchall()
        if orders:
            await update.message.reply_text("Aktif Siparişler:\n" + "\n".join([f"#{o[0]}" for o in orders]))
        else:
            await update.message.reply_text("Aktif sipariş yok.")

    elif text == "📋 Aktif Siparişlerim":
        user_id = update.effective_user.id
        cursor.execute("SELECT id,status FROM orders WHERE business_id=?", (user_id,))
        orders = cursor.fetchall()
        if orders:
            msg = "\n".join([f"#{o[0]} - {o[1]}" for o in orders])
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Sipariş yok.")

# ------------------ MAIN ------------------

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
app.add_handler(CallbackQueryHandler(buttons))

print("Bot çalışıyor...")
app.run_polling()
