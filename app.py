import os
import json
from telegram import *
from telegram.ext import *

TOKEN = "8229950774:AAGO63nQ_NfYnznbO8a4Qm_B-cCOGxESvQM"
ADMIN_ID = 8452588697

DATA_FILE = "data.json"

def load():
    if not os.path.exists(DATA_FILE):
        return {
            "kuryeler": {},
            "isletmeler": {},
            "bolgeler": [],
            "siparisler": []
        }
    with open(DATA_FILE) as f:
        return json.load(f)

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(db, f)

db = load()

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid == str(ADMIN_ID):
        keyboard = [
            ["➕ Kurye Ekle", "➕ İşletme Ekle"],
            ["🗺 Bölge Ekle", "📋 Tüm Siparişler"]
        ]
        await update.message.reply_text("👑 ADMIN PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if uid in db["kuryeler"]:
        keyboard = [
            ["📥 Bekleyenler", "📦 Aldıklarım"],
            ["🔎 Fiş Sorgu", "🚪 Çıkış"]
        ]
        await update.message.reply_text("🚚 KURYE PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if uid in db["isletmeler"]:
        keyboard = [
            ["📦 Sipariş Oluştur"],
            ["📋 Siparişlerim"],
            ["🔎 Fiş Sorgu"]
        ]
        await update.message.reply_text("🏪 İŞLETME PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    await update.message.reply_text("⛔ Yetkin yok.")

# ---------------- KURYE BEKLEYEN ----------------

async def bekleyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    bolgeler = db["kuryeler"][uid]["bolgeler"]

    for s in db["siparisler"]:
        if s["durum"] == "Bekliyor" and s["bolge"] in bolgeler:

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 Al", callback_data=f"al_{s['id']}")]
            ])

            await update.message.reply_photo(
                s["foto"],
                caption=f"📦 {s['id']}\n📍 {s['bolge']}\n🏪 {s['isletme']}",
                reply_markup=kb
            )

# ---------------- CALLBACK ----------------

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)

    if q.data.startswith("al_"):
        sid = int(q.data.split("_")[1])

        for s in db["siparisler"]:
            if s["id"] == sid and s["durum"] == "Bekliyor":
                s["durum"] = "Alındı"
                s["alan"] = uid
                save()

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 Teslim Ettim", callback_data=f"teslim_{sid}")]
                ])
                await q.edit_message_reply_markup(reply_markup=kb)

    if q.data.startswith("teslim_"):
        sid = int(q.data.split("_")[1])

        for s in db["siparisler"]:
            if s["id"] == sid and s["alan"] == uid:
                s["durum"] = "Teslim"
                save()

                await context.bot.send_message(
                    chat_id=int(s["isletme_id"]),
                    text=f"✅ {sid} nolu sipariş teslim edildi."
                )

                await q.edit_message_reply_markup(reply_markup=None)

# ---------------- FOTO ----------------

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in db["isletmeler"]:
        return

    bolge = db["isletmeler"][uid]["bolge"]

    aktif = False
    for k in db["kuryeler"].values():
        if bolge in k["bolgeler"]:
            aktif = True

    if not aktif:
        await update.message.reply_text("⚠️ Bu bölgede kurye yok!")
        return

    file_id = update.message.photo[-1].file_id
    sid = len(db["siparisler"]) + 1

    db["siparisler"].append({
        "id": sid,
        "bolge": bolge,
        "isletme": db["isletmeler"][uid]["isim"],
        "isletme_id": uid,
        "foto": file_id,
        "durum": "Bekliyor",
        "alan": ""
    })

    save()

    await update.message.reply_text("✅ Sipariş oluşturuldu.")

# ---------------- TEXT ----------------

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text

    if t == "📥 Bekleyenler":
        await bekleyen(update, context)

    if t == "📋 Tüm Siparişler":
        for s in db["siparisler"]:
            await update.message.reply_text(
                f"📦 {s['id']} | {s['bolge']} | {s['durum']}"
            )

# ---------------- MAIN ----------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, text))
app.add_handler(MessageHandler(filters.PHOTO, photo))
app.add_handler(CallbackQueryHandler(callback))

print("🚀 TESLİMAT SİSTEMİ PRO AKTİF")
app.run_polling()
