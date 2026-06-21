import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import *
from utils import parse_season_episode, get_button_text
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
            # Movie Title ကို ပြန်ယူမယ် (space ပါနိုင်လို့)
            movie_title = "_".join(data[:-2]) if len(data) > 2 else data[0]
            season = int(data[-2])
            episode = int(data[-1])
            
            # Movie Title ကို ပြန်ပြင်မယ် (ပုံမှန်)
            movie_title = movie_title.replace("_", " ")
            
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
            logger.error(f"Deep Link Error: {e}")
            await update.message.reply_text("❌ လင့်မှားနေပါတယ်။")
    else:
        await update.message.reply_text(
            "🎥 **ရုပ်ရှင် Bot မှ ကြိုဆိုပါတယ်။**\n\n"
            "📌 **အက်ဒမင်အတွက် ညွှန်ကြားချက်:**\n"
            "1️⃣ ပိုစတာ (ပုံ) ကို ပို့ပါ။\n"
            "2️⃣ ဇာတ်ညွှန်း (စာသား) ကို ပို့ပါ။\n"
            "3️⃣ Video တွေကို ဆက်တိုက်ပို့ပါ။ (Caption မှာ S01E01, s1e1, Season 1 Episode 1 စသဖြင့်)\n"
            "4️⃣ Video အကုန်ပို့ပြီးရင် `/done` နှိပ်ပါ။"
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
        "Caption ထဲမှာ `S01E01`, `s1e1`, `Season 1 Episode 1` စသဖြင့် ထည့်ပေးပါ။\n"
        "ဘယ်လိုပုံစံမဆို Bot က ကိုယ်တိုင်သိမယ်။"
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
    
    poster_file_id = context.user_data.get('temp_poster')
    synopsis = context.user_data.get('temp_synopsis')
    videos = context.user_data.get('temp_videos', [])
    
    if not poster_file_id or not synopsis:
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Poster နဲ့ Synopsis အရင်ပို့ပါ။")
        return
    
    if not videos:
        await update.message.reply_text("⚠️ အနည်းဆုံး တစ်ပုဒ်တော့ Video ပို့ပေးပါ။")
        return
    
    # Movie Title ကို ပထမ Video ရဲ့ Caption ကနေ ယူမယ်
    first_video = videos[0]
    movie_title = first_video['caption']
    
    await update.message.reply_text(f"⏳ Post ဆောက်နေပါတယ်... (Videos: {len(videos)})")
    
    # ---- Telegraph အတွက် ----
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
            # ---- Keyboard ဆောက်မယ် ----
            keyboard = []
            
            # Telegraph Button ရှိရင် ထည့်မယ်
            if telegraph_button:
                keyboard.append([telegraph_button])
            
            # Video Buttons (Deep Link)
            for ep in videos:
                safe_title = ep['caption'].replace(" ", "_").replace("/", "_").replace(":", "_")
                # Deep Link တည်ဆောက်မယ်
                deep_link = f"https://t.me/{context.bot.username}?start={safe_title}_{ep['season']}_{ep['episode']}"
                
                # Button Text - အတိုချုံးပြမယ်
                button_text = ep['button_text']
                
                button = InlineKeyboardButton(
                    text=button_text,
                    url=deep_link
                )
                keyboard.append([button])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # ဇာတ်ကားနာမည်ကို ပြမယ်
            display_title = movie_title[:50] + "..." if len(movie_title) > 50 else movie_title
            
            caption = f"🎬 **{display_title}**\n\n{synopsis_display}\n\n📥 ဇာတ်လမ်းကို ကြည့်ရန် အောက်ပါခလုတ်များကို နှိပ်ပါ။"
            
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=poster_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            episodes_list = [{"season": ep['season'], "episode": ep['episode']} for ep in videos]
            save_post_data(display_title, poster_file_id, synopsis, telegraph_url, episodes_list)
            
            await update.message.reply_text(f"✅ **Post ကို Channel ထဲမှာ အောင်မြင်စွာ တင်လိုက်ပါပြီ။**")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Post တင်ရာမှာ အမှားရှိသွားတယ်: {e}")
    else:
        await update.message.reply_text("ℹ️ CHANNEL_ID မထည့်ထားလို့ Post ကို ဒီမှာပဲ ပြပေးလိုက်မယ်။")
        await update.message.reply_text(f"🎬 {movie_title}\n\n{synopsis_display[:200]}...")
    
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
    
    await update.message.reply_text(
        "✅ ဇာတ်ညွှန်း သိမ်းဆည်းပြီးပါပြီ။\n\n"
        "📹 Video တွေ စတင်ပို့ပါ။\n"
        "Caption ထဲမှာ `S01E01`, `s1e1`, `Season 1 Episode 1` စသဖြင့် ထည့်ပေးပါ။\n"
        "ဘယ်လိုပုံစံမဆို Bot က ကိုယ်တိုင်သိမယ်။\n\n"
        "✅ အကုန်ပို့ပြီးရင် `/done` ကို နှိပ်ပါ။"
    )

# ---- Admin က Video ပို့တာ (စုဆောင်းမယ်) ----
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
        await update.message.reply_text("⚠️ Caption ထဲမှာ `S01E01` (သို့) `s1e1` ထည့်ပေးပါ။")
        return
    
    # ဒီ Video အတွက် Button Text ကို ပြင်ဆင်မယ်
    button_text = get_button_text(caption, season, episode)
    
    # Video ကို DB မှာ သိမ်းမယ်
    save_video_file(video.file_id, caption, season, episode, caption)
    
    # Video ကို List ထဲ သိမ်းမယ်
    if 'temp_videos' not in context.user_data:
        context.user_data['temp_videos'] = []
    
    context.user_data['temp_videos'].append({
        'file_id': video.file_id,
        'season': season,
        'episode': episode,
        'caption': caption,  # Full caption
        'button_text': button_text  # Button ပေါ်မှာပြမယ့်စာသား
    })
    
    total = len(context.user_data['temp_videos'])
    await update.message.reply_text(
        f"✅ Video #{total} သိမ်းဆည်းပြီးပါပြီ။\n"
        f"📺 Season {season} Episode {episode}\n"
        f"📝 {button_text[:50]}...\n\n"
        f"✅ ဆက်ပို့နိုင်ပါတယ်။ အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
    )

# ---- Main Function ----
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
