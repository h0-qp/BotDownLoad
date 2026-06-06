from pyrogram import Client, filters, enums
import os
import wget
from uuid import uuid4
import yt_dlp
import re

import config
from utils import check_subscription, run_sync, download_file
from sqldb import db
from api import tik, tiktokV3, tiktok

@Client.on_message(filters.regex("^(http|https)://.*?.tiktok.com") & filters.private)
async def tiktok_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
    
    if not await check_subscription(bot, message):
        return

    text = message.text
    msg = await message.reply("**جاري التحميل ...**")
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"

    try:
        url_data = await run_sync(tik, text)
        medias = []
        if isinstance(url_data, dict) and url_data.get("duration") == 0:
            for i in url_data["medias"]:
                dl_path = await download_file(i["url"], f".{i.get('extension', 'jpg')}")
                if dl_path:
                    if i["extension"] == "jpg":
                        await message.reply_photo(dl_path)
                    elif i["extension"] == "mp4":
                        await message.reply_video(dl_path)
                    else:
                        await message.reply_audio(dl_path)
                    medias.append(dl_path)
            await message.reply(f"**Done - @{username_ch}**")
            for i in medias:
                if os.path.exists(i): os.remove(i)
        elif isinstance(url_data, dict) and "medias" in url_data:
            dl_path = await download_file(url_data["medias"][0]["url"], ".mp4")
            if dl_path:
                await message.reply_video(dl_path, caption=f"@{username_ch}")
                os.remove(dl_path)
        else:
            raise Exception("Invalid tik data")
        await msg.delete()
    except Exception as e:
        print(f"error 0 : {e}")
        try:
            url = await run_sync(tiktokV3, text)
            dl_path = await download_file(url, ".mp4")
            if dl_path:
                await message.reply_video(dl_path, caption=f"@{username_ch}")
                os.remove(dl_path)
            await msg.delete()
        except Exception as e2:
            print(f"error 1 with tiktok, error: {e2}")
            try:
                data = await run_sync(tiktok, text)
                url = re.findall('href="(.*?)" rel="nofollow"', data["data"])[0]
                dl_path = await download_file(url, ".mp4")
                if dl_path:
                    await message.reply_video(dl_path, caption=f"@{username_ch}")
                    os.remove(dl_path)
                await msg.delete()
            except Exception as e3:
                print(f"error 2 with tiktok, error: {e3}")
                try:
                    def yt_dlp_tiktok(t):
                        ydl_opts = {'format': 'best[ext=mp4]', 'outtmpl': f'{uuid4()}.%(ext)s'}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(t, download=True)
                            return ydl.prepare_filename(info)
                            
                    filename = await run_sync(yt_dlp_tiktok, text)
                    if filename:
                        await message.reply_video(filename, caption=f"@{username_ch}")
                        os.remove(filename)
                    await msg.delete()
                except Exception as e4:
                    await msg.edit('حصل خطأ. );')
