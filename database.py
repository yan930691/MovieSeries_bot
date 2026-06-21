from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
from datetime import datetime

client = MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client[DB_NAME]

files_col = db["files"]

def save_file_data(file_id, file_name, caption, deep_link, file_type):
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
    return files_col.find_one({"deep_link": deep_link})
