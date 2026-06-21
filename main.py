import os
import logging
import re
import hashlib
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, RENDER_URL
from database import save_file_data, get_file_by_deep_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_USERNAME = None

# ---- Helper Functions ----
def generate_deep_link(file_name, caption):
    """ဖိုင်နာမည်နဲ့ Caption ကိုကြည့်ပြီး Deep Link ထုတ်ပေးမယ်"""
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', file_name)[:30]
    hash_id = hashlib.md5(f"{file_name}_{caption}_{datetime.utcnow().timestamp()}".encode()).hexdigest()[:12]
    return f"https://t.me/{BOT_USERNAME}?start={hash_id}"

# ---- Commands ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start ကို ကိုင်တွယ်မယ် (Deep Link ပါလာရင်လည်း) """
    user_id = update.effective_user.id
    args = context.args  # Deep Link ရဲ့ parameter ကို ယူမယ်
    
    # ---- Deep Link ကနေ လာတာ ----
    if args:
        link_id = args[0]
        deep_link = f"https://t.me/{context.bot.username}?start={link_id}"
        
        # Database ကနေ ရှာမယ်
        file_data = get_file_by_deep_link(deep_link)
        
        if file_data:
            file_id = file_data.get("file_id")
            file_name = file_data.get("file_name", "File")
            caption = file_data.get("caption", "")
            file_type = file_data.get("file_type", "")
            
            try:
                if file_type == "Video":
                    await update.message.reply_video(
                        video=file_id,
                        caption=f"🎬 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Document":
                    await update.message.reply_document(
                        document=file_id,
                        caption=f"📄 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Audio":
                    await update.message.reply_audio(
                        audio=file_id,
                        caption=f"🎵 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Photo":
                    await update.message.reply_photo(
                        photo=file_id,
                        caption=f"🖼️ **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Animation":
                    await update.message.reply_animation(
                        animation=file_id,
                        caption=f"🎞️ **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Sticker":
                    await update.message.reply_sticker(sticker=file_id)
                elif file_type == "Voice":
                    await update.message.reply_voice(
                        voice=file_id,
                        caption=f"🎤 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "VideoNote":
                    await update.message.reply_video_note(video_note=file_id)
                else:
                    await update.message.reply_document(
                        document=file_id,
                        caption=f"📁 **{file_name}**\n\n📝 {caption}"
                    )
                return
            except Exception as e:
                await update.message.reply_text(f"❌ ဖိုင်ကို ပြန်ပို့ရာမှာ အမှားရှိသွားတယ်: {e}")
                return
        
        # မတွေ့ရင်
        await update.message.reply_text(
            "❌ ဒီ Link အတွက် ဖိုင်ကို ရှာမတွေ့ပါ။\n"
            "Link က သက်တမ်းကုန်သွားတာ (သို့) မှားနေတာ ဖြစ်နိုင်ပါတယ်။"
        )
        return
    
    # ---- Admin အတွက် /start (Deep Link မပါရင်) ----
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "🔗 Deep Link မှ ကြိုဆိုပါတယ်။\n"
            "ကျေးဇူးပြုပြီး တရားဝင် Link ကို သုံးပါ။"
        )
        return
    
    await update.message.reply_text(
        "🔗 **Deep Link Generator Bot**\n\n"
        "📌 **ညွှန်ကြားချက်:**\n"
        "1️⃣ ဘယ်ဖိုင်မဆို (Video, Document, Audio, Photo) ပို့ပါ။\n"
        "2️⃣ Bot က Deep Link ကို အလိုအလျောက် ထုတ်ပေးမယ်။\n"
        "3️⃣ Caption မပါရင်လည်း ဖိုင်နာမည်ကိုသုံးပြီး ထုတ်ပေးမယ်။\n\n"
        "📝 **ဥပမာ:**\n"
        "ဖိုင်ပို့လိုက်ရင် → `https://t.me/Bot?start=abc123...`"
    )

# ---- ဖိုင်တွေကို ကိုင်တွယ်မယ် ----
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    # ---- ဖိုင်ကို စစ်ဆေးမယ် ----
    file_obj = None
    file_name = None
    file_id = None
    file_type = None
    caption = update.message.caption or ""
    
    if update.message.video:
        file_obj = update.message.video
        file_name = file_obj.file_name or f"Video_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Video"
    elif update.message.document:
        file_obj = update.message.document
        file_name = file_obj.file_name or f"Document_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Document"
    elif update.message.audio:
        file_obj = update.message.audio
        file_name = file_obj.file_name or f"Audio_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Audio"
    elif update.message.photo:
        file_obj = update.message.photo[-1]
        file_name = f"Photo_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Photo"
    elif update.message.animation:
        file_obj = update.message.animation
        file_name = file_obj.file_name or f"Animation_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Animation"
    elif update.message.sticker:
        file_obj = update.message.sticker
        file_name = f"Sticker_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Sticker"
    elif update.message.voice:
        file_obj = update.message.voice
        file_name = f"Voice_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "Voice"
    elif update.message.video_note:
        file_obj = update.message.video_note
        file_name = f"VideoNote_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_type = "VideoNote"
    else:
        await update.message.reply_text("⚠️ ဒီဖိုင်အမျိုးအစားကို မထောက်ပံ့ပါ။")
        return
    
    # Caption မပါရင် ဖိုင်နာမည်ကိုပဲ သုံးမယ်
    if not caption:
        caption = file_name
    
    # ---- Deep Link ထုတ်မယ် ----
    global BOT_USERNAME
    BOT_USERNAME = context.bot.username
    deep_link = generate_deep_link(file_name, caption)
    
    # Database မှာ သိမ်းမယ်
    try:
        save_file_data(file_id, file_name, caption, deep_link, file_type)
        db_status = "💾 Database မှာလည်း သိမ်းဆည်းထားပါတယ်။"
    except Exception as e:
        logger.error(f"Database Save Error: {e}")
        db_status = "⚠️ Database မှာ သိမ်းရာမှာ အဆင်မပြေပေမယ့် Link က ရှိနေပါတယ်။"
    
    # ---- ဖိုင်အမျိုးအစား Emoji ----
    type_emoji = {
        "Video": "🎬",
        "Document": "📄",
        "Audio": "🎵",
        "Photo": "🖼️",
        "Animation": "🎞️",
        "Sticker": "🏷️",
        "Voice": "🎤",
        "VideoNote": "📹"
    }.get(file_type, "📁")
    
    # Deep Link ကို ပြန်ပို့မယ်
    reply_text = (
        f"🔗 **Deep Link အဆင်သင့်ဖြစ်ပါပြီ။**\n\n"
        f"`{deep_link}`\n\n"
        f"📁 **ဖိုင်အချက်အလက်:**\n"
        f"{type_emoji} {file_name}\n"
        f"📝 Caption: {caption}\n\n"
        f"{db_status}\n\n"
        f"💡 **သုံးစွဲသူများအတွက်:**\n"
        f"ဒီ Link ကို **နှိပ်လိုက်ရင်** ဖိုင်ကို Bot က ပြန်ပို့ပေးမယ်။"
    )
    
    await update.message.reply_text(reply_text, parse_mode='Markdown')

# ---- Main ----
def main():
    global BOT_USERNAME
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    BOT_USERNAME = None
    
    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    
    # Message Handlers (အားလုံးကို ဖမ်းမယ်)
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        handle_file
    ))
    
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting webhook on port {port}")
    
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
