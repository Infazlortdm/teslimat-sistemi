import sqlite3
import logging
from telegram import *
from telegram.ext import *

TOKEN = "8229950774:AAGO63nQ_NfYnznbO8a4Qm_B-cCOGxESvQM"
ADMIN_ID = 8452588697

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS regions(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute("CREATE TABLE IF NOT EXISTS couriers(id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS businesses(id INTEGER PRIMARY KEY, name TEXT, region_id INTEGER)")
conn.commit()


def is_admin(user_id):
    return user_id == ADMIN_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_admin(user_id):
        await admin_panel(update)
    else:
        await update.message.reply_text("Yetkiniz yok.")


async def admin_panel(update):
    keyboard = [
        ["👤 Kurye Yönet", "🏪 İşletme Yönet"],
        ["🗺 Bölge Yönet"]
    ]
    await update.message.reply_text(
        "👑 ADMIN PANEL",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ------------------ MENÜLER ------------------

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "👤 Kurye Yönet":
        keyboard = [
            ["➕ Kurye Ekle"],
            ["🔙 Geri"]
        ]
        await update.message.reply_text(
            "👤 Kurye Yönet",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    elif text == "🏪 İşletme Yönet":
        keyboard = [
            ["➕ İşletme Ekle"],
            ["🔙 Geri"]
        ]
        await update.message.reply_text(
            "🏪 İşletme Yönet",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    elif text == "🗺 Bölge Yönet":
        keyboard = [
            ["➕ Bölge Ekle"],
            ["📋 Bölgeleri Listele"],
            ["🔙 Geri"]
        ]
        await update.message.reply_text(
            "🗺 Bölge Yönet",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    elif text == "🔙 Geri":
        await admin_panel(update)

    elif text == "➕ Bölge Ekle":
        context.user_data["add_region"] = True
        await update.message.reply_text("Bölge adını yaz:")

    elif context.user_data.get("add_region"):
        try:
            cursor.execute("INSERT INTO regions(name) VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Bölge eklendi.")
        except:
            await update.message.reply_text("⚠️ Bu bölge zaten var.")
        context.user_data["add_region"] = False

    elif text == "📋 Bölgeleri Listele":
        cursor.execute("SELECT name FROM regions")
        regions = cursor.fetchall()
        if regions:
            msg = "\n".join([r[0] for r in regions])
            await update.message.reply_text("📍 Bölgeler:\n" + msg)
        else:
            await update.message.reply_text("Bölge yok.")

    elif text == "➕ Kurye Ekle":
        context.user_data["add_courier"] = True
        await update.message.reply_text("Kurye Telegram ID yaz:")

    elif context.user_data.get("add_courier"):
        try:
            courier_id = int(text)
            cursor.execute("INSERT INTO couriers(id) VALUES(?)", (courier_id,))
            conn.commit()
            await update.message.reply_text("✅ Kurye eklendi.")
        except:
            await update.message.reply_text("⚠️ Hatalı veya zaten var.")
        context.user_data["add_courier"] = False

    elif text == "➕ İşletme Ekle":
        context.user_data["add_business"] = True
        await update.message.reply_text("İşletme Telegram ID yaz:")

    elif context.user_data.get("add_business"):
        try:
            business_id = int(text)
            cursor.execute("INSERT INTO businesses(id,name,region_id) VALUES(?,?,?)",
                           (business_id, "İşletme", 1))
            conn.commit()
            await update.message.reply_text("✅ İşletme eklendi.")
        except:
            await update.message.reply_text("⚠️ Hatalı veya zaten var.")
        context.user_data["add_business"] = False


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

print("Bot aktif...")
app.run_polling()
