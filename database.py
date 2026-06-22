import os
from pymongo import MongoClient
from datetime import datetime

# 🔥 Environment Variable ကနေ MONGO_URI ကိုဖတ်မယ်
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI not set in environment variables")

# 🔥 MongoDB Connection
client = MongoClient(
    MONGO_URI,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=3000,
    connectTimeoutMS=3000,
    socketTimeoutMS=3000
)
db = client["file_share_bot"]
files_col = db["files"]
posts_col = db["posts"]

def save_post_data(poster_file_id, caption, seasons, telegraph_url):
    """Post Data ကို သိမ်းမယ်"""
    data = {
        "poster_file_id": poster_file_id,
        "caption": caption,
        "seasons": seasons,
        "telegraph_url": telegraph_url,
        "created_at": datetime.utcnow()
    }
    return posts_col.insert_one(data)
