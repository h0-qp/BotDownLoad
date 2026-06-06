import os
import uuid
import yt_dlp

def download_youtube_video(url: str) -> dict:
    filename = f"temp_{uuid.uuid4().hex[:6]}.mp4"
    ydl_opts = {'outtmpl': filename, 'quiet': True, 'no_warnings': True, 'format': 'b[ext=mp4]/best', 'max_filesize': 50 * 1024 * 1024}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if os.path.exists(filename): return {"path": filename, "title": info.get("title", "")}
    except Exception:
        if os.path.exists(filename): os.remove(filename)
    return None
