import re

def parse_season_episode(caption):
    """
    Caption ထဲက Season နဲ့ Episode ကို ထုတ်ယူပါ
    အောက်ပါပုံစံတွေကို အကုန်ဖမ်းမယ်:
    - S01E01, s01e01
    - Season 1 Episode 1, season 1 episode 1
    - 1x01, 1x1
    - s1e1, S1E1
    """
    if not caption:
        return None, None
    
    patterns = [
        # S01E01, s01e01
        r'(?i)s(\d+)\s*e(\d+)',
        # Season 1 Episode 1
        r'(?i)season\s*(\d+)\s*(?:episode|ep)\s*(\d+)',
        # 1x01, 1x1
        r'(\d+)\s*x\s*(\d+)',
        # Episode 1 Season 1
        r'(?i)(?:episode|ep)\s*(\d+)\s*season\s*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            # group(1) က Season, group(2) က Episode
            return int(match.group(1)), int(match.group(2))
    
    return None, None

def extract_episode_name(caption):
    """Caption ထဲက Episode အမည်ကို ထုတ်ယူမယ် (ဥပမာ - 'Episode 1' သို့ 'EP01')"""
    if not caption:
        return "Episode"
    
    # Season/Episode ကို ဖယ်ပြီး ကျန်တာကို Episode Name အဖြစ်သတ်မှတ်
    cleaned = re.sub(r'(?i)s\s*\d+\s*e\s*\d+', '', caption)
    cleaned = re.sub(r'(?i)season\s*\d+\s*(?:episode|ep)\s*\d+', '', cleaned)
    cleaned = re.sub(r'\d+\s*x\s*\d+', '', cleaned)
    cleaned = re.sub(r'(?i)(?:episode|ep)\s*\d+\s*season\s*\d+', '', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        return "Episode"
    return cleaned

def extract_movie_title(caption):
    """Caption ထဲက Movie နာမည်ကို ထုတ်ယူမယ် (Season/Episode ဖယ်ပြီးကျန်တာ)"""
    if not caption:
        return "Unknown Movie"
    
    # Season/Episode ပုံစံတွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?i)s\s*\d+\s*e\s*\d+', '', caption)
    cleaned = re.sub(r'(?i)season\s*\d+\s*(?:episode|ep)\s*\d+', '', cleaned)
    cleaned = re.sub(r'\d+\s*x\s*\d+', '', cleaned)
    cleaned = re.sub(r'(?i)(?:episode|ep)\s*\d+\s*season\s*\d+', '', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned or "Unknown Movie"
