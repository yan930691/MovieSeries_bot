import re

def parse_season_episode(caption):
    """
    Caption ထဲက Season နဲ့ Episode ကို ထုတ်ယူပါ
    ပုံစံများ: S01E01, s1e1, Season 1 Episode 1, 1x01, အစရှိသဖြင့်
    """
    if not caption:
        return None, None
    
    patterns = [
        r'(?:S|Season)\s*(\d+)\s*(?:E|Episode)\s*(\d+)',  # Season 1 Episode 1, S01E01
        r's(\d+)e(\d+)',                                  # s1e1, s01e01
        r'(\d+)x(\d+)',                                   # 1x01
        r'Episode\s*(\d+)',                               # Episode 1 (Season မပါရင်)
        r'E(\d+)',                                        # E1 (Season မပါရင်)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)), int(match.group(2))
            elif len(match.groups()) == 1:
                # Season မပါရင် Season 1 လို့ သတ်မှတ်မယ်
                return 1, int(match.group(1))
    
    return None, None

def extract_movie_title(caption):
    """Caption ထဲက ဇာတ်ကားနာမည်ကို ထုတ်ယူပါ"""
    if not caption:
        return "Unknown Movie"
    
    # Season/Episode ဖော်ပြချက်တွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'Episode\s*\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'E\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    return cleaned or "Unknown Movie"

def extract_episode_name(caption):
    """Caption ထဲက Episode အမည်ကို ထုတ်ယူမယ် (ခလုတ်နာမည်အတွက်)"""
    if not caption:
        return "Episode"
    
    # Season/Episode ဖော်ပြချက်တွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'Episode\s*\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'E\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    if not cleaned:
        return "Episode"
    return cleaned
