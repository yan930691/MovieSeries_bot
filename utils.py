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
    """Caption ထဲက ဇာတ်ကားနာမည်ကို ထုတ်ယူပါ (Button အတွက် အသုံးပြုမယ်)"""
    if not caption:
        return "Unknown Movie"
    return caption.strip()

def get_button_text(caption, season, episode):
    """
    Button ပေါ်မှာ ပြမယ့် စာသားကို ပြင်ဆင်မယ်
    သတ်မှတ်ထားတဲ့ ပုံစံရှိရင် အတိုချုံးပြမယ်၊ မဟုတ်ရင် Caption အတိုင်းပြမယ်
    """
    if not caption:
        return f"Episode {episode}"
    
    # သတ်မှတ်ထားတဲ့ ပုံစံများ (ဥပမာ - "The Wire (2002) - S01E01 - The Target")
    # ဒါမျိုးဆိုရင် အတိုချုံးပြမယ်
    patterns = [
        r'(.*?)\s*[-\s]*S\d+E\d+[-\s]*(.*)',  # The Wire - S01E01 - The Target
        r'(.*?)\s*[-\s]*s\d+e\d+[-\s]*(.*)',  # The Wire - s1e1 - The Target
        r'(.*?)\s*[-\s]*Season\s*\d+\s*Episode\s*\d+[-\s]*(.*)',  # The Wire - Season 1 Episode 1 - The Target
    ]
    
    for pattern in patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            ep_title = match.group(2).strip()
            if title and ep_title:
                # ဇာတ်ကားနာမည်နဲ့ Episode နာမည်ကို အတိုချုံးပြမယ်
                return f"{title[:30]} - {ep_title[:20]}" if len(title) > 30 else f"{title} - {ep_title}"
            elif title:
                return title[:40] if len(title) > 40 else title
    
    # သတ်မှတ်ပုံစံမရှိရင် Caption အတိုင်းပြမယ် (ဒါပေမယ့် ရှည်ရင် အတိုချုံးမယ်)
    return caption[:50] + "..." if len(caption) > 50 else caption
