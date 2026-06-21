import os
import logging
import secrets
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import create_deep_linked_url
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import save_file_data, get_file_by_deep_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_USERNAME = None

# ---- Helper Functions ----
def generate_payload():
    """Deep Link အတွက် Payload ထုတ်မယ်"""
    return secrets.token_urlsafe(12)

# ---- Commands ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start ကို ကိုင်တွယ်မယ် (Deep Link ပါလာရင်လည်း) """
    user_id = update.effective_user.id
    args = context.args  # Deep Link ရဲ့ payload ကို ယူမယ်
    
    # ---- Deep Link ကနေ လာတာ (args ရှိရင်) ----
    if args:
        payload = args[0]
        deep_link = f"https://t.me/{context.bot.username}?start={payload}"
        
        logger.info(f"🔗 Deep Link clicked: {deep_link}")
        
        # Database ကနေ ရှာမယ်
        file_data = get_file_by_deep_link(deep_link)
        
        if file_data:
            file_id = file_data.get("file_id")
            file_name = file_data.get("file_name", "File")
            caption = file_data.get("caption", "")
            file_type = file_data.get("file_type", "")
            
            try:
                if file_type == "Video":
                    sent_msg = await update.message.reply_video(
                        video=file_id,
                        caption=f"🎬 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Document":
                    sent_msg = await update.message.reply_document(
                        document=file_id,
                        caption=f"📄 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Audio":
                    sent_msg = await update.message.reply_audio(
                        audio=file_id,
                        caption=f"🎵 **{file_name}**\n\n📝 {caption}"
                    )
                elif file_type == "Photo":
                    sent_msg = await update.message.reply_photo(
                        photo=file_id,
                        caption=f"🖼️ **{file_name}**\n\n📝 {caption}"
                    )
                else:
                    sent_msg = await update.message.reply_document(
                        document=file_id,
                        caption=f"📁 **{file_name}**\n\n📝 {caption}"
                    )
                
                # ဖိုင်ပို့ပြီးရင် သတိပေးစာ (Channel တွေ အတွက်)
                warning_text = (
                    "⚠️ ⚠️ ⚠️ အရေးကြီးပါတယ် ⚠️ ⚠️ ⚠️\n\n"
                    "👉ဤရုပ်ရှင်ဖိုင်များ/ဗီဒီယိုများကို 5 မိနစ်အတွင်း (မူပိုင်ခွင့်ပြဿနာများကြောင့်) ဖျက်ပါမည်။\n"
                    "👉ကျေးဇူးပြု၍ ဤဖိုင်များ/ဗီဒီယိုများအားလုံးကို သင်၏ Saved Messages များသို့ Forward လုပ်ပြီး ထိုနေရာတွင် ဇာတ်ကားအား ကြည့်ရှုပါ။\n"
                    "👉ကျွန်ုပ်၏ Channel ကို လာရောက်အားပေးမှုအတွက် ကျေးဇူးအထူးတင်ပါတယ် 🙏🙏🙏\n"
                    "👉Channel ရေရှည်တည်တံ့ဖို့အတွက် Support ပေးချင်ပါက Wave Pay (09767011991) ကို ကူညီနိုင်ပါတယ်။\n"
                    "👉Channel ကို Share ခြင်းဖြင့်လည်း ကူညီနိုင်ပါတယ်။\n"
                    "👉အားလုံးကို ကျေးဇူးတင်ပါတယ်။"
                )
                keyboard = [
                    [InlineKeyboardButton("🎬 Movie Channel", url="https://t.me/moviesandseriesforallwzn")],
                    [InlineKeyboardButton("🔞 Adult Channel", url="https://t.me/everyboyhobby")],
                    [InlineKeyboardButton("🎵 Music Channel", url="https://t.me/wznmusiclibary")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                warn_msg = await context.bot.send_message(chat_id=user_id, text=warning_text, reply_markup=reply_markup)
                
                # ၅ မိနစ်အကြာမှာ ဖျက်မယ်
                asyncio.create_task(delete_messages_after_delay(context, user_id, [sent_msg.message_id, warn_msg.message_id], 300))
                
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
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    else:
        await update.message.reply_text("⚠️ ဒီဖိုင်အမျိုးအစားကို မထောက်ပံ့ပါ။")
        return
    
    # Caption မပါရင် ဖိုင်နာမည်ကိုပဲ သုံးမယ်
    if not caption:
        caption = file_name
    
    # ---- Deep Link ထုတ်မယ် (secrets ကို သုံးမယ်) ----
    global BOT_USERNAME
    BOT_USERNAME = context.bot.username
    payload = generate_payload()
    deep_link = create_deep_linked_url(BOT_USERNAME, payload)
    
    # Database မှာ သိမ်းမယ် (payload ကို deep_link နေရာမှာ သိမ်းမယ်)
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
        "Photo": "🖼️"
    }.get(file_type, "📁")
    
    # Deep Link ကို ပြန်ပို့မယ်
    reply_text = (
        f"🔗 **Deep Link အဆင်သင့်ဖြစ်ပါပြီ။**\n\n"
        f"{deep_link}\n\n"
        f"📁 **ဖိုင်အချက်အလက်:**\n"
        f"{type_emoji} {file_name}\n"
        f"📝 Caption: {caption}\n\n"
        f"{db_status}\n\n"
        f"💡 **သုံးစွဲသူများအတွက်:**\n"
        f"ဒီ Link ကို **နှိပ်လိုက်ရင်** ဖိုင်ကို Bot က ပြန်ပို့ပေးမယ်။"
    )
    
    await update.message.reply_text(reply_text, parse_mode='Markdown')

# ---- Auto-delete helper ----
async def delete_messages_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list, delay_seconds: int = 300):
    import asyncio
    await asyncio.sleep(delay_seconds)
    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            logger.info(f"Auto-deleted message {msg_id}")
        except Exception as e:
            logger.warning(f"Failed to delete {msg_id}: {e}")

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
        handle_file_upload
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
