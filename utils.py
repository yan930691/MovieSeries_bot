import re

def parse_season_episode(caption):
    """
    Caption ထဲက Season နဲ့ Episode ကို ထုတ်ယူပါ
    အောက်ပါပုံစံတွေကို ဖမ်းယူနိုင်တယ်-
    - s1e1, S1E1, s01e01, S01E01
    - Season 1 Episode 1, season 1 episode 1
    - 1x01, 1x1
    - Episode 1 (ဒါဆိုရင် Season ကို 1 လို့ သတ်မှတ်မယ်)
    - Ep 1
    """
    if not caption:
        return None, None
    
    # ပုံစံအမျိုးမျိုးအတွက် Regex Patterns
    patterns = [
        # s1e1, S01E01 စသည်ဖြင့်
        r'(?:s|S)\s*(\d+)\s*(?:e|E)\s*(\d+)',
        # Season 1 Episode 1
        r'(?:season|Season)\s*(\d+)\s*(?:episode|Episode)\s*(\d+)',
        # 1x01, 1x1
        r'(\d+)\s*x\s*(\d+)',
        # Episode 1 (Season မပါရင် Season=1)
        r'(?:episode|Episode|Ep|EP)\s*(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption)
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)), int(match.group(2))
            else:
                # Episode 1 ပုံစံအတွက် Season=1
                return 1, int(match.group(1))
    
    return None, None

def extract_movie_title(caption):
    """Caption ထဲက Season/Episode ဖယ်ပြီး ဇာတ်ကားနာမည်ကို ထုတ်ယူပါ"""
    if not caption:
        return "Unknown Movie"
    
    # ပုံစံအမျိုးမျိုးကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?:s|S)\s*\d+\s*(?:e|E)\s*\d+', '', caption)
    cleaned = re.sub(r'(?:season|Season)\s*\d+\s*(?:episode|Episode)\s*\d+', '', cleaned)
    cleaned = re.sub(r'\d+\s*x\s*\d+', '', cleaned)
    cleaned = re.sub(r'(?:episode|Episode|Ep|EP)\s*\d+', '', cleaned)
    
    cleaned = cleaned.strip()
    return cleaned or "Unknown Movie"

def extract_episode_name(caption):
    """Caption ထဲက Episode အမည်ကို ထုတ်ယူပါ (Season/Episode ဖယ်ပြီး ကျန်တာ)"""
    if not caption:
        return "Episode"
    
    # Season/Episode ပုံစံတွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?:s|S)\s*\d+\s*(?:e|E)\s*\d+', '', caption)
    cleaned = re.sub(r'(?:season|Season)\s*\d+\s*(?:episode|Episode)\s*\d+', '', cleaned)
    cleaned = re.sub(r'\d+\s*x\s*\d+', '', cleaned)
    cleaned = re.sub(r'(?:episode|Episode|Ep|EP)\s*\d+', '', cleaned)
    
    cleaned = cleaned.strip()
    
    if not cleaned:
        # Caption မှာ "s1e1" ပဲပါရင် "Episode 1" လို့ ပြန်ပေးမယ်
        season, episode = parse_season_episode(caption)
        if episode:
            return f"Episode {episode}"
        return "Episode"
    
    return cleaned
