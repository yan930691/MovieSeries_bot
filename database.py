from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
from datetime import datetime

# SSL Error မဖြစ်အောင် tlsAllowInvalidCertificates=true ထည့်ပေးထားတယ်
def get_db_connection():
    """MongoDB Connection ကို SSL Error မရှိအောင် ပြင်ဆင်ထားတယ်"""
    client = MongoClient(
        MONGODB_URI,
        tls=True,
        tlsAllowInvalidCertificates=True  # ဒါက SSL Error ကို ဖြေရှင်းပေးတယ်
    )
    return client[DB_NAME]

db = get_db_connection()
posts_col = db["posts"]

def save_post_data(poster_file_id, caption, seasons_data, telegraph_url):
    """Post Data ကို သိမ်းမယ်"""
    data = {
        "poster_file_id": poster_file_id,
        "caption": caption,
        "seasons": seasons_data,
        "telegraph_url": telegraph_url,
        "created_at": datetime.utcnow()
    }
    return posts_col.insert_one(data)

def get_all_posts(limit=10):
    """နောက်ဆုံး Post ၁၀ ခုကို ယူမယ်"""
    cursor = posts_col.find().sort("created_at", -1).limit(limit)
    return list(cursor)

def get_post_by_id(post_id):
    """Post ID နဲ့ ရှာမယ်"""
    from bson import ObjectId
    return posts_col.find_one({"_id": ObjectId(post_id)})
