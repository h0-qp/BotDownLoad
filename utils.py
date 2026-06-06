import aiohttp
import aiofiles
import asyncio
import os
from user_agent import generate_user_agent
from urllib.parse import urlparse
from uuid import uuid4
import requests
import config
from sqldb import db

# ⚙️ Asynchronous Download System
async def download_file(url, extension=None):
    if extension is None:
        path = urlparse(url).path
        extension = os.path.splitext(path)[1]
        if not extension:
            extension = ".mp4"
            
    uid = uuid4()
    filename = f"{uid}{extension}"
    
    headers = {"User-Agent": generate_user_agent()}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            if not chunk:
                                break
                            await f.write(chunk)
                    return filename
    except Exception as e:
        print(f"Async download error: {e}")
    return None

# ⚙️ Thread Executor for heavy sync functions (like yt-dlp)
async def run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# Sync logic moved to executor if needed
def is_member(user_id):
    ch_channel = db.get("channel")
    if not ch_channel: return True
    ch_user = ch_channel.get("id") if isinstance(ch_channel, dict) else None
    if not ch_user or ch_user == "لا يوجد": return True
    try:
        res = requests.get(f"https://api.telegram.org/bot{config.token}/getchatmember?chat_id={ch_user}&user_id={user_id}").text
        if "member" in res or "creator" in res or "administrator" in res:
            return True
        return False
    except:
        return True

async def check_subscription(client, message):
    id = message.from_user.id
    if db.get("subs") not in ["False", 0, None, False, "0"]:
        if not await run_sync(is_member, id):
            ch_user_info = db.get("channel")
            ch_user = ch_user_info.get("username") if isinstance(ch_user_info, dict) else "cn_world"
            await message.reply(f"أنت غير مشترك في قناة البوت رجاءا أشتراك بالاول لتتمكن من أستخدام البوت.\n\nCH: @{ch_user}\n\nبعد الاشتراك ارسل /start مجددا")
            return False
    return True
