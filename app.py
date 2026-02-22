import sqlite3
import logging
from telegram import *
from telegram.ext import *

TOKEN = "8229950774:AAGO63nQ_NfYnznbO8a4Qm_B-cCOGxESvQM"
ADMIN_ID = 8452588697

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("veritabani.db", check_same_thread=False)
cursor = conn.cursor()

# ---------------- VERİTABANI ----------------

cursor.execute("CREATE TABLE IF NOT EXISTS bolgeler(id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT UNIQUE)")
cursor.execute("CREATE TABLE IF NOT EXISTS kuryeler(id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS kurye_bolgeler(kurye_id INTEGER, bolge_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS isletmeler(id INTEGER PRIMARY KEY, ad TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS isletme_bolgeler(isletme_id INTEGER, bolge_id INTEGER)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS siparisler(
id INTEGER PRIMARY KEY AUTOINCREMENT,
isletme_id INTEGER,
bolge_id INTEGER,
kurye_id INTEGER,
foto TEXT,
durum TEXT DEFAULT 'Bekliyor')
""")
conn.commit()

# ---------------- YARDIMCI ----------------

def rol(user_id):
    if user_id == ADMIN_ID:
        return "admin"
    cursor.execute("SELECT * FROM kuryeler WHERE id=?", (user_id,))
    if cursor.fetchone():
        return "kurye"
    cursor.execute("SELECT * FROM isletmeler WHERE id=?", (user_id,))
    if cursor.fetchone():
        return "isletme"
    return None

def en_az_yogun_kurye(bolge_id):
    cursor.execute("""
    SELECT kuryeler.id, COUNT(siparisler.id) as toplam
    FROM kuryeler
    JOIN kurye_bolgeler ON kuryeler.id = kurye_bolgeler.kurye_id
    LEFT JOIN siparisler ON siparisler.kurye_id = kuryeler.id AND siparisler.durum != 'Teslim Edildi'
    WHERE kurye_bolgeler.bolge_id = ?
    GROUP BY kuryeler.id
    ORDER BY toplam ASC
    LIMIT 1
    """, (bolge_id,))
    sonuc = cursor.fetchone()
    return sonuc[0] if sonuc else None

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    r = rol(user_id)

    if r == "admin":
        keyboard = [
            ["🗺 Bölge Ekle", "👤 Kurye Ekle"],
            ["🏪 İşletme Ekle", "📦 Tüm Siparişler"]
        ]
        await update.message.reply_text("👑 YÖNETİCİ PANELİ",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif r == "kurye":
        keyboard = [["📥 Aktif Siparişlerim", "📊 Performansım"]]
        await update.message.reply_text("🚚 KURYE PANELİ",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif r == "isletme":
        keyboard = [["📦 Yeni Sipariş", "📋 Siparişlerim"]]
        await update.message.reply_text("🏪 İŞLETME PANELİ",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    else:
        await update.message.reply_text("❌ Sistemde kayıtlı değilsiniz.")

# ---------------- MESAJ ----------------

async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    r = rol(user_id)

    # -------- ADMIN --------
    if r == "admin":

        if text == "🗺 Bölge Ekle":
            context.user_data["bolge_ekle"] = True
            await update.message.reply_text("Bölge adını yazınız:")
            return

        if context.user_data.get("bolge_ekle"):
            try:
                cursor.execute("INSERT INTO bolgeler(ad) VALUES(?)", (text,))
                conn.commit()
                await update.message.reply_text("✅ Bölge eklendi.")
            except:
                await update.message.reply_text("⚠️ Bu bölge zaten var.")
            context.user_data["bolge_ekle"] = False
            return

        if text == "👤 Kurye Ekle":
            context.user_data["kurye_ekle"] = True
            await update.message.reply_text("Kurye Telegram ID yaz:")
            return

        if context.user_data.get("kurye_ekle"):
            try:
                cursor.execute("INSERT INTO kuryeler(id) VALUES(?)", (int(text),))
                conn.commit()
                await update.message.reply_text("✅ Kurye eklendi.")
            except:
                await update.message.reply_text("⚠️ Hatalı veya zaten var.")
            context.user_data["kurye_ekle"] = False
            return

        if text == "🏪 İşletme Ekle":
            context.user_data["isletme_ekle"] = True
            await update.message.reply_text("İşletme Telegram ID yaz:")
            return

        if context.user_data.get("isletme_ekle"):
            try:
                cursor.execute("INSERT INTO isletmeler(id,ad) VALUES(?,?)",
                               (int(text), "İşletme"))
                conn.commit()
                await update.message.reply_text("✅ İşletme eklendi.")
            except:
                await update.message.reply_text("⚠️ Hatalı veya zaten var.")
            context.user_data["isletme_ekle"] = False
            return

    # -------- İŞLETME --------
    if r == "isletme":

        if text == "📦 Yeni Sipariş":
            cursor.execute("""
            SELECT bolgeler.id, bolgeler.ad
            FROM bolgeler
            JOIN isletme_bolgeler ON bolgeler.id = isletme_bolgeler.bolge_id
            WHERE isletme_bolgeler.isletme_id=?
            """, (user_id,))
            bolgeler = cursor.fetchall()

            if not bolgeler:
                await update.message.reply_text("Bu işletmeye bölge atanmamış.")
                return

            keyboard = [[InlineKeyboardButton(b[1], callback_data=f"bolge_{b[0]}")] for b in bolgeler]
            await update.message.reply_text("Sipariş hangi bölge?",
                reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if text == "📋 Siparişlerim":
            cursor.execute("SELECT id,durum FROM siparisler WHERE isletme_id=?", (user_id,))
            rows = cursor.fetchall()
            if rows:
                msg = "\n".join([f"#{r[0]} - {r[1]}" for r in rows])
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text("Sipariş yok.")
            return

    # -------- KURYE --------
    if r == "kurye":

        if text == "📥 Aktif Siparişlerim":
            cursor.execute("SELECT id,durum FROM siparisler WHERE kurye_id=? AND durum!='Teslim Edildi'", (user_id,))
            rows = cursor.fetchall()
            if rows:
                msg = "\n".join([f"#{r[0]} - {r[1]}" for r in rows])
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text("Aktif sipariş yok.")
            return

        if text == "📊 Performansım":
            cursor.execute("SELECT COUNT(*) FROM siparisler WHERE kurye_id=?", (user_id,))
            toplam = cursor.fetchone()[0]
            await update.message.reply_text(f"Toplam aldığınız sipariş: {toplam}")
            return

# ---------------- FOTO ----------------

async def foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "secilen_bolge" not in context.user_data:
        return

    user_id = update.effective_user.id
    bolge_id = context.user_data["secilen_bolge"]
    foto_id = update.message.photo[-1].file_id

    kurye = en_az_yogun_kurye(bolge_id)

    if not kurye:
        await update.message.reply_text("⚠️ Bu bölgede kurye yok.")
        return

    cursor.execute("""
    INSERT INTO siparisler(isletme_id,bolge_id,kurye_id,foto)
    VALUES(?,?,?,?)
    """, (user_id, bolge_id, kurye, foto_id))
    conn.commit()

    siparis_id = cursor.lastrowid

    await update.message.reply_text(f"✅ Sipariş #{siparis_id} oluşturuldu.")

    await context.bot.send_photo(
        chat_id=kurye,
        photo=foto_id,
        caption=f"📦 Yeni Sipariş #{siparis_id}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Siparişi Aldım", callback_data=f"al_{siparis_id}")]
        ])
    )

    del context.user_data["secilen_bolge"]

# ---------------- BUTON ----------------

async def buton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("bolge_"):
        bolge_id = int(data.split("_")[1])
        context.user_data["secilen_bolge"] = bolge_id
        await query.edit_message_text("📸 Fiş fotoğrafını gönderiniz.")
        return

    if data.startswith("al_"):
        siparis_id = int(data.split("_")[1])
        cursor.execute("UPDATE siparisler SET durum='Kurye Aldı' WHERE id=?", (siparis_id,))
        conn.commit()

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Teslim Ettim", callback_data=f"teslim_{siparis_id}")]
            ])
        )
        return

    if data.startswith("teslim_"):
        siparis_id = int(data.split("_")[1])
        cursor.execute("UPDATE siparisler SET durum='Teslim Edildi' WHERE id=?", (siparis_id,))
        conn.commit()

        cursor.execute("SELECT isletme_id FROM siparisler WHERE id=?", (siparis_id,))
        isletme_id = cursor.fetchone()[0]

        await context.bot.send_message(isletme_id,
                                       f"✅ Sipariş #{siparis_id} teslim edildi.")

        await query.edit_message_text(f"✅ Sipariş #{siparis_id} teslim edildi.")

# ---------------- MAIN ----------------

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj))
app.add_handler(MessageHandler(filters.PHOTO, foto))
app.add_handler(CallbackQueryHandler(buton))

print("Bot aktif.")
app.run_polling()
