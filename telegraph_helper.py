import requests
from telegraph import Telegraph
import uuid

telegraph = Telegraph()

def create_telegraph_page(title, content):
    """
    Telegraph မှာ Page တစ်ခုဆောက်ပြီး URL ပြန်ပေးမယ်
    content က HTML format ဖြစ်ရမယ် (သို့) စာသားရှည်
    """
    try:
        # Account မရှိရင် အလိုအလျောက် ဖန်တီးပေးမယ်
        telegraph.create_account(short_name=f'bot_{uuid.uuid4().hex[:8]}')
        
        response = telegraph.create_page(
            title=title,
            html_content=f"<p>{content.replace(chr(10), '<br>')}</p>",  # New line တွေကို <br> ပြောင်း
            author_name="Movie Bot"
        )
        return response['url']
    except Exception as e:
        print(f"Telegraph Error: {e}")
        return None
