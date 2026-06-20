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
