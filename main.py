import os
import logging
import re
import hashlib
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import save_file_data, get_file_by_deep_link
from telegraph_helper import create_telegraph_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_USERNAME = None

# ---- Helper Functions (Button Creator) ----
def extract_season_episode_from_caption(caption):
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

# ---- Helper Functions (Deep Link Generator) ----
def generate_deep_link(file_name, caption):
    """ဖိုင်နာမည်နဲ့ Caption ကိုကြည့်ပြီး Deep Link ထုတ်ပေးမယ်"""
    hash_id = hashlib.md5(f"{file_name}_{caption}_{datetime.utcnow().timestamp()}".encode()).hexdigest()[:16]
    return f"https://t.me/{BOT_USERNAME}?start={hash_id}"

# ---- Command Handlers (Button Creator) ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    await update.message.reply_text(
        "🎬 **Button Creator + Deep Link Generator Bot**\n\n"
        "📌 **Button Creator အတွက်:**\n"
        "1️⃣ `/post` နှိပ်ပြီး Post အသစ်စတင်ပါ။\n"
        "2️⃣ Poster (ပုံ) → Caption (စာသား) ပို့ပါ။\n"
        "3️⃣ `/1`, `/2`, `/3` ... နှိပ်ပြီး Season ရွေးပါ။\n"
        "4️⃣ Deep Link တွေ ဆက်တိုက်ပို့ပါ။\n"
        "5️⃣ Season ပြီးရင် `1`, `2`, `3` ... နှိပ်ပါ။\n"
        "6️⃣ အကုန်ပြီးရင် `/done` နှိပ်ပါ။\n\n"
        "🔗 **Deep Link Generator အတွက်:**\n"
        "• ဘာဖိုင်မဆို (Forward ပါ) တိုက်ရိုက်ပို့ပါ။\n"
        "• Bot က Caption ကိုကြည့်ပြီး Deep Link ထုတ်ပေးမယ်။"
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
    
    # Telegraph
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
        
        await update.message.reply_photo(
            photo=poster,
            caption=final_caption,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            f"✅ **Post ကို သင့်ဆီကိုပဲ ပို့လိုက်ပါပြီ။**\n"
            f"📊 Season {len(seasons)} ခု၊ Episode {total_episodes} ခု ပါဝင်ပါတယ်။"
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
        f"ပုံစံ: `နာမည်|https://t.me/...` သို့ `https://t.me/...`\n\n"
        f"✅ Season {season_num} ပြီးရင် `{season_num}` လို့ ရိုက်ပါ။"
    )

