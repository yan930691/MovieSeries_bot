from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME
import os

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Collection နှစ်ခု
files_col = db["movie_files"]
posts_col = db["movie_posts"]

def save_video_file(file_id, movie_title, season, episode, caption):
    """Video File Data ကို သိမ်းမယ်"""
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
    """ဇာတ်ကားတစ်ကားအတွက် Season/Episode အားလုံးကို ဆွဲထုတ်မယ်"""
    cursor = files_col.find({"movie_title": movie_title}).sort([("season", 1), ("episode", 1)])
    return list(cursor)

def get_video_by_season_episode(movie_title, season, episode):
    """သတ်မှတ် Season/Episode အတွက် File ID ကို ရှာမယ်"""
    return files_col.find_one({"movie_title": movie_title, "season": season, "episode": episode})

def save_post_data(movie_title, poster_file_id, synopsis, telegraph_url, episodes_list):
    """Channel မှာ Post တင်ပြီးရင် အချက်အလက်တွေ သိမ်းမယ်"""
    data = {
        "movie_title": movie_title,
        "poster_file_id": poster_file_id,
        "synopsis": synopsis,
        "telegraph_url": telegraph_url,
        "episodes": episodes_list  # [{season:1, episode:1}, ...]
    }
    posts_col.update_one(
        {"movie_title": movie_title},
        {"$set": data},
        upsert=True
    )

def get_post_data(movie_title):
    return posts_col.find_one({"movie_title": movie_title})
