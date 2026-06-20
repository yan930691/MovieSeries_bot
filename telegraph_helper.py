import uuid
from telegraph import Telegraph

telegraph = Telegraph()

def create_telegraph_page(title, content):
    try:
        telegraph.create_account(short_name=f'bot_{uuid.uuid4().hex[:8]}')
        response = telegraph.create_page(
            title=title,
            html_content=f"<p>{content.replace(chr(10), '<br>')}</p>",
            author_name="Movie Bot"
        )
        return response['url']
    except Exception as e:
        print(f"Telegraph Error: {e}")
        return None