# ---- Handlers (Button Creator) ----
async def handle_photo_button_creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_text_button_creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    text = update.message.text.strip()
    
    if text.startswith('/'):
        return
    
    step = context.user_data.get('step')
    
    # Caption
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
    
    # Season Done
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
    
    # Deep Link စုဆောင်းနေတယ်
    if step and step.startswith('adding_links_season_'):
        season_num = step.replace('adding_links_season_', '')
        
        if '|' in text:
            parts = text.split('|', 1)
            button_text = parts[0].strip()
            button_url = parts[1].strip()
        else:
            button_url = text
            if not button_url.startswith('https://t.me/'):
                await update.message.reply_text(
                    "⚠️ URL က `https://t.me/...` နဲ့ စရမယ်။\n\n"
                    "ပုံစံ: `https://t.me/Bot?start=xxx` (သို့) `နာမည်|https://t.me/Bot?start=xxx`"
                )
                return
            
            caption_text = text
            season, episode = extract_season_episode_from_caption(caption_text)
            movie_title = extract_movie_title(caption_text)
            
            if season and episode:
                button_text = f"{movie_title} S{season}E{episode} ရယူရန် နှိပ်ပါ"
            else:
                button_text = f"Episode ရယူရန် နှိပ်ပါ"
        
        if not button_url.startswith('https://t.me/'):
            await update.message.reply_text("⚠️ URL က `https://t.me/...` နဲ့ စရမယ်။")
            return
        
        if 'temp_seasons' not in context.user_data:
            context.user_data['temp_seasons'] = {}
        
        if season_num not in context.user_data['temp_seasons']:
            context.user_data['temp_seasons'][season_num] = []
        
        _, ep_num = extract_season_episode_from_caption(button_url)
        
        context.user_data['temp_seasons'][season_num].append({
            'text': button_text,
            'url': button_url,
            'episode': ep_num or 0
        })
        
        total = len(context.user_data['temp_seasons'][season_num])
        await update.message.reply_text(
            f"✅ **Season {season_num}** - Link #{total} သိမ်းဆည်းပြီးပါပြီ။\n"
            f"📝 {button_text}\n\n"
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

# ---- Deep Link Generator Handler (Forward ပါ ဖမ်းမယ်) ----
async def handle_file_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ဖိုင်တွေကို ကိုင်တွယ်မယ် (Forward ပါ)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    # Button Creator က သုံးနေတယ်ဆိုရင် မလုပ်ပါနဲ့
    if context.user_data.get('step'):
        return
    
    # ---- ဖိုင်ကို စစ်ဆေးမယ် (Forward ပါ) ----
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
        f"{deep_link}\n\n"
        f"📁 **ဖိုင်အချက်အလက်:**\n"
        f"{type_emoji} {file_name}\n"
        f"📝 Caption: {caption}\n\n"
        f"{db_status}\n\n"
        f"💡 **သုံးစွဲသူများအတွက်:**\n"
        f"ဒီ Link ကို **နှိပ်လိုက်ရင်** ဖိုင်ကို Bot က ပြန်ပို့ပေးမယ်။"
    )
    
    await update.message.reply_text(reply_text, parse_mode='Markdown')

# ---- Deep Link Handler (သုံးစွဲသူတွေ Link နှိပ်ရင်) ----
async def deep_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start?start=xxx ဆိုပြီး လာရင် ဖိုင်ကို ပြန်ပို့မယ် """
    user_id = update.effective_user.id
    args = context.args
    
    # Admin အတွက် /start (Deep Link မပါရင်)
    if not args:
        if user_id == ADMIN_ID:
            await start_command(update, context)
        else:
            await update.message.reply_text(
                "🔗 Deep Link မှ ကြိုဆိုပါတယ်။\n"
                "ကျေးဇူးပြုပြီး တရားဝင် Link ကို သုံးပါ။"
            )
        return
    
    link_id = args[0]
    deep_link = f"https://t.me/{context.bot.username}?start={link_id}"
    
    logger.info(f"Deep Link clicked: {deep_link}")
    
    # Database ကနေ ရှာမယ်
    file_data = get_file_by_deep_link(deep_link)
    
    if not file_data:
        await update.message.reply_text(
            "❌ ဒီ Link အတွက် ဖိုင်ကို ရှာမတွေ့ပါ။\n"
            "Link က သက်တမ်းကုန်သွားတာ (သို့) မှားနေတာ ဖြစ်နိုင်ပါတယ်။"
        )
        return
    
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
    except Exception as e:
        await update.message.reply_text(f"❌ ဖိုင်ကို ပြန်ပို့ရာမှာ အမှားရှိသွားတယ်: {e}")

# ---- Main ----
def main():
    global BOT_USERNAME
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    BOT_USERNAME = None
    
    # Commands (Button Creator)
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Season Commands (/1, /2, /3 ...)
    for i in range(1, 21):
        app.add_handler(CommandHandler(str(i), season_command))
    
    # Deep Link Handler (သုံးစွဲသူတွေအတွက်)
    app.add_handler(CommandHandler("start", deep_link_handler))
    
    # Handlers (Button Creator)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_button_creator))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_button_creator))
    
    # Deep Link Generator Handler (Forward ပါ ဖမ်းမယ်)
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        handle_file_deep_link
    ), group=1)  # group=1 ထားလို့ Button Creator ထက် နောက်ကျမှ အလုပ်လုပ်မယ်
    
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
