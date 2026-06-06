from pyrogram import Client, filters, enums
from pyrogram.types import InputMediaPhoto, InputMediaVideo
import os
import asyncio
import config
from utils import check_subscription, run_sync, download_file
from sqldb import db
from api import twitter, threads

@Client.on_message(filters.regex("(twitter.com|x.com)") & filters.private)
async def twitter_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
    
    if not await check_subscription(bot, message):
        return

    m = await message.reply("**جاري التحميل...**")
    try:
        data = await run_sync(twitter, message.text)
        url = data["link"]
        dl_path = await download_file(url, ".mp4")
        if dl_path:
            await message.reply_chat_action(enums.ChatAction.UPLOAD_VIDEO)
            vid = await message.reply_video(dl_path, caption="سيتم حذف الفيديو بعد 60 ثواني.")
            os.remove(dl_path)
            await m.delete()
            await asyncio.sleep(60)
            await vid.delete()
    except Exception as error:
        print(error)
        await m.edit("حدث خطأ.")

@Client.on_message(filters.regex("^(http|https)://(threads.net|www.threads.net)") & filters.private)
async def threads_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    m = await message.reply("**جاري التحميل...**")
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"

    try:
        response = await run_sync(threads, message.text)
        if not response or not response.get("result"):
            return await m.edit("هناك خطأ حاول ربما لم أجد الفيديو حاول برابط اخر.")
            
        videos = response.get("videos", [])
        images = response.get("images", [])
        media = []
        media_for_download = []
        
        for i in images:
            if len(media) >= 10:
                await message.reply_chat_action(enums.ChatAction.UPLOAD_PHOTO)
                await message.reply_media_group(media)
                media.clear()
            dl_path = await download_file(i, ".jpg")
            if dl_path:
                media_for_download.append(dl_path)
                media.append(InputMediaPhoto(dl_path))
                
        for i in videos:
            if len(media) >= 10:
                await message.reply_chat_action(enums.ChatAction.UPLOAD_VIDEO)
                await message.reply_media_group(media)
                media.clear()
            dl_path = await download_file(i, ".mp4")
            if dl_path:
                media_for_download.append(dl_path)
                media.append(InputMediaVideo(dl_path))
                
        if media:
            await message.reply_media_group(media)
        await message.reply(f"@{username_ch}")
        
        await m.delete()
        for file in media_for_download:
            if os.path.exists(file): os.remove(file)
            
    except Exception as error:
        print(error)
        await m.edit("حدث خطأ.")
