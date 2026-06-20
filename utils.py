import re

def parse_season_episode(caption):
    if not caption:
        return None, None
    
    patterns = [
        r'(?:S|Season)\s*(\d+)\s*(?:E|Episode)\s*(\d+)',
        r's(\d+)e(\d+)',
        r'(\d+)x(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    return None, None

def extract_movie_title(caption):
    if not caption:
        return "Unknown Movie"
    
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    return cleaned.strip() or "Unknown Movie"

def extract_episode_name(caption):
    """Caption ထဲက Episode အမည်ကို ထုတ်ယူမယ် (ဥပမာ - 'Episode 1' သို့ 'EP01')"""
    if not caption:
        return "Episode"
    
    # Season/Episode ကို ဖယ်ပြီး ကျန်တာကို Episode Name အဖြစ်သတ်မှတ်
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        return "Episode"
    return cleaned
