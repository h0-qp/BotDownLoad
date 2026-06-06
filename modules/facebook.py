import os
import uuid
import yt_dlp

def download_facebook_video(url: str) -> dict:
    filename = f"fb_{uuid.uuid4().hex[:6]}.mp4"
    # إعدادات خاصة لتخطي حماية فيسبوك وسحب أعلى جودة mp4
    ydl_opts = {
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'max_filesize': 50 * 1024 * 1024,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if os.path.exists(filename):
                return {"path": filename, "title": info.get("title", "Facebook Video 🎬")}
    except Exception as e:
        print(f"Facebook Download Error: {e}", flush=True)
        if os.path.exists(filename): os.remove(filename)
    return None
