import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from telegraph_helper import create_telegraph_page
from database import save_post_data, get_all_posts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Helper Functions ----
def extract_season_episode_from_caption(caption):
    """Caption ထဲက S01E12 ကို ထုတ်ယူမယ်"""
    if not caption:
        return None, None
    
    patterns = [
        r'(?:S|Season)\s*(\d+)\s*(?:E|Episode)\s*(\d+)',
        r's(\d+)e(\d+)',
        r'(\d+)x(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    return None, None

def extract_movie_title(caption):
    """Caption ထဲက ဇာတ်ကားနာမည်ကို ထုတ်ယူမယ်"""
    if not caption:
        return "Movie"
    
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'\(\d{4}\)', '', cleaned)
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(MPK|MKV|MP4|AVI|x264|x265|HEVC)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned or "Movie"

def extract_deep_link_and_caption(text):
    """
    ခင်ဗျားပို့တဲ့ မက်ဆေ့ချ်ကနေ Deep Link နဲ့ Caption ကို ခွဲထုတ်မယ်
    ပုံစံ:
    🔗 သင်၏ Deep Link အဆင်သင့်ဖြစ်ပါပြီ။
    
    https://t.me/WZNmoviefilsend_bot?start=oWA-ex7me6BDcZTb
    
    The Wire (2002) - S01E12 - Cleaning Up 1080p MPK.mp4
    """
    if not text:
        return None, None
    
    # URL ကို ရှာမယ်
    url_pattern = r'https://t\.me/[^\s]+'
    url_match = re.search(url_pattern, text)
    
    if not url_match:
        return None, None
    
    deep_link = url_match.group(0)
    
    # URL ပြီးရင် ကျန်တဲ့ စာသားကို Caption အဖြစ် ယူမယ်
    url_end = url_match.end()
    caption = text[url_end:].strip()
    
    # ပထမဆုံး စာကြောင်းကို Caption အဖြစ် ယူမယ် (ဗွီဒီယိုနာမည်)
    if caption:
        lines = caption.split('\n')
        caption = lines[0].strip()
    
    return deep_link, caption

