from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

posts_col = db["posts"]

# လိုအပ်ရင် နောက်မှ ထပ်ထည့်လို့ရတယ်
