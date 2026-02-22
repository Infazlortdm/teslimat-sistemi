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

TOKEN = os.getenv("8191531749:AAFqEELtLO-XFmvHdf99EZ5WNxwjG9d6LcU")
ADMIN_ID = int(os.getenv("8452588697"))

DATA_FILE = "data.json"

# -------------------- VERİ YÜKLE --------------------
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

# -------------------- START --------------------
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

    await update.message.reply_text("Yetkiniz yok.")

# -------------------- MESAJ --------------------
async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    # -------- ADMIN --------
    if user_id == str(ADMIN_ID):

        if text == "➕ Kurye Ekle":
            await update.message.reply_text("Kurye ID gönder:")
            context.user_data["mod"] = "kurye_ekle"

        elif text == "➕ İşletme Ekle":
            await update.message.reply_text("İşletme ID gönder:")
            context.user_data["mod"] = "isletme_ekle"

        elif text == "🌍 Bölge Ekle":
            await update.message.reply_text("Bölge adı gönder:")
            context.user_data["mod"] = "bolge_ekle"

        elif text == "📦 Tüm Siparişler":
            for s in data["siparisler"]:
                await update.message.reply_text(
                    f"ID:{s['id']} | Bölge:{s['bolge']} | Durum:{s['durum']}"
                )

        elif context.user_data.get("mod") == "kurye_ekle":
            data["kuryeler"][text] = {"bolge": "", "aktif": True}
            save_data(data)
            await update.message.reply_text("✅ Kurye eklendi.")
            context.user_data["mod"] = None

        elif context.user_data.get("mod") == "isletme_ekle":
            data["isletmeler"][text] = {"aktif": True}
            save_data(data)
            await update.message.reply_text("✅ İşletme eklendi.")
            context.user_data["mod"] = None

        elif context.user_data.get("mod") == "bolge_ekle":
            data["bolgeler"].append(text)
            save_data(data)
            await update.message.reply_text("✅ Bölge eklendi.")
            context.user_data["mod"] = None

    # -------- KURYE --------
    elif user_id in data["kuryeler"]:

        if text == "🟡 Bekleyenler":
            for s in data["siparisler"]:
                if s["durum"] == "Bekliyor":
                    await update.message.reply_photo(
                        photo=s["foto"],
                        caption=f"ID:{s['id']} /al {s['id']}"
                    )

        elif text == "🔵 Aldıklarım":
            for s in data["siparisler"]:
                if s["alan"] == user_id:
                    await update.message.reply_text(f"ID:{s['id']} | {s['durum']}")

        elif text == "🟢 Teslim Ettiklerim":
            for s in data["siparisler"]:
                if s["alan"] == user_id and s["durum"] == "Teslim":
                    await update.message.reply_text(f"ID:{s['id']}")

    # -------- İŞLETME --------
    elif user_id in data["isletmeler"]:

        if text == "📦 Sipariş Oluştur":
            keyboard = [[b] for b in data["bolgeler"]]
            await update.message.reply_text(
                "Bölge seç:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            context.user_data["mod"] = "bolge_sec"

        elif context.user_data.get("mod") == "bolge_sec":
            context.user_data["bolge"] = text
            await update.message.reply_text("Fotoğraf gönder:")
            context.user_data["mod"] = "foto_bekle"

# -------------------- FOTO --------------------
async def foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in data["isletmeler"] and context.user_data.get("mod") == "foto_bekle":
        siparis_id = len(data["siparisler"]) + 1
        data["siparisler"].append({
            "id": siparis_id,
            "isletme": user_id,
            "bolge": context.user_data["bolge"],
            "foto": update.message.photo[-1].file_id,
            "alan": "",
            "durum": "Bekliyor"
        })
        save_data(data)
        await update.message.reply_text("✅ Sipariş oluşturuldu.")
        context.user_data["mod"] = None

# -------------------- SİPARİŞ AL --------------------
async def al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    siparis_id = context.args[0]

    for s in data["siparisler"]:
        if str(s["id"]) == siparis_id and s["durum"] == "Bekliyor":
            s["alan"] = user_id
            s["durum"] = "Alındı"
            save_data(data)
            await update.message.reply_text("✅ Sipariş alındı.")

# -------------------- MAIN --------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("al", al))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj))
    app.add_handler(MessageHandler(filters.PHOTO, foto))

    print("BOT AKTİF 🚀")
    app.run_polling()
