import os
import logging
import secrets
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import create_deep_linked_url
from pymongo import MongoClient
import asyncio
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------- MongoDB ----------
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    logger.error("MONGO_URI not set")
    exit(1)

client = MongoClient(
    MONGO_URI,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=3000,
    connectTimeoutMS=3000,
    socketTimeoutMS=3000
)
db = client["file_share_bot"]
files_col = db["files"]

def save_file(payload, file_id, file_name):
    files_col.update_one({"payload": payload}, {"$set": {"file_id": file_id, "file_name": file_name}}, upsert=True)

def get_file(payload):
    doc = files_col.find_one({"payload": payload})
    if doc:
        return doc["file_id"], doc["file_name"]
    return None, None

def generate_payload():
    return secrets.token_urlsafe(12)

# ---------- Telegraph ----------
async def create_telegraph_page(title, content):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.telegra.ph/createPage",
                json={
                    "access_token": os.environ.get("TELEGRAPH_TOKEN", ""),
                    "title": title,
                    "content": f"<p>{content.replace(chr(10), '<br>')}</p>",
                    "author_name": "Movie Bot"
                }
            ) as response:
                data = await response.json()
                if data.get("ok"):
                    return data["result"]["url"]
    except Exception as e:
        logger.error(f"Telegraph error: {e}")
    return None

# ---------- Telegram Config ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN not set")
    exit(1)

BOT_USERNAME = os.environ.get("BOT_USERNAME", "").strip()
if BOT_USERNAME.startswith("@"):
    BOT_USERNAME = BOT_USERNAME[1:]

ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_ID", "").split(",") if x.strip()]

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ---------- Start Command ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        if is_admin(user_id):
            await update.message.reply_text(
                "🎬 **Admin Panel**\n\n"
                "/post - ပိုစတာဖန်တီးရန်\n"
                "📝 ဇာတ်ညွှန်းရှည်ရင် Telegraph မှာ တင်ပေးမယ်"
            )
        else:
            await update.message.reply_text("🔗 Deep Link ကို နှိပ်ပါ။")
        return
    
    payload = args[0]
    file_id, file_name = get_file(payload)
    
    if not file_id:
        await update.message.reply_text("❌ လင့်ခ် သက်တမ်းကုန်သွားပါပြီ။")
        return
    
    try:
        if file_name and file_name.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            await update.message.reply_video(video=file_id, caption=f"🎬 {file_name}")
        elif file_name and file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            await update.message.reply_photo(photo=file_id, caption=f"🖼️ {file_name}")
        else:
            await update.message.reply_document(document=file_id, filename=file_name or "file")
        
        logger.info(f"✅ File sent to {user_id}: {file_name}")
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text(f"❌ ဖိုင်ပို့ရာတွင် အမှားရှိသည်: {e}")

# ---------- File Upload ----------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ အဒ်မင်များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    message = update.message
    file_obj = None
    file_name = None
    
    if message.video:
        file_obj = message.video
        file_name = file_obj.file_name or "video.mp4"
    elif message.document:
        file_obj = message.document
        file_name = file_obj.file_name or "document"
    elif message.photo:
        file_obj = message.photo[-1]
        file_name = "photo.jpg"
    else:
        return
    
    payload = generate_payload()
    save_file(payload, file_obj.file_id, file_name)
    deep_link = create_deep_linked_url(BOT_USERNAME, payload)
    
    await update.message.reply_text(
        f"🔗 **Deep Link အဆင်သင့်ဖြစ်ပါပြီ။**\n\n"
        f"{deep_link}\n\n"
        f"📁 {file_name}"
    )

# ---------- Post Creator ----------
async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ အဒ်မင်များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    await update.message.reply_text(
        "🎬 **Post Creator**\n\n"
        "1️⃣ ပိုစတာ (ပုံ) ပို့ပါ။\n"
        "2️⃣ ဇာတ်ညွှန်း (စာသား) ပို့ပါ။\n"
        "   - စာသားရှည်ရင် Telegraph မှာ တင်ပေးမယ်\n"
        "3️⃣ ရုပ်ရှင်ဖိုင် (Video) ပို့ပါ။\n\n"
        "Bot က Deep Link ကို အလိုအလျောက် ထုတ်ပေးမယ်။"
    )

# ---------- Flask Webhook ----------
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.error("WEBHOOK_URL not set")
    exit(1)

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("post", post_command))
telegram_app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL | filters.PHOTO, handle_file))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, telegram_app.bot)
        telegram_app.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "error", 500

# ---------- Main ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
