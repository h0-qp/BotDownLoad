import re
import cloudscraper
import instaloader
from bs4 import BeautifulSoup

il = instaloader.Instaloader(
    download_pictures=False, download_videos=False, 
    download_video_thumbnails=False, download_geotags=False, 
    download_comments=False, save_metadata=False
)
il.context._session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

SESSION_ID = "54331833835%3A7fPWDGnWJnUZCj%3A22%3AAYdgFUZ8fSyRh7xLnXc_7HnrMxPkQmVUEDI5cUoPLA"
try:
    il.context._session.cookies.set("sessionid", SESSION_ID, domain=".instagram.com")
except Exception: pass

def fetch_instagram_post(url: str) -> list:
    try:
        match = re.search(r'/(?:p|reel|tv|share/reel)/([A-Za-z0-9_-]+)', url)
        if not match: return []
        shortcode = match.group(1)
        post = instaloader.Post.from_shortcode(il.context, shortcode)
        media_list = []
        if post.typename == 'GraphSidecar':
            for node in post.get_sidecar_nodes():
                if node.is_video: media_list.append({"type": "video", "url": node.video_url})
                else: media_list.append({"type": "photo", "url": node.display_url})
        else:
            if post.is_video: media_list.append({"type": "video", "url": post.video_url})
            else: media_list.append({"type": "photo", "url": post.display_url})
        return media_list
    except Exception:
        try:
            scr = cloudscraper.create_scraper()
            resp = scr.post("https://co.wuk.sh/api/json", json={"url": url}, headers={"Accept": "application/json", "Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200 and resp.json().get("url"):
                return [{"type": "video", "url": resp.json()["url"]}]
        except Exception: pass
    return []

def fetch_instagram_profile(username: str) -> dict:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        url = f"https://www.instagram.com/{username}/"
        resp = scraper.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            title_tag = soup.find("meta", {"property": "og:title"})
            desc_tag = soup.find("meta", {"property": "og:description"})
            img_tag = soup.find("meta", {"property": "og:image"})
            
            name = username
            followers = "غير محدد"
            following = "غير محدد"
            
            if title_tag and title_tag.get("content"):
                name = title_tag["content"].split("•")[0].strip()
            if desc_tag and desc_tag.get("content"):
                desc = desc_tag["content"]
                f_match = re.search(r'([0-9kM\.,]+)\s*Followers', desc)
                if f_match: followers = f_match.group(1)
                l_match = re.search(r'([0-9kM\.,]+)\s*Following', desc)
                if l_match: following = l_match.group(1)
                
            pic_url = img_tag["content"] if img_tag else "https://telegram.org/img/t_logo.png"
            return {
                "name": name, "username": username, "bio": "بايو مخفي",
                "followers": followers, "following": following,
                "is_verified": "Verified" in resp.text,
                "is_private": "🔒 الحساب قد يكون خاصاً" if "isPrivate\":true" in resp.text else "🔓 حساب عام",
                "pic_url": pic_url, "id": "مخفي للآمان"
            }
    except Exception: pass
    return None

def fetch_instagram_stories(username: str) -> list:
    try:
        profile = instaloader.Profile.from_username(il.context, username)
        stories_media = []
        for story in il.get_stories(userids=[profile.userid]):
            for item in story.get_items():
                if item.is_video: stories_media.append({"type": "video", "url": item.video_url})
                else: stories_media.append({"type": "photo", "url": item.display_url})
        return stories_media
    except Exception:
        try:
            scr = cloudscraper.create_scraper()
            res = scr.post("https://api.cobalt.biz.ua/api/json", json={"url": f"https://instagram.com/stories/{username}/"}, timeout=10)
            if res.status_code == 200 and res.json().get("picker"):
                return [{"type": "video" if "video" in item["url"] else "photo", "url": item["url"]} for item in res.json()["picker"]]
        except Exception: pass
    return []
