import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGODB_URI = os.environ.get("MONGODB_URI")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
RENDER_URL = os.environ.get("RENDER_URL")

DB_NAME = "movie_bot_db"
