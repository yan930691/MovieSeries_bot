import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import *
from utils import parse_season_episode, extract_movie_title, extract_episode_name
from telegraph_helper import create_telegraph_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- ဖိုင်တွေကို ၅ မိနစ်အကြာမှာ ဖျက်ဖို့ ----
async def delete_messages_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list, delay_seconds: int = 300):
    await asyncio.sleep(delay_seconds)
    try:
        for msg_id in message_ids:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        logger.info(f"Deleted {len(message_ids)} messages in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error deleting messages: {e}")

async def schedule_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list):
    asyncio.create_task(delete_messages_after_delay(context, chat_id, message_ids, 300))

# ---- Commands ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
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
                await schedule_deletion(context, update.effective_chat.id, [msg.message_id])
            else:
                await update.message.reply_text("❌ ဒီ Episode အတွက် Video မတွေ့ပါ။")
        except Exception as e:
            await update.message.reply_text("❌ လင့်မှားနေပါတယ်။")
    else:
        await update.message.reply_text(
            "🎥 **ရုပ်ရှင် Bot မှ ကြိုဆိုပါတယ်။**\n\n"
            "📌 **အက်ဒမင်အတွက် ညွှန်ကြားချက်:**\n"
            "1️⃣ ပိုစတာ (ပုံ) ကို ပို့ပါ။\n"
            "2️⃣ ဇာတ်ညွှန်း (စာသား) ကို ပို့ပါ။\n"
            "3️⃣ Video တွေကို ဆက်တိုက်ပို့ပါ။ (Caption မှာ S01E01 ထည့်ပါ)\n"
            "4️⃣ Video အကုန်ပို့ပြီးရင် `/done` နှိပ်ပါ။"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **အကူအညီ**\n\n"
        "• `/start` - Bot ကိုစတင်ရန်\n"
        "• `/help` - အကူအညီ\n"
        "• `/done` - Video အကုန်ပို့ပြီးရင် Post ဆောက်ရန်\n"
        "• `/cancel` - လုပ်နေတာကိုဖျက်ရန်"
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    context.user_data.clear()
    await update.message.reply_text("✅ လုပ်ဆောင်နေတာကို ဖျက်လိုက်ပါပြီ။")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    movie_title = context.user_data.get('temp_movie')
    poster_file_id = context.user_data.get('temp_poster')
    synopsis = context.user_data.get('temp_synopsis')
    
    if not movie_title or not poster_file_id or not synopsis:
        await update.message.reply_text("⚠️ Poster, Synopsis, Video တွေ အရင်ပို့ပါ။")
        return
    
    # DB ကနေ Video အကုန်ယူမယ်
    episodes = get_all_episodes(movie_title)
    
    if not episodes:
        await update.message.reply_text("⚠️ ဒီ Movie အတွက် Video မတွေ့ပါ။ Video တွေပြန်ပို့ပါ။")
        return
    
    await update.message.reply_text(f"⏳ Post ဆောက်နေပါတယ်... (Videos: {len(episodes)})")
    
    # ---- Telegraph ----
    telegraph_url = None
    telegraph_button = None
    
    if len(synopsis) > 1024:
        telegraph_url = create_telegraph_page(f"{movie_title} - ဇာတ်ညွှန်း", synopsis)
        if telegraph_url:
            synopsis_display = "ဇာတ်ညွှန်းရှည်လွန်းလို့ Telegraph မှာ တင်ထားပါတယ်။"
            telegraph_button = InlineKeyboardButton(
                text="📖 ဇာတ်ညွှန်းအပြည့်အစုံဖတ်ရန်",
                url=telegraph_url
            )
        else:
            synopsis_display = synopsis[:1024] + "..."
    else:
        synopsis_display = synopsis
    
    if CHANNEL_ID:
        try:
            keyboard = []
            
            if telegraph_button:
                keyboard.append([telegraph_button])
            
            for ep in episodes:
                safe_title = movie_title.replace(" ", "_")
                deep_link = f"https://t.me/{context.bot.username}?start={safe_title}_{ep['season']}_{ep['episode']}"
                
                ep_name = extract_episode_name(ep['caption']) or f"Episode {ep['episode']}"
                
                button = InlineKeyboardButton(
                    text=ep_name,
                    url=deep_link
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
            await update.message.reply_text(f"❌ Post တင်ရာမှာ အမှားရှိသွားတယ်: {e}")
    else:
        await update.message.reply_text("ℹ️ CHANNEL_ID မထည့်ထားလို့ Post ကို ဒီမှာပဲ ပြပေးလိုက်မယ်။")
        await update.message.reply_text(f"🎬 {movie_title}\n\n{synopsis_display[:200]}...")
    
    context.user_data.clear()

# ---- Admin Handlers ----
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    photo = update.message.photo[-1]
    context.user_data['temp_poster'] = photo.file_id
    
    await update.message.reply_text("✅ ပိုစတာ သိမ်းဆည်းပြီးပါပြီ။ ဇာတ်ညွှန်း (စာသား) ကို ပို့ပါ။")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if not context.user_data.get('temp_poster'):
        await update.message.reply_text("⚠️ Poster အရင်ပို့ပါ။")
        return
    
    synopsis = update.message.text
    context.user_data['temp_synopsis'] = synopsis
    
    await update.message.reply_text(
        "✅ ဇာတ်ညွှန်း သိမ်းဆည်းပြီးပါပြီ။\n\n"
        "📹 Video တွေ စတင်ပို့ပါ။\n"
        "Caption ထဲမှာ `S01E01` ထည့်ပေးပါ။\n\n"
        "✅ အကုန်ပို့ပြီးရင် `/done` နှိပ်ပါ။"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    if not context.user_data.get('temp_poster') or not context.user_data.get('temp_synopsis'):
        await update.message.reply_text("⚠️ Poster နဲ့ Synopsis အရင်ပို့ပါ။")
        return
    
    if not update.message.video:
        return
    
    video = update.message.video
    caption = update.message.caption or ""
    
    season, episode = parse_season_episode(caption)
    if not season or not episode:
        await update.message.reply_text("⚠️ Caption ထဲမှာ `S01E01` ထည့်ပေးပါ။")
        return
    
    movie_title = extract_movie_title(caption)
    
    if 'temp_movie' not in context.user_data:
        context.user_data['temp_movie'] = movie_title
    elif context.user_data['temp_movie'] != movie_title:
        await update.message.reply_text(
            f"ℹ️ Movie Title ပြောင်းသွားပါတယ်။\n"
            f"အဟောင်း: `{context.user_data['temp_movie']}`\n"
            f"အသစ်: `{movie_title}`\n\n"
            f"ဒီ Title အသစ်အတွက် ဆက်သိမ်းမယ်။"
        )
        context.user_data['temp_movie'] = movie_title
    
    save_video_file(video.file_id, movie_title, season, episode, caption)
    
    total = len(get_all_episodes(movie_title))
    
    await update.message.reply_text(
        f"✅ Video #{total} သိမ်းဆည်းပြီးပါပြီ။\n"
        f"🎬 {movie_title}\n"
        f"📺 Season {season} Episode {episode}\n\n"
        f"✅ ဆက်ပို့နိုင်ပါတယ်။ အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
    )

# ---- Main ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
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
