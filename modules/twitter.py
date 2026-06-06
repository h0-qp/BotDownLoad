import re
import cloudscraper

def extract_twitter_data(url: str) -> list:
    match = re.search(r'(?:twitter\.com|x\.com)/([^/]+/status/\d+)', url)
    if not match: return []
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(f"https://api.vxtwitter.com/{match.group(1)}", timeout=10)
        if resp.status_code == 200:
            media_list = []
            for m in resp.json().get("media_extended", []):
                if m["type"] == "image": media_list.append({"type": "photo", "url": m["url"]})
                elif m["type"] in ["video", "gif"]: media_list.append({"type": "video", "url": m["url"]})
            return media_list
    except Exception: pass
    return []
