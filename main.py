import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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
        # Deep Link: movie_title_season_episode
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
            "3️⃣ Video တွေကို Caption ထဲမှာ `S01E01` ထည့်ပြီး ပို့ပါ။ (အကုန်ပို့ပြီးရင် /done နှိပ်ပါ)\n"
            "4️⃣ `/done` နှိပ်ပြီးရင် Bot က Post တစ်ခုတည်း ဆောက်ပေးမယ်။"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **အကူအညီ**\n\n"
        "📌 **အက်ဒမင်အတွက်:**\n"
        "• `/start` - Bot ကိုစတင်ရန်\n"
        "• `/help` - အကူအညီ\n"
        "• `/done` - Video အကုန်ပို့ပြီးရင် Post ဆောက်ရန်\n"
        "• `/cancel` - လုပ်နေတာကိုဖျက်ရန်\n\n"
        "📝 **Video တင်နည်း**\n"
        "Caption ထဲမှာ `S01E01` ထည့်ပါ။\n"
        "ဥပမာ - `Game of Thrones S01E01`"
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    context.user_data.clear()
    await update.message.reply_text("✅ လုပ်ဆောင်နေတာကို ဖျက်လိုက်ပါပြီ။")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /done - Video အကုန်ပို့ပြီးရင် Post ဆောက်မယ် """
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    movie_title = context.user_data.get('temp_movie')
    poster_file_id = context.user_data.get('temp_poster')
    synopsis = context.user_data.get('temp_synopsis')
    videos = context.user_data.get('temp_videos', [])
    
    if not movie_title or not poster_file_id or not synopsis:
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Poster, Synopsis, Video တွေ အရင်ပို့ပါ။")
        return
    
    if not videos:
        await update.message.reply_text("⚠️ အနည်းဆုံး တစ်ပုဒ်တော့ Video ပို့ပေးပါ။")
        return
    
    # ---- Post ဆောက်မယ် ----
    await update.message.reply_text("⏳ Post ဆောက်နေပါတယ်...")
    
    # Telegraph အတွက်
    telegraph_url = None
    if len(synopsis) > 1024:
        telegraph_url = create_telegraph_page(f"{movie_title} - ဇာတ်ညွှန်း", synopsis)
        if telegraph_url:
            synopsis_display = f"ဇာတ်ညွှန်းအပြည့်အစုံကို အောက်ပါလင့်မှာ ဖတ်ပါ။\n{telegraph_url}"
        else:
            synopsis_display = synopsis[:1024] + "..."
    else:
        synopsis_display = synopsis
    
    if CHANNEL_ID:
        try:
            # Deep Link Buttons ဆောက်မယ်
            keyboard = []
            for ep in videos:
                safe_title = movie_title.replace(" ", "_")
                # Deep Link: t.me/Bot?start=movie_title_season_episode
                deep_link = f"https://t.me/{context.bot.username}?start={safe_title}_{ep['season']}_{ep['episode']}"
                button = InlineKeyboardButton(
                    text=ep['caption'],
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
            
            # Post Data သိမ်း
            episodes_list = [{"season": ep['season'], "episode": ep['episode']} for ep in videos]
            save_post_data(movie_title, poster_file_id, synopsis, telegraph_url, episodes_list)
            
            await update.message.reply_text(f"✅ **Post ကို Channel ထဲမှာ အောင်မြင်စွာ တင်လိုက်ပါပြီ။**")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Post တင်ရာမှာ အမှားရှိသွားတယ်: {e}")
    else:
        await update.message.reply_text("ℹ️ CHANNEL_ID မထည့်ထားလို့ Post ကို ဒီမှာပဲ ပြပေးလိုက်မယ်။")
        await update.message.reply_text(f"🎬 {movie_title}\n\n{synopsis_display[:200]}...")
    
    # Temporary Data ရှင်း
    context.user_data.clear()

# ---- Admin က Poster ပို့တာ ----
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    photo = update.message.photo[-1]
    context.user_data['temp_poster'] = photo.file_id
    await update.message.reply_text("✅ ပိုစတာ သိမ်းဆည်းပြီးပါပြီ။ ဇာတ်ညွှန်း (စာသား) ကို ပို့ပါ။")

# ---- Admin က Synopsis ပို့တာ ----
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if not context.user_data.get('temp_poster'):
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Poster အရင်ပို့ပါ။")
        return
    
    synopsis = update.message.text
    context.user_data['temp_synopsis'] = synopsis
    
    await update.message.reply_text("✅ ဇာတ်ညွှန်း သိမ်းဆည်းပြီးပါပြီ။\n\n📹 Video တွေ စတင်ပို့ပါ။\nCaption ထဲမှာ `S01E01` ထည့်ပေးပါ။\n\n✅ အကုန်ပို့ပြီးရင် `/done` ကို နှိပ်ပါ။")

# ---- Admin က Video ပို့တာ (တစ်ပုဒ်ချင်းစီ) ----
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    if not context.user_data.get('temp_poster') or not context.user_data.get('temp_synopsis'):
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Poster နဲ့ Synopsis အရင်ပို့ပါ။")
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
    episode_name = extract_episode_name(caption)
    
    # Movie Title ကို သိမ်းမယ်
    context.user_data['temp_movie'] = movie_title
    
    # Video ကို DB မှာ သိမ်းမယ်
    save_video_file(video.file_id, movie_title, season, episode, caption)
    
    # Video ကို List ထဲ သိမ်းမယ်
    if 'temp_videos' not in context.user_data:
        context.user_data['temp_videos'] = []
    
    context.user_data['temp_videos'].append({
        'file_id': video.file_id,
        'season': season,
        'episode': episode,
        'caption': episode_name
    })
    
    await update.message.reply_text(
        f"✅ Video {len(context.user_data['temp_videos'])} သိမ်းဆည်းပြီးပါပြီ။\n"
        f"🎬 {movie_title}\n"
        f"📺 Season {season} Episode {episode}\n"
        f"📝 {episode_name}\n\n"
        f"✅ ဆက်ပို့နိုင်ပါတယ်။ အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
    )

# ---- Media Group (တစ်ခါတည်း ဖိုင်များများပို့တာ) ကို ကိုင်တွယ်မယ် ----
async def handle_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if not context.user_data.get('temp_poster') or not context.user_data.get('temp_synopsis'):
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Poster နဲ့ Synopsis အရင်ပို့ပါ။")
        return
    
    if not update.message.media_group_id:
        return
    
    # Media Group ထဲက Video တွေကို process လုပ်မယ်
    for media_item in update.message.media_group:
        if isinstance(media_item, dict) and media_item.get('type') == 'video':
            # ဒီနေရာမှာ media_item က video file object ဖြစ်မယ်
            # ဒါပေမယ့် media_group ကို သီးခြား handler မှာ ကိုင်တွယ်ရတာ ပိုလွယ်တယ်
            # ဒီအတွက် message object ကို သုံးမယ်
            pass
    
    # အလွယ်ဆုံးနည်းက media group ကို သီးခြားစီ process မလုပ်ဘဲ
    # အစား handle_video ကို ပြန်သုံးမယ် (ဒါပေမယ့် group အတွက် သီးခြားရေးတာ ပိုကောင်း)
    await update.message.reply_text("📹 Media Group ကို လက်ခံရရှိပါပြီ။ Video တွေကို တစ်ပုဒ်ချင်းစီ process လုပ်နေပါတယ်...")
    
    # ဒီနေရာမှာ media group ထဲက video တွေကို ဆွဲထုတ်ပြီး process လုပ်ဖို့ လိုတယ်
    # ဒါပေမယ့် PTB မှာ media group အတွက် built-in handler မရှိသေးဘူး
    # ဒါကြောင့် ဒီနေရာမှာ အလွယ်ဆုံးနည်းက တစ်ပုဒ်ချင်းစီ ပို့ဖို့ ပြောတာပဲ

    await update.message.reply_text(
        "⚠️ Media Group (တစ်ခါတည်း ဖိုင်များများပို့တာ) ကို မထောက်ပံ့သေးပါ။\n"
        "ကျေးဇူးပြုပြီး **တစ်ပုဒ်ချင်းစီ** ပို့ပေးပါ။\n\n"
        "သို့မဟုတ် အောက်ပါအတိုင်း ပို့နိုင်ပါတယ်:\n"
        "1. Video 1 ကို ပို့ပါ\n"
        "2. Video 2 ကို ပို့ပါ\n"
        "3. ... စသည်ဖြင့်\n"
        "4. အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
    )

# ---- Main Function ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # Media Group အတွက် (ဒါပေမယ့် PTB က မထောက်ပံ့သေးဘူး)
    # app.add_handler(MessageHandler(filters.MEDIA_GROUP, handle_media_group))
    
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
