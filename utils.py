import re

def parse_season_episode(caption):
    """
    Caption ထဲက Season နဲ့ Episode ကို ထုတ်ယူပါ
    """
    if not caption:
        return None, None
    
    patterns = [
        r'(?:S|Season)\s*(\d+)\s*(?:E|Episode)\s*(\d+)',
        r's(\d+)e(\d+)',
        r'(\d+)x(\d+)',
        r'Episode\s*(\d+)',
        r'E(\d+)',
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
    
    # Quality နဲ့ Format တွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(MPK|MKV|MP4|AVI|x264|x265|HEVC|H\.264|H\.265)\b', '', cleaned, flags=re.IGNORECASE)
    
    # Dash တွေကို Space ပြောင်းပြီး နေရာလွတ်တွေကို စုစည်းမယ်
    cleaned = re.sub(r'-\s*', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # နာမည်ကို ထုတ်ယူမယ် (ပထမဆုံး စကားလုံးအုပ်စု)
    # ဥပမာ - "The Wire The Target" ဆိုရင် "The Wire" ပဲ ယူမယ်
    parts = cleaned.split()
    if len(parts) >= 2:
        # "The" နဲ့စရင် ပထမ 2 လုံး (The Wire)
        if parts[0].lower() == "the" and len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        else:
            # ပထမဆုံး 2 လုံးကို ယူမယ်
            return " ".join(parts[:2])
    
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
    
    # Quality နဲ့ Format တွေကို ဖယ်ရှားမယ်
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(MPK|MKV|MP4|AVI|x264|x265|HEVC)\b', '', cleaned, flags=re.IGNORECASE)
    
    # Dash နဲ့ နေရာလွတ်တွေကို ရှင်းမယ်
    cleaned = re.sub(r'-\s*', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # Episode Name ကို ထုတ်ယူမယ်
    if cleaned:
        # "The Wire The Target" ဆိုရင် "The Target" ကို ယူမယ်
        parts = cleaned.split()
        if len(parts) >= 3 and parts[0].lower() == "the" and parts[1].lower() == "wire":
            # "The Wire" ဖယ်ပြီး ကျန်တာကို Episode Name အဖြစ်
            return " ".join(parts[2:]) or "Episode"
        elif len(parts) >= 2 and parts[0].lower() == "the":
            # "The" နဲ့စပြီး နောက်ထပ် စကားလုံးတွေပါရင် အကုန်ယူမယ်
            return " ".join(parts[1:]) or "Episode"
        else:
            # မဟုတ်ရင် အကုန်လုံးကို Episode Name အဖြစ်
            return cleaned
    
    return "Episode"
