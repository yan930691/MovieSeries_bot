from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
from datetime import datetime

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

posts_col = db["posts"]

def save_post_data(poster_file_id, caption, seasons_data, telegraph_url):
    """
    Post Data ကို သိမ်းမယ်
    seasons_data = {
        "1": [{"text": "S1E1", "url": "https://..."}, ...],
        "2": [{"text": "S2E1", "url": "https://..."}, ...]
    }
    """
    data = {
        "poster_file_id": poster_file_id,
        "caption": caption,
        "seasons": seasons_data,
        "telegraph_url": telegraph_url,
        "created_at": datetime.utcnow()
    }
    return posts_col.insert_one(data)

def get_latest_post():
    """နောက်ဆုံး Post ကို ယူမယ် (အသုံးမပြုရသေးဘူး)"""
    return posts_col.find_one(sort=[("_id", -1)])
