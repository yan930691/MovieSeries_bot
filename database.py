from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
from datetime import datetime

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

posts_col = db["posts"]

def save_post_data(poster_file_id, caption, seasons_data, telegraph_url):
    data = {
        "poster_file_id": poster_file_id,
        "caption": caption,
        "seasons": seasons_data,
        "telegraph_url": telegraph_url,
        "created_at": datetime.utcnow()
    }
    return posts_col.insert_one(data)
