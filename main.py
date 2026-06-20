import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import *
from utils import parse_season_episode, extract_movie_title
from telegraph_helper import create_telegraph_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- ဖိုင်တွေကို ၅ မိနစ်အကြာမှာ ဖျက်ဖို့ စာရင်းသိမ်းမယ် ----
pending_deletions = {}  # {chat_id: [message_id1, message_id2, ...]}

async def delete_messages_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list, delay_seconds: int = 300):
    """၅ မိနစ်အကြာမှာ သတ်မှတ်ထားတဲ့ Message တွေကို ဖျက်မယ်"""
    await asyncio.sleep(delay_seconds)
    try:
        for msg_id in message_ids:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        logger.info(f"Deleted {len(message_ids)} messages in chat {chat_id} after {delay_seconds} seconds")
    except Exception as e:
        logger.error(f"Error deleting messages: {e}")

async def schedule_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list):
    """ဖျက်ဖို့ အချိန်ဇယားဆွဲမယ်"""
    if chat_id not in pending_deletions:
        pending_deletions[chat_id] = []
    pending_deletions[chat_id].extend(message_ids)
    
    # Task ကို Background မှာ Run မယ်
    asyncio.create_task(delete_messages_after_delay(context, chat_id, message_ids, 300))

# ---- Commands (မြန်မာလို) ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start - Bot ကိုစတင်ရန် """
    args = context.args
    if args:
        # Deep Link ကနေလာတာ (movie_title_season_episode)
        try:
            data = args[0].split('_')
            movie_title = data[0]
            season = int(data[1])
            episode = int(data[2])
            
            video_data = get_video_by_season_episode(movie_title, season, episode)
            if video_data:
                msg = await update.message.reply_video(
                    video=video_data['file_id'],
                    caption=f"🎬 **{movie_title}**\n📺 Season {season} Episode {episode}\n\n🍿 ကြည့်ရှု့ပါ။"
                )
                # Video နဲ့ Caption ကို ၅ မိနစ်အကြာမှာ ဖျက်မယ်
                await schedule_deletion(context, update.effective_chat.id, [msg.message_id])
            else:
                await update.message.reply_text("❌ ဒီ Episode အတွက် Video မတွေ့ပါ။")
        except Exception as e:
            await update.message.reply_text("❌ လင့်မှားနေပါတယ်။ ကျေးဇူးပြုပြီး ပြန်စစ်ပါ။")
    else:
        await update.message.reply_text(
            "🎥 **ရုပ်ရှင် Bot မှ ကြိုဆိုပါတယ်။**\n\n"
            "📌 **အက်ဒမင်အတွက် ညွှန်ကြားချက်:**\n"
            "1️⃣ Video ကို Caption ထဲမှာ `S01E01` ထည့်ပြီး ပို့ပါ။\n"
            "2️⃣ ပိုစတာ (ပုံ) ကို ပို့ပါ။\n"
            "3️⃣ ဇာတ်ညွှန်း (စာသား) ကို ပို့ပါ။\n"
            "➡️ Bot က Channel ထဲမှာ Post တစ်ခု အလိုအလျောက် တင်ပေးမယ်။\n\n"
            "📥 **အသုံးပြုသူများအတွက်:**\n"
            "Channel ထဲက ခလုတ်တွေကို နှိပ်ပြီး ဇာတ်လမ်းကို ကြည့်ပါ။"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /help - အကူအညီ """
    await update.message.reply_text(
        "🆘 **အကူအညီ**\n\n"
        "🤖 ဒီ Bot က ရုပ်ရှင်စီးရီးတွေကို Channel မှာ စနစ်တကျ ဖော်ပြပေးတဲ့ Bot ဖြစ်ပါတယ်။\n\n"
        "🔹 **အက်ဒမင် (Admin) အတွက်**\n"
        "• `/start` - Bot ကိုစတင်ရန်\n"
        "• `/help` - အကူအညီ\n"
        "• `/stats` - စာရင်းအင်းကြည့်ရန်\n\n"
        "📝 **Video တင်နည်း**\n"
        "Video ရဲ့ Caption ထဲမှာ `S01E01` (သို့) `Season 1 Episode 1` လို့ ထည့်ပေးပါ။\n\n"
        "📥 **အသုံးပြုသူများအတွက်**\n"
        "Channel ထဲက ခလုတ်တွေကို နှိပ်ပြီး ကြည့်ရှု့နိုင်ပါတယ်။\n"
        "ဗီဒီယိုကို ၅ မိနစ်အကြာမှာ အလိုအလျောက် ဖျက်ပေးမယ်။"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /stats - စာရင်းအင်းကြည့်ရန် (Admin အတွက်သာ) """
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ဒီ Command ကို Admin အတွက်သာ ခွင့်ပြုထားပါတယ်။")
        return
    
    total_movies = len(files_col.distinct("movie_title"))
    total_episodes = files_col.count_documents({})
    total_posts = posts_col.count_documents({})
    
    await update.message.reply_text(
        f"📊 **စာရင်းအင်း**\n\n"
        f"🎬 ဇာတ်ကားပေါင်း: {total_movies}\n"
        f"📺 Episode ပေါင်း: {total_episodes}\n"
        f"📝 Post ပေါင်း: {total_posts}"
    )

# ---- Admin က Video ပို့တာကိုင်တွယ်မယ် ----
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခင်ဗျားကို ခွင့်မပြုပါ။")
        return
    
    if not update.message.video:
        return
    
    video = update.message.video
    caption = update.message.caption or ""
    
    season, episode = parse_season_episode(caption)
    if not season or not episode:
        await update.message.reply_text("⚠️ Caption ထဲမှာ `S01E01` (သို့) `Season 1 Episode 1` ထည့်ပေးပါ။")
        return
    
    movie_title = extract_movie_title(caption)
    
    save_video_file(video.file_id, movie_title, season, episode, caption)
    
    await update.message.reply_text(
        f"✅ **Video သိမ်းဆည်းပြီးပါပြီ။**\n"
        f"🎬 ဇာတ်ကား: {movie_title}\n"
        f"📺 Season {season} Episode {episode}"
    )
    
    context.user_data['temp_movie'] = movie_title

# ---- Admin က Poster ပို့တာကိုင်တွယ်မယ် ----
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if not context.user_data.get('temp_movie'):
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Video အရင်ပို့ပါ။")
        return
    
    photo = update.message.photo[-1]
    context.user_data['temp_poster'] = photo.file_id
    await update.message.reply_text("✅ ပိုစတာ သိမ်းဆည်းပြီးပါပြီ။ ဇာတ်ညွှန်း (စာသား) ကို ပို့ပါ။")

# ---- Admin က Synopsis ပို့တာကိုင်တွယ်မယ် ----
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    movie_title = context.user_data.get('temp_movie')
    poster_file_id = context.user_data.get('temp_poster')
    
    if not movie_title or not poster_file_id:
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Video နဲ့ ပိုစတာ အရင်ပို့ပါ။")
        return
    
    synopsis = update.message.text
    telegraph_url = None
    
    if len(synopsis) > 1024:
        await update.message.reply_text("⏳ ဇာတ်ညွှန်းရှည်လွန်းလို့ Telegraph မှာ တင်နေပါတယ်...")
        telegraph_url = create_telegraph_page(f"{movie_title} - ဇာတ်ညွှန်း", synopsis)
        if telegraph_url:
            synopsis_display = f"ဇာတ်ညွှန်းအပြည့်အစုံကို အောက်ပါလင့်မှာ ဖတ်ပါ။\n{telegraph_url}"
        else:
            synopsis_display = synopsis[:1024] + "... (Telegraph အမှားဖြစ်နေပါတယ်)"
    else:
        synopsis_display = synopsis
    
    episodes = get_all_episodes(movie_title)
    if not episodes:
        await update.message.reply_text("⚠️ ဒီ ဇာတ်ကားအတွက် Episode တစ်ခုမှ မတွေ့ပါ။ Video အရင်ပို့ပါ။")
        return
    
    if CHANNEL_ID:
        try:
            keyboard = []
            for ep in episodes:
                safe_title = movie_title.replace(" ", "_")
                cb_data = f"{safe_title}|{ep['season']}|{ep['episode']}"
                button = InlineKeyboardButton(
                    text=f"Season {ep['season']} Episode {ep['episode']}",
                    callback_data=cb_data
                )
                keyboard.append([button])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            caption = f"🎬 **{movie_title}**\n\n{synopsis_display}\n\n📥 ဇာတ်လမ်းကို ကြည့်ရန် အောက်ပါခလုတ်များကို နှိပ်ပါ။"
            
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=poster_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            episodes_list = [{"season": ep['season'], "episode": ep['episode']} for ep in episodes]
            save_post_data(movie_title, poster_file_id, synopsis, telegraph_url, episodes_list)
            
            await update.message.reply_text(f"✅ **Post ကို Channel ထဲမှာ အောင်မြင်စွာ တင်လိုက်ပါပြီ။**")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Channel မှာ Post တင်ရာမှာ အမှားရှိသွားတယ်: {e}")
    else:
        await update.message.reply_text("ℹ️ CHANNEL_ID မထည့်ထားလို့ Post ကို ဒီမှာပဲ ပြပေးလိုက်မယ်။")
        await update.message.reply_text(f"🎬 {movie_title}\n\n{synopsis_display[:200]}...")
    
    context.user_data.clear()

# ---- User တွေ Button နှိပ်ရင် Video ပို့မယ် ----
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('|')
    if len(data) != 3:
        await query.edit_message_text("❌ တောင်းဆိုချက်မှားနေပါတယ်။")
        return
    
    movie_title = data[0].replace("_", " ")
    season = int(data[1])
    episode = int(data[2])
    
    video_data = get_video_by_season_episode(movie_title, season, episode)
    
    if video_data:
        msg = await query.message.reply_video(
            video=video_data['file_id'],
            caption=f"🎬 **{movie_title}**\n📺 Season {season} Episode {episode}\n\n🍿 ကြည့်ရှု့ပါ။"
        )
        # ၅ မိနစ်အကြာမှာ ဖျက်မယ်
        await schedule_deletion(context, query.message.chat_id, [msg.message_id])
    else:
        await query.message.reply_text("❌ ဒီ Episode အတွက် Video မတွေ့ပါ။")

# ---- Main Function (PTB 22.x အတွက် ပြင်ဆင်ထားတယ်) ----
def main():
    # PTB 22.x မှာ event loop ကို အလိုအလျောက် စီမံပေးတယ်
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commands (မြန်မာလို)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
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
