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
        r'Episode\s*(\d+)',                               # Episode 1
        r'E(\d+)',                                        # E1
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)), int(match.group(2))
            elif len(match.groups()) == 1:
                return 1, int(match.group(1))
    
    return None, None

def extract_movie_title(caption):
    """
    Caption ထဲက ဇာတ်ကားနာမည်ကို ထုတ်ယူပါ
    ဥပမာ - The Wire (2002) - S01E12 - Cleaning Up 1080p MPK
    ➡️ The Wire
    """
    if not caption:
        return "Unknown Movie"
    
    # Season/Episode ဖော်ပြချက်တွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'Episode\s*\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'E\d+', '', cleaned, flags=re.IGNORECASE)
    
    # Year ကို ဖယ်ရှားမယ် (2002)
    cleaned = re.sub(r'\(\d{4}\)', '', cleaned)
    
    # Quality ကို ဖယ်ရှားမယ် (1080p, 720p, 4K, MPK, MKV, MP4, x264, x265)
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(MPK|MKV|MP4|AVI|x264|x265|HEVC|H\.264|H\.265)\b', '', cleaned, flags=re.IGNORECASE)
    
    # နာမည်မဟုတ်တဲ့ စကားလုံးတွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'-\s*', ' ', cleaned)  # Dash ကို space ပြောင်း
    cleaned = re.sub(r'\s+', ' ', cleaned)   # နေရာလွတ်တွေကို စုစည်း
    cleaned = cleaned.strip()
    
    return cleaned or "Unknown Movie"

def extract_episode_name(caption):
    """
    Caption ထဲက Episode အမည်ကို ထုတ်ယူမယ် (ခလုတ်နာမည်အတွက်)
    ဥပမာ - The Wire (2002) - S01E12 - Cleaning Up 1080p MPK
    ➡️ Cleaning Up
    """
    if not caption:
        return "Episode"
    
    # Season/Episode ဖော်ပြချက်တွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'Episode\s*\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'E\d+', '', cleaned, flags=re.IGNORECASE)
    
    # Year ကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'\(\d{4}\)', '', cleaned)
    
    # Quality ကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(MPK|MKV|MP4|AVI|x264|x265|HEVC)\b', '', cleaned, flags=re.IGNORECASE)
    
    # Dash နဲ့ နေရာလွတ်တွေကို ရှင်းမယ်
    cleaned = re.sub(r'-\s*', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # Episode Name ကို ထုတ်ယူမယ် (နောက်ဆုံးအပိုင်း)
    if cleaned and ' - ' in caption:
        # Caption ထဲက နာမည်အတိုင်း ထားမယ်
        return cleaned
    
    # ဘာမှမရှိရင်
    if not cleaned:
        return "Episode"
    return cleaned
