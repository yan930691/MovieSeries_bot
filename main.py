import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import *
from utils import parse_season_episode, extract_movie_title
from telegraph_helper import create_telegraph_page

# Logging ဖွင့်ထားပါ (Render မှာ အလုပ်လုပ်တာမြင်ရမယ်)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Temporary Storage (Admin ရဲ့ အဆင့်လိုက် Input တွေကို သိမ်းမယ်) ---
# user_data ကို context.user_data နဲ့ သုံးမယ်

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ကို /start နှိပ်ရင် ဒီဟာ အလုပ်လုပ်မယ် (Deep Link အတွက်ပါ)"""
    args = context.args
    if args:
        # Deep Link ကနေ လာတာ (t.me/Bot?start=Movie_Title_S1_E1)
        try:
            data = args[0].split('_')
            movie_title = data[0]
            season = int(data[1])
            episode = int(data[2])
            
            video_data = get_video_by_season_episode(movie_title, season, episode)
            if video_data:
                await update.message.reply_video(
                    video=video_data['file_id'],
                    caption=f"🎬 {movie_title}\n📺 Season {season} Episode {episode}\n\nEnjoy watching!"
                )
            else:
                await update.message.reply_text("Sorry, this episode is not found.")
        except:
            await update.message.reply_text("Invalid link.")
    else:
        await update.message.reply_text(
            "🎥 Welcome to Movie Bot!\n\n"
            "🔹 Admin အတွက်:\n"
            "1. Video ကို Caption ထဲမှာ S01E01 ထည့်ပြီး ပို့ပါ။\n"
            "2. Poster (ပုံ) ကို ပို့ပါ။\n"
            "3. Synopsis (ဇာတ်ညွှန်း) ကို စာသားအနေနဲ့ ပို့ပါ။\n"
            "➡️ Bot က Channel ထဲမှာ Post တစ်ခု အလိုအလျောက် တင်ပေးမယ်။"
        )

# ---- ၁။ Admin က Video ပို့တဲ့အခါ ----
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ပို့လိုက်တဲ့ Video ကို လက်ခံပြီး DB မှာ သိမ်းမယ်"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    if not update.message.video:
        return
    
    video = update.message.video
    caption = update.message.caption or ""
    
    # Season/Episode ခွဲထုတ်
    season, episode = parse_season_episode(caption)
    if not season or not episode:
        await update.message.reply_text("⚠️ Caption ထဲမှာ S01E01 (သို့) Season 1 Episode 1 ထည့်ပေးပါ။")
        return
    
    movie_title = extract_movie_title(caption)
    
    # DB မှာ သိမ်း
    save_video_file(video.file_id, movie_title, season, episode, caption)
    
    # Admin ကို အတည်ပြုပြန်ကြား
    await update.message.reply_text(
        f"✅ Video Saved!\n"
        f"🎬 Movie: {movie_title}\n"
        f"📺 Season {season} Episode {episode}"
    )
    
    # ဒီ Movie အတွက် Poster နဲ့ Synopsis ကို စောင့်နေဖို့ သိမ်းထား
    context.user_data['temp_movie'] = movie_title

# ---- ၂။ Admin က Poster (ပုံ) ပို့တဲ့အခါ ----
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if not context.user_data.get('temp_movie'):
        await update.message.reply_text("⚠️ ပထမဆုံး Video အရင်ပို့ပါ။")
        return
    
    photo = update.message.photo[-1]  # အရည်အသွေးအမြင့်ဆုံးပုံ
    context.user_data['temp_poster'] = photo.file_id
    await update.message.reply_text("✅ Poster saved! ခု Synopsis (စာသား) ကို ပို့ပါ။")

# ---- ၃။ Admin က Synopsis (စာသား) ပို့တဲ့အခါ ----
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    movie_title = context.user_data.get('temp_movie')
    poster_file_id = context.user_data.get('temp_poster')
    
    if not movie_title or not poster_file_id:
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး Video နဲ့ Poster အရင်ပို့ပါ။")
        return
    
    synopsis = update.message.text
    telegraph_url = None
    
    # Synopsis ရှည်လားစစ်
    if len(synopsis) > 1024:
        await update.message.reply_text("⏳ Synopsis ရှည်လွန်းလို့ Telegraph မှာ တင်နေပါတယ်...")
        telegraph_url = create_telegraph_page(f"{movie_title} - Synopsis", synopsis)
        if telegraph_url:
            synopsis_display = f"Synopsis အပြည့်အစုံကို အောက်ပါလင့်မှာ ဖတ်ပါ။\n{telegraph_url}"
        else:
            synopsis_display = synopsis[:1024] + "... (Telegraph error)"
    else:
        synopsis_display = synopsis
    
    # Episode အားလုံးကို DB ကနေ ဆွဲထုတ်
    episodes = get_all_episodes(movie_title)
    if not episodes:
        await update.message.reply_text("⚠️ ဒီ Movie အတွက် Episode တစ်ခုမှ မတွေ့ပါ။ Video အရင်ပို့ပါ။")
        return
    
    # ---- Channel မှာ Post တင်မယ် ----
    if CHANNEL_ID:
        try:
            # Keyboard (Buttons) တွေ ဆောက်မယ်
            keyboard = []
            for ep in episodes:
                # Callback data ကို အတိုလေး သိမ်းမယ် (64 bytes ထဲဆံ့အောင်)
                # ပုံစံ: movie_title|S|E  (ဥပမာ: Walking_Dead|1|2)
                safe_title = movie_title.replace(" ", "_")
                cb_data = f"{safe_title}|{ep['season']}|{ep['episode']}"
                button = InlineKeyboardButton(
                    text=f"Season {ep['season']} Episode {ep['episode']}",
                    callback_data=cb_data
                )
                keyboard.append([button])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Caption ဆောက်မယ်
            caption = f"🎬 **{movie_title}**\n\n{synopsis_display}\n\n📥 ဇာတ်လမ်းကို ကြည့်ရန် အောက်ပါခလုတ်များကို နှိပ်ပါ။"
            
            # Channel ကို Photo နဲ့တကွ ပို့မယ်
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=poster_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # DB မှာ Post Data သိမ်း
            episodes_list = [{"season": ep['season'], "episode": ep['episode']} for ep in episodes]
            save_post_data(movie_title, poster_file_id, synopsis, telegraph_url, episodes_list)
            
            await update.message.reply_text(f"✅ Post ကို Channel ထဲမှာ အောင်မြင်စွာ တင်လိုက်ပါပြီ။")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Channel မှာ Post တင်ရာမှာ အမှားရှိသွားတယ်: {e}")
    else:
        await update.message.reply_text("ℹ️ CHANNEL_ID မထည့်ထားလို့ Post ကို ဒီမှာပဲ ပြပေးလိုက်မယ်။")
        # ဒီနေရာမှာ Admin ဆီကိုပဲ ပြန်ပို့ပေးလို့ရတယ် (စမ်းသပ်ရန်)
        await update.message.reply_text(f"Movie: {movie_title}\nSynopsis: {synopsis_display[:200]}...")
    
    # Temporary Data ရှင်းထုတ်
    context.user_data.clear()

# ---- ၄။ User တွေ Button နှိပ်ရင် Video ပြန်ပို့မယ် ----
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Loading ပျောက်အောင်
    
    data = query.data.split('|')
    if len(data) != 3:
        await query.edit_message_text("Invalid request.")
        return
    
    movie_title = data[0].replace("_", " ")
    season = int(data[1])
    episode = int(data[2])
    
    video_data = get_video_by_season_episode(movie_title, season, episode)
    
    if video_data:
        # User ကို Video ပြန်ပို့မယ် (ဒါမှမဟုတ် Channel မှာ Inline ပြန်ပို့မယ်)
        await query.message.reply_video(
            video=video_data['file_id'],
            caption=f"🎬 {movie_title}\n📺 Season {season} Episode {episode}\n\nEnjoy!"
        )
    else:
        await query.message.reply_text("❌ ဒီ Episode အတွက် Video မတွေ့ပါ။")

# ---- Main Function (Webhook စတင်ရန်) ----
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handler တွေ ထည့်မယ်
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Webhook စတင်မယ်
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