# ---- Command Handlers ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    posts_count = len(get_all_posts(limit=100))
    
    await update.message.reply_text(
        f"🎬 **Button Creator Bot**\n\n"
        f"📊 သိမ်းဆည်းထားတဲ့ Post ပေါင်း: {posts_count}\n\n"
        "📌 **ညွှန်ကြားချက်:**\n"
        "1️⃣ `/post` နှိပ်ပြီး Post အသစ်စတင်ပါ။\n"
        "2️⃣ Poster (ပုံ) → Caption (စာသား) ပို့ပါ။\n"
        "3️⃣ `/1`, `/2`, `/3` ... နှိပ်ပြီး Season ရွေးပါ။\n"
        "4️⃣ Deep Link တွေ ဆက်တိုက်ပို့ပါ။\n"
        "5️⃣ Season ပြီးရင် `1`, `2`, `3` ... နှိပ်ပါ။\n"
        "6️⃣ အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
    )

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    context.user_data.clear()
    context.user_data['step'] = 'waiting_poster'
    await update.message.reply_text("🖼️ Poster (ပုံ) ကို ပို့ပါ။")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    poster = context.user_data.get('temp_poster')
    caption_text = context.user_data.get('temp_caption')
    seasons = context.user_data.get('temp_seasons', {})
    
    if not poster:
        await update.message.reply_text("⚠️ Poster (ပုံ) အရင်ပို့ပါ။ `/post` နဲ့ ပြန်စပါ။")
        return
    
    if not caption_text:
        await update.message.reply_text("⚠️ Caption (စာသား) အရင်ပို့ပါ။ `/post` နဲ့ ပြန်စပါ။")
        return
    
    if not seasons:
        await update.message.reply_text("⚠️ အနည်းဆုံး Season တစ်ခုတော့ ထည့်ပေးပါ။")
        return
    
    total_episodes = sum(len(links) for links in seasons.values())
    await update.message.reply_text(f"⏳ Post ဆောက်နေပါတယ်... (Seasons: {len(seasons)}, Episodes: {total_episodes})")
    
    # ---- Telegraph (Caption ရှည်ရင်) ----
    telegraph_url = None
    telegraph_button = None
    
    if len(caption_text) > 1024:
        telegraph_url = create_telegraph_page("📖 ဇာတ်ညွှန်း", caption_text)
        if telegraph_url:
            telegraph_button = InlineKeyboardButton(
                text="📖 ဇာတ်ညွှန်းအပြည့်အစုံဖတ်ရန်",
                url=telegraph_url
            )
            caption_display = ""
        else:
            caption_display = caption_text[:1024] + "..."
    else:
        caption_display = caption_text
    
    try:
        keyboard = []
        
        if telegraph_button:
            keyboard.append([telegraph_button])
        
        for season_num in sorted(seasons.keys(), key=int):
            season_links = seasons[season_num]
            season_links_sorted = sorted(season_links, key=lambda x: x.get('episode', 0))
            
            keyboard.append([InlineKeyboardButton(f"🎬 Season {season_num} (Episodes: {len(season_links_sorted)})", callback_data="none")])
            
            for link_data in season_links_sorted:
                button_text = link_data['text']
                button_url = link_data['url']
                keyboard.append([InlineKeyboardButton(button_text, url=button_url)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if caption_display:
            final_caption = f"🎬 **{caption_display}**\n\n📥 အောက်ပါခလုတ်များကို နှိပ်ပြီး ကြည့်ရှု့ပါ။"
        else:
            final_caption = f"📥 အောက်ပါခလုတ်များကို နှိပ်ပြီး ကြည့်ရှု့ပါ။"
        
        sent_msg = await update.message.reply_photo(
            photo=poster,
            caption=final_caption,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        try:
            save_post_data(poster, caption_text, seasons, telegraph_url)
            await update.message.reply_text(
                f"✅ **Post ကို သင့်ဆီကိုပဲ ပို့လိုက်ပါပြီ။**\n"
                f"📊 Season {len(seasons)} ခု၊ Episode {total_episodes} ခု ပါဝင်ပါတယ်။\n"
                f"💾 Database မှာလည်း သိမ်းဆည်းထားပါတယ်။\n\n"
                f"💡 Channel မှာ ပြန်တင်ချင်ရင် ဒီ Post ကို Forward လုပ်ပါ။"
            )
        except Exception as db_error:
            logger.error(f"Database Save Error: {db_error}")
            await update.message.reply_text(
                f"✅ **Post ကို သင့်ဆီကိုပဲ ပို့လိုက်ပါပြီ။**\n"
                f"📊 Season {len(seasons)} ခု၊ Episode {total_episodes} ခု ပါဝင်ပါတယ်။\n"
                f"⚠️ Database မှာ သိမ်းရာမှာ အဆင်မပြေပေမယ့် Post က ရှိနေပါတယ်။"
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Post တင်ရာမှာ အမှားရှိသွားတယ်: {e}")
    
    context.user_data.clear()

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    context.user_data.clear()
    await update.message.reply_text("✅ လုပ်ဆောင်နေတာကို ဖျက်လိုက်ပါပြီ။")

# ---- Season Command Handlers ----
async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    command_text = update.message.text
    season_num = command_text.replace('/', '').strip()
    
    if not season_num.isdigit():
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး `/1`, `/2`, `/3` ပုံစံသုံးပါ။")
        return
    
    if not context.user_data.get('temp_poster'):
        await update.message.reply_text("⚠️ Poster (ပုံ) အရင်ပို့ပါ။ `/post` နဲ့ ပြန်စပါ။")
        return
    
    if not context.user_data.get('temp_caption'):
        await update.message.reply_text("⚠️ Caption (စာသား) အရင်ပို့ပါ။ `/post` နဲ့ ပြန်စပါ။")
        return
    
    context.user_data['current_season'] = season_num
    context.user_data['step'] = f'adding_links_season_{season_num}'
    
    await update.message.reply_text(
        f"✅ **Season {season_num}** အတွက် အဆင်သင့်ဖြစ်ပါပြီ။\n\n"
        f"🔗 Deep Link တွေ စတင်ပို့ပါ။\n"
        f"ပုံစံ: (ခင်ဗျား ပို့နေကျအတိုင်း)\n"
        f"```\n🔗 သင်၏ Deep Link အဆင်သင့်ဖြစ်ပါပြီ။\n\nhttps://t.me/Bot?start=xxx\n\nThe Wire - S01E01 - Title.mp4\n```\n\n"
        f"✅ Season {season_num} ပြီးရင် `{season_num}` လို့ ရိုက်ပါ။"
    )

# ---- Handlers ----
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    step = context.user_data.get('step')
    
    if step != 'waiting_poster':
        await update.message.reply_text("⚠️ ကျေးဇူးပြုပြီး `/post` နဲ့ အရင်စတင်ပါ။")
        return
    
    photo = update.message.photo[-1]
    context.user_data['temp_poster'] = photo.file_id
    context.user_data['step'] = 'waiting_caption'
    await update.message.reply_text("✅ ပိုစတာ သိမ်းဆည်းပြီးပါပြီ။ Caption (စာသား) ကို ပို့ပါ။")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    text = update.message.text.strip()
    
    if text.startswith('/'):
        return
    
    step = context.user_data.get('step')
    
    # ---- Caption စောင့်နေတယ် ----
    if step == 'waiting_caption':
        context.user_data['temp_caption'] = text
        context.user_data['step'] = 'waiting_season'
        await update.message.reply_text(
            "✅ Caption သိမ်းဆည်းပြီးပါပြီ။\n\n"
            "📌 Season ရွေးပါ။\n"
            "• `/1` - Season 1\n"
            "• `/2` - Season 2\n"
            "• `/3` - Season 3\n"
            "• ... စသဖြင့်\n\n"
            "✅ Season ပြီးရင် သက်ဆိုင်ရာ နံပါတ်ကို ရိုက်ပါ။"
        )
        return
    
    # ---- Season Done ----
    if text.isdigit() and step and step.startswith('adding_links_season_'):
        season_num = text
        current_season = context.user_data.get('current_season')
        
        if not current_season:
            await update.message.reply_text("⚠️ Season မရွေးရသေးပါ။ `/1`, `/2` နဲ့ အရင်ရွေးပါ။")
            return
        
        if current_season != season_num:
            await update.message.reply_text(
                f"⚠️ သင်က Season {current_season} အတွက် လုပ်နေပါတယ်။\n"
                f"Season {season_num} ကို ပြီးကြောင်း အသိပေးချင်ရင် `/{season_num}` နဲ့ အရင်ရွေးပါ။"
            )
            return
        
        if 'temp_seasons' not in context.user_data:
            context.user_data['temp_seasons'] = {}
        
        if season_num not in context.user_data['temp_seasons']:
            await update.message.reply_text(f"⚠️ Season {season_num} အတွက် Link တစ်ခုမှ မတွေ့ပါ။")
            return
        
        link_count = len(context.user_data['temp_seasons'][season_num])
        await update.message.reply_text(
            f"✅ **Season {season_num}** ပြီးပါပြီ။\n"
            f"📝 Link {link_count} ခု သိမ်းဆည်းထားပါတယ်။\n\n"
            f"📌 နောက် Season အတွက် `/2`, `/3` နှိပ်ပါ။\n"
            f"📌 အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
        )
        
        context.user_data['current_season'] = None
        context.user_data['step'] = 'waiting_season'
        return
    
    # ---- Deep Link တွေ စုဆောင်းနေတယ် ----
    if step and step.startswith('adding_links_season_'):
        season_num = step.replace('adding_links_season_', '')
        
        # ---- ခင်ဗျားရဲ့ ပုံစံအတိုင်း ကိုင်တွယ်မယ် ----
        # ပုံစံ:
        # 🔗 သင်၏ Deep Link အဆင်သင့်ဖြစ်ပါပြီ။
        # 
        # https://t.me/WZNmoviefilsend_bot?start=oWA-ex7me6BDcZTb
        # 
        # The Wire (2002) - S01E12 - Cleaning Up 1080p MPK.mp4
        
        # URL နဲ့ Caption ကို ခွဲထုတ်မယ်
        deep_link, caption = extract_deep_link_and_caption(text)
        
        if not deep_link:
            await update.message.reply_text(
                "⚠️ Deep Link မတွေ့ပါ။\n\n"
                "ပုံစံ:\n"
                "```\n🔗 သင်၏ Deep Link အဆင်သင့်ဖြစ်ပါပြီ။\n\nhttps://t.me/Bot?start=xxx\n\nThe Wire - S01E01 - Title.mp4\n```"
            )
            return
        
        if not caption:
            # Caption မပါရင် URL ကိုပဲ သုံးမယ်
            caption = deep_link
        
        # Season/Episode ကို Caption ကနေ ထုတ်ယူမယ်
        season, episode = extract_season_episode_from_caption(caption)
        movie_title = extract_movie_title(caption)
        
        if season and episode:
            button_text = f"{movie_title} S{season}E{episode} ရယူရန် နှိပ်ပါ"
        else:
            button_text = f"Episode ရယူရန် နှိပ်ပါ"
        
        # Season အတွက် သိမ်းမယ်
        if 'temp_seasons' not in context.user_data:
            context.user_data['temp_seasons'] = {}
        
        if season_num not in context.user_data['temp_seasons']:
            context.user_data['temp_seasons'][season_num] = []
        
        # Episode Number ကို သိမ်းမယ် (စီရန်)
        _, ep_num = extract_season_episode_from_caption(caption)
        
        context.user_data['temp_seasons'][season_num].append({
            'text': button_text,
            'url': deep_link,
            'episode': ep_num or 0
        })
        
        total = len(context.user_data['temp_seasons'][season_num])
        await update.message.reply_text(
            f"✅ **Season {season_num}** - Link #{total} သိမ်းဆည်းပြီးပါပြီ။\n"
            f"📝 {button_text}\n"
            f"🔗 {deep_link[:50]}...\n\n"
            f"✅ ဆက်ပို့နိုင်ပါတယ်။\n"
            f"✅ Season {season_num} ပြီးရင် `{season_num}` ရိုက်ပါ။"
        )
        return
    
    # ---- ဘာမှမဟုတ်ရင် ----
    await update.message.reply_text(
        "⚠️ နားမလည်ပါ။\n\n"
        "📌 `/post` - Post အသစ်စတင်ရန်\n"
        "📌 `/1`, `/2`, `/3` - Season ရွေးရန်\n"
        "📌 `/done` - Post တင်ရန်\n"
        "📌 `/cancel` - ဖျက်ရန်"
    )

# ---- Main ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    for i in range(1, 21):
        app.add_handler(CommandHandler(str(i), season_command))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
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
