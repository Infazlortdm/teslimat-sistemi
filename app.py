import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ===============================
# SABİT BİLGİLER (ENV GEREKMİYOR)
# ===============================

TOKEN = "8191531749:AAFqEELtLO-XFmvHdf99EZ5WNxwjG9d6LcU"
ADMIN_ID = 8452588697

DATA_FILE = "data.json"

# ===============================
# VERİ YÜKLE / KAYDET
# ===============================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "kuryeler": {},
            "isletmeler": {},
            "bolgeler": [],
            "siparisler": []
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ===============================
# START
# ===============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id == str(ADMIN_ID):
        keyboard = [
            ["➕ Kurye Ekle", "➕ İşletme Ekle"],
            ["🌍 Bölge Ekle", "📦 Tüm Siparişler"],
        ]
        await update.message.reply_text(
            "👑 ADMIN PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    if user_id in data["isletmeler"]:
        keyboard = [
            ["📦 Sipariş Oluştur"],
            ["📋 Siparişlerim"],
            ["🚪 Çıkış Yap"]
        ]
        await update.message.reply_text(
            "🏪 İŞLETME PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    if user_id in data["kuryeler"]:
        keyboard = [
            ["🟡 Bekleyenler"],
            ["🔵 Aldıklarım"],
            ["🟢 Teslim Ettiklerim"],
            ["🚪 Çıkış Yap"]
        ]
        await update.message.reply_text(
            "🚚 KURYE PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    await update.message.reply_text("⛔ Yetkiniz yok.")

# ===============================
# ADMIN / MESAJ
# ===============================

async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id == str(ADMIN_ID):

        if text == "➕ Kurye Ekle":
            await update.message.reply_text("Kurye ID gönder:")
            context.user_data["mod"] = "kurye"

        elif text == "➕ İşletme Ekle":
            await update.message.reply_text("İşletme ID gönder:")
            context.user_data["mod"] = "isletme"

        elif text == "🌍 Bölge Ekle":
            await update.message.reply_text("Bölge adı gönder:")
            context.user_data["mod"] = "bolge"

        elif text == "📦 Tüm Siparişler":
            if not data["siparisler"]:
                await update.message.reply_text("Sipariş yok.")
                return
            for s in data["siparisler"]:
                await update.message.reply_text(
                    f"ID:{s['id']} | Bölge:{s['bolge']} | Durum:{s['durum']}"
                )

        elif context.user_data.get("mod") == "kurye":
            data["kuryeler"][text] = {}
            save_data(data)
            await update.message.reply_text("✅ Kurye eklendi.")
            context.user_data["mod"] = None

        elif context.user_data.get("mod") == "isletme":
            data["isletmeler"][text] = {}
            save_data(data)
            await update.message.reply_text("✅ İşletme eklendi.")
            context.user_data["mod"] = None

        elif context.user_data.get("mod") == "bolge":
            data["bolgeler"].append(text)
            save_data(data)
            await update.message.reply_text("✅ Bölge eklendi.")
            context.user_data["mod"] = None

# ===============================
# SİPARİŞ OLUŞTURMA
# ===============================

async def foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in data["isletmeler"]:
        siparis_id = len(data["siparisler"]) + 1
        data["siparisler"].append({
            "id": siparis_id,
            "isletme": user_id,
            "bolge": "Genel",
            "foto": update.message.photo[-1].file_id,
            "alan": "",
            "durum": "Bekliyor"
        })
        save_data(data)
        await update.message.reply_text("✅ Sipariş oluşturuldu.")

# ===============================
# SİPARİŞ AL
# ===============================

async def al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    siparis_id = context.args[0]

    for s in data["siparisler"]:
        if str(s["id"]) == siparis_id and s["durum"] == "Bekliyor":
            s["alan"] = user_id
            s["durum"] = "Alındı"
            save_data(data)
            await update.message.reply_text("✅ Sipariş alındı.")

# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("al", al))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj))
    app.add_handler(MessageHandler(filters.PHOTO, foto))

    print("BOT AKTİF 🚀")
    app.run_polling()
