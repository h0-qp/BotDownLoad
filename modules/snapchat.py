import os
import uuid
import yt_dlp

def download_snapchat_video(url: str) -> dict:
    filename = f"snap_{uuid.uuid4().hex[:6]}.mp4"
    ydl_opts = {
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'max_filesize': 30 * 1024 * 1024
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if os.path.exists(filename):
                return {"path": filename, "title": info.get("description", "Snapchat Spotlight ✨")}
    except Exception as e:
        print(f"Snapchat Download Error: {e}", flush=True)
        if os.path.exists(filename): os.remove(filename)
    return None
