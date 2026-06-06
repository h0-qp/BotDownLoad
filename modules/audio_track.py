import os
import uuid
import cloudscraper
import yt_dlp

def download_audio_track(url: str) -> dict:
    scraper = cloudscraper.create_scraper()
    if "spotify.com" in url:
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            resp = scraper.get(oembed_url, timeout=10)
            if resp.status_code == 200:
                track_title = resp.json().get("title")
                if track_title:
                    ydl_opts = {
                        'outtmpl': f"audio_{uuid.uuid4().hex[:6]}.%(ext)s", 'quiet': True, 'no_warnings': True,
                        'format': 'bestaudio[ext=m4a]/m4a/bestaudio/best', 'noplaylist': True, 'max_filesize': 30 * 1024 * 1024
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(f"ytsearch1:{track_title} audio", download=True)
                        if 'entries' in info and info['entries']:
                            actual_filename = ydl.prepare_filename(info['entries'][0])
                            if os.path.exists(actual_filename): return {"path": actual_filename, "title": track_title}
        except Exception: pass
        return None

    filename = f"audio_{uuid.uuid4().hex[:6]}.mp3"
    instances = ["https://co.wuk.sh/api/json", "https://cobalt.cst.im/api/json", "https://api.cobalt.biz.ua/api/json"]
    for inst in instances:
        try:
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            resp = scraper.post(inst, json={"url": url, "isAudioOnly": True}, headers=headers, timeout=15)
            if resp.status_code == 200 and resp.json().get("status") in ["stream", "redirect"]:
                r = scraper.get(resp.json().get("url"), timeout=30)
                with open(filename, 'wb') as f: f.write(r.content)
                return {"path": filename, "title": resp.json().get("text", "Audio Track 🎵")}
        except Exception: continue
    return None
