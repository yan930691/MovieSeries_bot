from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

files_col = db["movie_files"]
posts_col = db["movie_posts"]
sessions_col = db["sessions"]  # Session data အတွက်

def save_video_file(file_id, movie_title, season, episode, caption):
    data = {
        "file_id": file_id,
        "movie_title": movie_title,
        "season": season,
        "episode": episode,
        "caption": caption
    }
    return files_col.update_one(
        {"movie_title": movie_title, "season": season, "episode": episode},
        {"$set": data},
        upsert=True
    )

def get_all_episodes(movie_title):
    cursor = files_col.find({"movie_title": movie_title}).sort([("season", 1), ("episode", 1)])
    return list(cursor)

def get_video_by_season_episode(movie_title, season, episode):
    return files_col.find_one({"movie_title": movie_title, "season": season, "episode": episode})

def save_post_data(movie_title, poster_file_id, synopsis, telegraph_url, episodes_list):
    data = {
        "movie_title": movie_title,
        "poster_file_id": poster_file_id,
        "synopsis": synopsis,
        "telegraph_url": telegraph_url,
        "episodes": episodes_list
    }
    posts_col.update_one(
        {"movie_title": movie_title},
        {"$set": data},
        upsert=True
    )

def get_post_data(movie_title):
    return posts_col.find_one({"movie_title": movie_title})

# ---- Session အတွက် ----
def save_session(chat_id, data):
    """Session data ကို DB မှာ သိမ်းမယ်"""
    sessions_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "data": data}},
        upsert=True
    )

def get_session(chat_id):
    """Session data ကို DB ကနေ ဆွဲထုတ်မယ်"""
    session = sessions_col.find_one({"chat_id": chat_id})
    if session:
        return session.get("data", {})
    return {}

def delete_session(chat_id):
    """Session data ကို DB ကနေ ဖျက်မယ်"""
    sessions_col.delete_one({"chat_id": chat_id})
