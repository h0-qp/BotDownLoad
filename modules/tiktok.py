import cloudscraper

def extract_tiktok_data(url: str) -> dict:
    clean_url = url.split("?")[0] if "?" in url else url
    api_url = "https://www.tikwm.com/api/"
    data = {"url": clean_url, "hd": 1}
    def fix_url(link): return "https://www.tikwm.com" + link if link and link.startswith("/") else link
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.post(api_url, data=data, timeout=15)
        if resp.status_code == 200:
            res = resp.json()
            if res.get("code") == 0:
                body = res.get("data")
                if "images" in body:
                    return {"type": "images", "images": [fix_url(i) for i in body["images"]], "audio": fix_url(body.get("music")), "title": body.get("title")}
                else: return {"type": "video", "video_url": fix_url(body.get("play")), "title": body.get("title")}
    except Exception: pass
    return None
