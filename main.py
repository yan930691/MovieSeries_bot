import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, RENDER_URL
from database import save_post_data
from telegraph_helper import create_telegraph_page
from utils import extract_deeplink_and_name, extract_season_episode_from_name, extract_button_name_from_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Helper Function ----
def extract_movie_title_from_name(name):
    if not name:
        return "Movie"
    
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'\(\d{4}\)', '', cleaned)
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(MPK|MKV|MP4|AVI|x264|x265|HEVC)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned or "Movie"

# ---- Command Handlers ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    await update.message.reply_text(
        "🎥 **Button Creator Bot**\n\n"
        "📌 **ညွှန်ကြားချက်:**\n"
        "1️⃣ `/post` နှိပ်ပြီး Post အသစ်စတင်ပါ။\n"
        "2️⃣ Poster (ပုံ) → Caption (စာသား) ပို့ပါ။\n"
        "3️⃣ Deep Link တွေ ဆက်တိုက်ပို့ပါ။\n"
        "4️⃣ အကုန်ပို့ပြီးရင် `/done` နှိပ်ပါ။"
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
    links = context.user_data.get('temp_links', [])
    
    if not poster:
        await update.message.reply_text("⚠️ Poster (ပုံ) အရင်ပို့ပါ။")
        return
    
    if not caption_text:
        await update.message.reply_text("⚠️ Caption (စာသား) အရင်ပို့ပါ။")
        return
    
    if not links:
        await update.message.reply_text("⚠️ အနည်းဆုံး Deep Link တစ်ခုတော့ ပို့ပေးပါ။")
        return
    
    # ---- Link တွေကို Season အလိုက် စီမယ် ----
    seasons = {}
    for link_data in links:
        url = link_data['url']
        name = link_data['name']
        
        s, e = extract_season_episode_from_name(name)
        movie_name = extract_movie_title_from_name(name)
        
        if s and e:
            button_text = f"{movie_name} Season {s} Episode {e} ရယူရန်"
            season_key = str(s)
        else:
            button_text = extract_button_name_from_name(name)
            season_key = "0"
        
        if season_key not in seasons:
            seasons[season_key] = []
        
        seasons[season_key].append({
            'text': button_text,
            'url': url,
            'episode': e or 0
        })
    
    total_episodes = sum(len(links) for links in seasons.values())
    await update.message.reply_text(f"⏳ Post ဆောက်နေပါတယ်... (Seasons: {len(seasons)}, Episodes: {total_episodes})")
    
    # ---- Telegraph ----
    telegraph_url = None
    telegraph_button = None
    
    if len(caption_text) > 1024:
        telegraph_url = create_telegraph_page("ဇာတ်ညွှန်း", caption_text)
        if telegraph_url:
            caption_display = ""
            telegraph_button = InlineKeyboardButton(
                text="📖 ဇာတ်ညွှန်းအပြည့်အစုံဖတ်ရန်",
                url=telegraph_url
            )
        else:
            caption_display = caption_text[:1024] + "..."
    else:
        caption_display = caption_text
    
    # ---- ခလုတ်အားလုံးကို စုမယ် ----
    all_buttons = []
    
    if telegraph_button:
        all_buttons.append(('header', telegraph_button))
    
    for season_num in sorted(seasons.keys(), key=int):
        season_links = seasons[season_num]
        season_links_sorted = sorted(season_links, key=lambda x: x.get('episode', 0))
        
        if season_num == "0":
            header_text = "─── အခြား အပိုင်းများ ───"
        else:
            header_text = f"─── အတွဲ {season_num} (အပိုင်းပေါင်း: {len(season_links_sorted)}) ───"
        
        all_buttons.append(('header', InlineKeyboardButton(header_text, callback_data="none")))
        
        for link_data in season_links_sorted:
            all_buttons.append(('button', InlineKeyboardButton(link_data['text'], url=link_data['url'])))
    
    # ---- ဒေတာကို သိမ်းထားမယ် ----
    context.user_data['all_buttons'] = all_buttons
    context.user_data['poster'] = poster
    context.user_data['caption_display'] = caption_display
    context.user_data['season_count'] = len(seasons)
    context.user_data['total_episodes'] = total_episodes
    context.user_data['caption_text'] = caption_text
    context.user_data['telegraph_url'] = telegraph_url
    
    # ---- ပထမစာမျက်နှာကို ပြမယ် ----
    await show_page(update, context, page=0)

