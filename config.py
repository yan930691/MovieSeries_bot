import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGODB_URI = os.environ.get("MONGODB_URI")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # မထည့်ချင်ရင် None ထားလိုက်
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # ခင်ဗျား Telegram User ID
RENDER_URL = os.environ.get("RENDER_URL")  # https://your-bot.onrender.com

# Database Name
DB_NAME = "movie_bot_db"
