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

TOKEN = "8191531749:AAFqEELtLO-XFmvHdf99EZ5WNxwjG9d6LcU"
ADMIN_ID = 8452588697

DATA_FILE = "data.json"

# ---------------- DATA ----------------

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

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id == str(ADMIN_ID):
        keyboard = [
            ["➕ Kurye Ekle", "➕ İşletme Ekle"],
            ["🌍 Bölge Ekle", "📍 Kurye Bölge Ata"],
            ["📦 Sipariş Oluştur", "📋 Tüm Siparişler"]
        ]
        await update.message.reply_text(
            "👑 ADMIN PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    if user_id in data["isletmeler"]:
        keyboard = [
            ["📦 Sipariş Oluştur"],
            ["📋 Siparişlerim"]
        ]
        await update.message.reply_text(
            "🏪 İŞLETME PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    if user_id in data["kuryeler"]:
        keyboard = [
            ["🟡 Bekleyenler"],
            ["🔵 Aldıklarım"],
            ["🟢 Teslim Ettiklerim"]
        ]
        await update.message.reply_text(
            f"🚚 KURYE PANEL\n📍 Bölgen: {data['kuryeler'][user_id]['bolge']}",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    await update.message.reply_text("⛔ Yetkiniz yok.")

# ---------------- ADMIN ----------------

async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    # ADMIN
    if user_id == str(ADMIN_ID):

        if text == "➕ Kurye Ekle":
            await update.message.reply_text("Kurye ID gönder:")
            context.user_data["mod"] = "kurye"

        elif text == "➕ İşletme Ekle":
            await update.message.reply_text("İşletme ID gönder:")
            context.user_data["mod"] = "isletme"

        elif text == "🌍 Bölge Ekle":
            await update.message.reply_text("Bölge adı:")
            context.user_data["mod"] = "bolge"

        elif text == "📍 Kurye Bölge Ata":
            await update.message.reply_text("Kurye ID gönder:")
            context.user_data["mod"] = "bolge_kurye_id"

        elif text == "📦 Sipariş Oluştur":
            keyboard = [[b] for b in data["bolgeler"]]
            await update.message.reply_text(
                "Bölge seç:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            context.user_data["mod"] = "siparis_bolge"

        elif context.user_data.get("mod") == "kurye":
            data["kuryeler"][text] = {"bolge": ""}
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

        elif context.user_data.get("mod") == "bolge_kurye_id":
            context.user_data["kurye_id"] = text
            await update.message.reply_text("Atanacak bölge adı:")
            context.user_data["mod"] = "bolge_ata"

        elif context.user_data.get("mod") == "bolge_ata":
            kurye_id = context.user_data["kurye_id"]
            if kurye_id in data["kuryeler"]:
                data["kuryeler"][kurye_id]["bolge"] = text
                save_data(data)
                await update.message.reply_text("✅ Bölge atandı.")
            context.user_data["mod"] = None

        elif context.user_data.get("mod") == "siparis_bolge":
            context.user_data["bolge"] = text
            await update.message.reply_text("Fotoğraf gönder:")
            context.user_data["mod"] = "siparis_foto"

    # KURYE
    elif user_id in data["kuryeler"]:

        if text == "🟡 Bekleyenler":
            for s in data["siparisler"]:
                if s["bolge"] == data["kuryeler"][user_id]["bolge"] and s["durum"] == "Bekliyor":
                    await update.message.reply_photo(
                        s["foto"],
                        caption=f"📦 ID:{s['id']}\n/al {s['id']}"
                    )

        elif text == "🔵 Aldıklarım":
            for s in data["siparisler"]:
                if s["alan"] == user_id and s["durum"] == "Alındı":
                    await update.message.reply_text(f"📦 {s['id']}")

        elif text == "🟢 Teslim Ettiklerim":
            for s in data["siparisler"]:
                if s["alan"] == user_id and s["durum"] == "Teslim":
                    await update.message.reply_text(f"📦 {s['id']}")

# ---------------- FOTO ----------------

async def foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if context.user_data.get("mod") == "siparis_foto":
        siparis_id = len(data["siparisler"]) + 1

        data["siparisler"].append({
            "id": siparis_id,
            "bolge": context.user_data["bolge"],
            "foto": update.message.photo[-1].file_id,
            "alan": "",
            "durum": "Bekliyor"
        })

        save_data(data)

        # 🔔 BÖLGEDEKİ KURYELERE BİLDİRİM
        for k_id, k in data["kuryeler"].items():
            if k["bolge"] == context.user_data["bolge"]:
                try:
                    await context.bot.send_message(
                        chat_id=int(k_id),
                        text=f"🔔 {k['bolge']} bölgesinde yeni sipariş var!"
                    )
                except:
                    pass

        await update.message.reply_text("✅ Sipariş oluşturuldu.")
        context.user_data["mod"] = None

# ---------------- SİPARİŞ AL ----------------

async def al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    siparis_id = context.args[0]

    for s in data["siparisler"]:
        if str(s["id"]) == siparis_id and s["durum"] == "Bekliyor":
            s["alan"] = user_id
            s["durum"] = "Alındı"
            save_data(data)
            await update.message.reply_text("✅ Sipariş alındı.")

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("al", al))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj))
    app.add_handler(MessageHandler(filters.PHOTO, foto))

    print("🚀 SİSTEM AKTİF")
    app.run_polling()
