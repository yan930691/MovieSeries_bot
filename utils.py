import re

def parse_season_episode(caption):
    """
    Caption ထဲက Season နဲ့ Episode ကို ထုတ်ယူပါ
    ဥပမာ: "The Walking Dead S01E01" -> (1, 1)
    """
    if not caption:
        return None, None
    
    # S01E02, S1E2, Season 1 Episode 2, s01e02 စသည်ဖြင့် အကုန်ဖမ်းမယ်
    patterns = [
        r'(?:S|Season)\s*(\d+)\s*(?:E|Episode)\s*(\d+)',
        r's(\d+)e(\d+)',
        r'(\d+)x(\d+)'  # 1x01 ပုံစံအတွက်
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    return None, None

def extract_movie_title(caption):
    """
    Season/Episode ဖယ်ပြီး ဇာတ်ကားနာမည်ကို သီးသန့်ထုတ်ယူပါ
    """
    if not caption:
        return "Unknown Movie"
    # S01E01 စတဲ့ စာသားတွေကို ဖယ်ရှားပြီး ကျန်တာကို နာမည်အဖြစ်သတ်မှတ်
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    return cleaned.strip() or "Unknown Movie"