async def show_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0, edit: bool = False):
    """စာမျက်နှာတစ်ခုကို ပြမယ်"""
    all_buttons = context.user_data.get('all_buttons', [])
    poster = context.user_data.get('poster')
    caption_display = context.user_data.get('caption_display', '')
    
    if not all_buttons or not poster:
        await update.message.reply_text("⚠️ ဒေတာ မတွေ့ပါ။ /post နဲ့ ပြန်စတင်ပါ။")
        return
    
    # ---- စာမျက်နှာခွဲမယ် (တစ်မျက်နှာ ၅၀ ခလုတ်) ----
    ITEMS_PER_PAGE = 50
    total_pages = (len(all_buttons) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(all_buttons))
    page_buttons = all_buttons[start_idx:end_idx]
    
    # ---- Keyboard ဆောက်မယ် ----
    keyboard = []
    for btn_type, btn in page_buttons:
        keyboard.append([btn])
    
    # ---- စာမျက်နှာ ညွှန်ပြချက်တွေ ----
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ နောက်", callback_data=f"page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="none"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("ရှေ့ ▶️", callback_data=f"page_{page+1}"))
    
    if len(nav_buttons) > 1:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    final_caption = f"🎬 **{caption_display}**\n\n📥 အောက်ပါခလုတ်များကို နှိပ်ပြီး ကြည့်ရှု့ပါ။\n\n📄 စာမျက်နှာ {page+1}/{total_pages}"
    
    # ---- Post ကို ပြန်ပို့မယ် ----
    try:
        if edit:
            await update.callback_query.edit_message_media(
                media=telegram.InputMediaPhoto(
                    media=poster,
                    caption=final_caption,
                    parse_mode='Markdown'
                ),
                reply_markup=reply_markup
            )
            await update.callback_query.answer()
        else:
            await update.message.reply_photo(
                photo=poster,
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # ---- Database မှာ သိမ်းမယ် ----
            try:
                save_post_data(
                    poster, 
                    context.user_data.get('caption_text'), 
                    context.user_data.get('season_count'), 
                    context.user_data.get('telegraph_url')
                )
            except Exception as db_error:
                logger.error(f"Database save error: {db_error}")
            
            await update.message.reply_text(
                f"✅ **Post ကို သင့်ဆီကိုပဲ ပို့လိုက်ပါပြီ။**\n\n"
                f"📊 Season {context.user_data.get('season_count', 0)} ခု၊ Episode {context.user_data.get('total_episodes', 0)} ခု ပါဝင်ပါတယ်။\n"
                f"📄 စာမျက်နှာ {total_pages} ခု ခွဲထားပါတယ်။\n\n"
                f"💡 Channel မှာ ပြန်တင်ချင်ရင် ဒီ Post ကို Forward လုပ်ပါ။"
            )
        
    except Exception as e:
        error_msg = f"❌ Post တင်ရာမှာ အမှားရှိသွားတယ်။ ကျေးဇူးပြုပြီး နောက်မှ ပြန်ကြိုးစားပါ။"
        if edit:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        logger.error(f"Post error: {e}")

# ---- Callback Handler (စာမျက်နှာပြောင်းရန်) ----
async def page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("page_"):
        return
    
    try:
        page = int(data.split("_")[1])
    except:
        return
    
    # show_page ကို edit=True နဲ့ ခေါ်မယ်
    await show_page(update, context, page=page, edit=True)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ခွင့်မပြုပါ။")
        return
    
    context.user_data.clear()
    await update.message.reply_text("✅ လုပ်ဆောင်နေတာကို ဖျက်လိုက်ပါပြီ။")

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
        context.user_data['step'] = 'waiting_links'
        await update.message.reply_text(
            "✅ Caption သိမ်းဆည်းပြီးပါပြီ။\n\n"
            "🔗 Deep Link တွေ စတင်ပို့ပါ။\n"
            "ဘယ်ပုံစံမဆို ရပါတယ်။\n\n"
            "✅ အကုန်ပို့ပြီးရင် `/done` နှိပ်ပါ။"
        )
        return
    
    # ---- Deep Link တွေ စုဆောင်းနေတယ် ----
    if step == 'waiting_links':
        url, name = extract_deeplink_and_name(text)
        
        if not url:
            await update.message.reply_text(
                "⚠️ Deep Link မတွေ့ပါ။\n"
                "ကျေးဇူးပြုပြီး `https://t.me/...` ပါတဲ့ Message ကို ပို့ပါ။"
            )
            return
        
        if 'temp_links' not in context.user_data:
            context.user_data['temp_links'] = []
        
        context.user_data['temp_links'].append({
            'url': url,
            'name': name
        })
        
        total = len(context.user_data['temp_links'])
        await update.message.reply_text(
            f"✅ Link #{total} သိမ်းဆည်းပြီးပါပြီ။\n"
            f"✅ ဆက်ပို့နိုင်ပါတယ်။\n"
            f"✅ အကုန်ပြီးရင် `/done` နှိပ်ပါ။"
        )
        return
    
    # ---- ဘာမှမဟုတ်ရင် ----
    await update.message.reply_text(
        "⚠️ နားမလည်ပါ။\n\n"
        "📌 `/post` - Post အသစ်စတင်ရန်\n"
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
    app.add_handler(CallbackQueryHandler(page_callback, pattern="page_"))
    
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
