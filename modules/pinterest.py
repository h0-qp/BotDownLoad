import re
import cloudscraper
from bs4 import BeautifulSoup

def extract_pinterest_data(url: str) -> dict:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        resp = scraper.get(url, timeout=15)
        if resp.status_code == 200:
            mp4_matches = re.findall(r'https://[^"\'>\\]+\.mp4', resp.text)
            if mp4_matches: return {"type": "video", "url": next((v for v in mp4_matches if "720p" in v), mp4_matches[0])}
            soup = BeautifulSoup(resp.text, "html.parser")
            image_tag = soup.find("meta", {"property": "og:image"}) or soup.find("meta", {"name": "og:image"})
            if image_tag and image_tag.get("content"):
                img_url = image_tag["content"].replace("236x", "originals").replace("474x", "originals").replace("736x", "originals")
                return {"type": "photo", "url": img_url}
    except Exception: pass
    return None
