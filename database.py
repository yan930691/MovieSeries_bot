from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
from datetime import datetime

client = MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client[DB_NAME]

posts_col = db["posts"]
files_col = db["files"]  # Deep Link အတွက် ဖိုင်တွေသိမ်းမယ်

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

def save_file_data(file_id, file_name, caption, deep_link, file_type):
    """Deep Link အတွက် ဖိုင်ဒေတာကို သိမ်းမယ်"""
    data = {
        "file_id": file_id,
        "file_name": file_name,
        "caption": caption,
        "deep_link": deep_link,
        "file_type": file_type,
        "created_at": datetime.utcnow()
    }
    return files_col.insert_one(data)

def get_file_by_deep_link(deep_link):
    """Deep Link နဲ့ ဖိုင်ကို ရှာမယ်"""
    return files_col.find_one({"deep_link": deep_link})
