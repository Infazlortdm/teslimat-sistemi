import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "8229950774:AAGO63nQ_NfYnznbO8a4Qm_B-cCOGxESvQM"
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

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id == str(ADMIN_ID):
        keyboard = [["➕ Kurye Ekle", "➕ İşletme Ekle"],
                    ["🗺 Bölge Ekle", "📋 Tüm Siparişler"]]
        await update.message.reply_text(
            "👑 Admin Paneli",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    if user_id in data["kuryeler"]:
        keyboard = [["📥 Bekleyenler", "📦 Aldıklarım"],
                    ["🔎 Fiş Sorgu", "🚪 Çıkış"]]
        await update.message.reply_text(
            "🚚 Kurye Paneli",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    if user_id in data["isletmeler"]:
        keyboard = [["📦 Sipariş Oluştur"],
                    ["🔎 Fiş Sorgu"]]
        await update.message.reply_text(
            "🏪 İşletme Paneli",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    await update.message.reply_text("⛔ Yetkin yok.")

# ---------------- BEKLEYEN ----------------

async def bekleyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in data["kuryeler"]:
        return

    bolgeler = data["kuryeler"][user_id]["bolgeler"]

    for s in data["siparisler"]:
        if s["durum"] == "Bekliyor" and s["bolge"] in bolgeler:

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 Al", callback_data=f"al_{s['id']}")]
            ])

            await update.message.reply_photo(
                s["foto"],
                caption=f"📦 {s['id']}\n📍 {s['bolge']}\n🏪 {s['isletme']}",
                reply_markup=keyboard
            )

# ---------------- CALLBACK ----------------

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data.startswith("al_"):
        siparis_id = int(query.data.split("_")[1])

        for s in data["siparisler"]:
            if s["id"] == siparis_id:
                s["durum"] = "Alındı"
                s["alan"] = user_id
                save_data()

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 Teslim Ettim", callback_data=f"teslim_{siparis_id}")]
                ])

                await query.edit_message_reply_markup(reply_markup=keyboard)

    if query.data.startswith("teslim_"):
        siparis_id = int(query.data.split("_")[1])

        for s in data["siparisler"]:
            if s["id"] == siparis_id:
                s["durum"] = "Teslim"
                save_data()

                await context.bot.send_message(
                    chat_id=int(s["isletme_id"]),
                    text=f"✅ {siparis_id} nolu sipariş teslim edildi."
                )

                await query.edit_message_reply_markup(reply_markup=None)

# ---------------- TEXT HANDLER ----------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)

    # Kurye bekleyen
    if text == "📥 Bekleyenler":
        await bekleyen(update, context)

    # Admin tüm sipariş
    if text == "📋 Tüm Siparişler":
        for s in data["siparisler"]:
            await update.message.reply_text(
                f"📦 {s['id']} | {s['bolge']} | {s['durum']}"
            )

# ---------------- PHOTO ----------------

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in data["isletmeler"]:
        return

    bolge = data["isletmeler"][user_id]["bolge"]

    aktif = False
    for k in data["kuryeler"].values():
        if bolge in k["bolgeler"]:
            aktif = True

    if not aktif:
        await update.message.reply_text("⚠️ Bu bölgede atanmış kurye yok!")
        return

    file_id = update.message.photo[-1].file_id

    siparis_id = len(data["siparisler"]) + 1

    data["siparisler"].append({
        "id": siparis_id,
        "bolge": bolge,
        "isletme": data["isletmeler"][user_id]["isim"],
        "isletme_id": user_id,
        "foto": file_id,
        "durum": "Bekliyor",
        "alan": ""
    })

    save_data()

    await update.message.reply_text("✅ Sipariş oluşturuldu.")

# ---------------- MAIN ----------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, text_handler))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(CallbackQueryHandler(button))

print("🚀 TESLİMAT SİSTEMİ AKTİF")
app.run_polling()
