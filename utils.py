import re

def extract_deeplink_and_name(text):
    """
    ခင်ဗျားပို့တဲ့ ပုံစံကနေ Deep Link နဲ့ Video Name ကို ထုတ်ယူမယ်
    """
    if not text:
        return None, None
    
    url_pattern = r'https://t\.me/[^\s]+'
    url_match = re.search(url_pattern, text)
    
    if not url_match:
        return None, None
    
    url = url_match.group(0)
    
    remaining = text.replace(url, '').strip()
    
    lines = remaining.split('\n')
    name_parts = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('🔗') and not line.startswith('သင်၏'):
            name_parts.append(line)
    
    name = ' '.join(name_parts).strip()
    
    if not name:
        name = "Episode"
    
    return url, name

def extract_season_episode_from_name(name):
    """
    Video Name ထဲက Season နဲ့ Episode ကို ထုတ်ယူမယ်
    """
    if not name:
        return None, None
    
    patterns = [
        r'(?:S|Season)\s*(\d+)\s*(?:E|Episode)\s*(\d+)',
        r's(\d+)e(\d+)',
        r'(\d+)x(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    return None, None

def extract_button_name_from_name(name):
    """
    Video Name ကို ခလုတ်နာမည်အဖြစ် ပြောင်းမယ်
    """
    if not name:
        return "Episode"
    
    cleaned = re.sub(r'(?:S|Season)\s*\d+\s*(?:E|Episode)\s*\d+', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r's\d+e\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+x\d+', '', cleaned)
    cleaned = re.sub(r'\(\d{4}\)', '', cleaned)
    cleaned = re.sub(r'\b\d{3,4}p\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\.(mp4|mkv|avi|mov|wmv|flv|webm)$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'-\s*', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        return "Episode"
    
    return cleaned[:40]  # ရှည်ရင် အတိုချုံးမယ်
