from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
from datetime import datetime

def get_db_connection():
    client = MongoClient(
        MONGODB_URI,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    return client[DB_NAME]

db = get_db_connection()
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

def get_all_posts(limit=10):
    cursor = posts_col.find().sort("created_at", -1).limit(limit)
    return list(cursor)
