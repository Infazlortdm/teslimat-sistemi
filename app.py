import os
import json
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

TOKEN = "8191531749:AAFqEELtLO-XFmvHdf99EZ5WNxwjG9d6LcU"
ADMIN_ID = 8452588697

DATA_FILE = "data.json"

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

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f)

data = load_data()

# ---------------- ADMIN TÜM SİPARİŞLER ----------------

async def tum_siparisler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not data["siparisler"]:
        await update.message.reply_text("Sipariş yok.")
        return

    for s in data["siparisler"]:
        await update.message.reply_text(
            f"📦 {s['id']} | {s['bolge']} | {s['isletme']} | {s['durum']}"
        )

# ---------------- BEKLEYEN ----------------

async def bekleyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in data["kuryeler"]:
        return

    kurye_bolgeler = data["kuryeler"][user_id]["bolgeler"]

    bulundu = False

    for s in data["siparisler"]:
        if s["durum"] == "Bekliyor" and s["bolge"] in kurye_bolgeler:

            bulundu = True

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 Al", callback_data=f"al_{s['id']}")]
            ])

            await update.message.reply_photo(
                s["foto"],
                caption=f"📦 {s['id']}\n📍 {s['bolge']}\n🏪 {s['isletme']}",
                reply_markup=keyboard
            )

    if not bulundu:
        await update.message.reply_text("Bu bölgede bekleyen sipariş yok.")

# ---------------- CALLBACK ----------------

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data_id = query.data

    if data_id.startswith("al_"):
        siparis_id = data_id.split("_")[1]

        for s in data["siparisler"]:
            if str(s["id"]) == siparis_id and s["durum"] == "Bekliyor":

                s["durum"] = "Alındı"
                s["alan"] = user_id
                save_data(data)

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 Teslim Ettim", callback_data=f"teslim_{siparis_id}")]
                ])

                await query.edit_message_reply_markup(reply_markup=keyboard)
                return

    if data_id.startswith("teslim_"):
        siparis_id = data_id.split("_")[1]

        for s in data["siparisler"]:
            if str(s["id"]) == siparis_id and s["alan"] == user_id:

                s["durum"] = "Teslim"
                save_data(data)

                await context.bot.send_message(
                    chat_id=int(s["isletme"]),
                    text=f"✅ {siparis_id} nolu sipariş teslim edildi."
                )

                await query.edit_message_reply_markup(reply_markup=None)
                return

# ---------------- SİPARİŞ OLUŞTUR ----------------

async def siparis_olustur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in data["isletmeler"] and user_id != str(ADMIN_ID):
        return

    bolge = context.args[0]
    isletme_adi = context.args[1]

    aktif_kurye_var = False
    for k in data["kuryeler"].values():
        if bolge in k["bolgeler"]:
            aktif_kurye_var = True

    if not aktif_kurye_var:
        await update.message.reply_text("⚠️ Bu bölgede atanmış kurye yok!")
        return

    siparis_id = len(data["siparisler"]) + 1

    data["siparisler"].append({
        "id": siparis_id,
        "bolge": bolge,
        "isletme": isletme_adi,
        "foto": None,
        "alan": "",
        "durum": "Bekliyor"
    })

    save_data(data)

    await update.message.reply_text("Sipariş oluşturuldu.")

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("tum", tum_siparisler))
    app.add_handler(CommandHandler("bekleyen", bekleyen))
    app.add_handler(CommandHandler("siparis", siparis_olustur))
    app.add_handler(CallbackQueryHandler(button))

    print("🚀 Sistem Stabil")
    app.run_polling()
