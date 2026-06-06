from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn
import os
import yt_dlp
from uuid import uuid4
import config
from utils import check_subscription, run_sync, download_file
from sqldb import db
from api import soundcloud, spotify

@Client.on_message(filters.regex("^(https|http)://m.soundcloud.com/.*?") & filters.private)
async def soundcloud_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    m = await message.reply("**جاري التحميل...**")
    try:
        response = await run_sync(soundcloud, message.text)
        if not response or not response.get("status"):
            return await m.edit("**لم يتم إيجاد الاغنية.**")
            
        link = response["link"]
        dl_path = await download_file(link, ".mp3")
        if dl_path:
            via = f"[via](https://t.me/{bot.me.username})"
            caption = f"[Link]({message.text}) | {via}."
            await message.reply_audio(dl_path, caption=caption)
            os.remove(dl_path)
        await m.delete()
    except Exception as error:
        print(error)
        await m.edit("حدث خطأ.")

@Client.on_message(filters.regex("^(https|http)://(spotify|open.spotify).com/track/.*?") & filters.private)
async def spotify_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    m = await message.reply("**جاري التحميل...**")
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"
    channel_title = username_ch.get("title") if isinstance(username_ch, dict) else "القناة"

    try:
        response = await run_sync(spotify, message.text)
        if not response or not response.get("status"):
            return await m.edit("**أرسل رابط سبوتي صحيح.**")
            
        link = response["link"]
        
        def yt_dlp_spotify(l):
            ydl_ops = {"format": "bestaudio[ext=m4a]", "outtmpl": f"{uuid4()}.%(ext)s"}
            with yt_dlp.YoutubeDL(ydl_ops) as ydl:
                info_dict = ydl.extract_info(l, download=True)
                return ydl.prepare_filename(info_dict), info_dict
                
        dl_path, info_dict = await run_sync(yt_dlp_spotify, link)
        if dl_path:
            if int(info_dict.get('duration', 0)) > 700:
                os.remove(dl_path)
                return await m.edit("**⚠️ حد التحميل ساعة ونص فقط**")
                
            thumb_path = await download_file(info_dict.get('thumbnail', ''), ".jpg")
            
            via = f"[via](https://t.me/{bot.me.username})"
            caption = f"[Link]({message.text}) | {via}."
            
            await message.reply_audio(
                audio=dl_path,
                title=info_dict.get('title'),
                duration=int(info_dict.get('duration', 0)),
                performer=info_dict.get('channel', 'Unknown'),
                caption=caption,
                thumb=thumb_path,
                reply_markup=km([[btn(f"{channel_title}", url=f"https://t.me/{username_ch}")]] )
            )
            os.remove(dl_path)
            if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        await m.delete()
    except Exception as error:
        print(error)
        await m.edit("حدث خطأ.")

@Client.on_message(filters.command("song") & filters.private)
async def downsong_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    if len(message.text.split(None)) <= 1:
        return await message.reply("ضع شيء للبحث عنه.")
        
    query = message.text.replace("/song ", "")
    msg = await message.reply("**يتم التحميل...**")
    
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"
    channel_title = username_ch.get("title") if isinstance(username_ch, dict) else "القناة"

    try:
        from youtube_search import YoutubeSearch
        yt = await run_sync(lambda q: YoutubeSearch(q, max_results=1).to_dict(), query)
        if not yt: return await msg.edit("لم يتم العثور على شيء.")
        
        vid_id = yt[0]["id"]
        url = f'https://youtu.be/{vid_id}'
        
        def yt_dlp_song(u):
            ydl_ops = {"format": "bestaudio[ext=m4a]", "outtmpl": f"{uuid4()}.%(ext)s"}
            with yt_dlp.YoutubeDL(ydl_ops) as ydl:
                info_dict = ydl.extract_info(u, download=True)
                return ydl.prepare_filename(info_dict), info_dict
                
        dl_path, info_dict = await run_sync(yt_dlp_song, url)
        
        if dl_path:
            if int(info_dict.get('duration', 0)) > 10555:
                os.remove(dl_path)
                return await msg.edit("**⚠️ حد التحميل ساعة ونص فقط**")
            
            await msg.edit("**جاري الإرسال ..**")
            thumb_path = await download_file(info_dict.get('thumbnail', ''), ".jpg")
            
            await message.reply_audio(
                dl_path,
                title=info_dict.get('title'),
                duration=int(info_dict.get('duration', 0)),
                performer=info_dict.get('channel', ''),
                thumb=thumb_path,
                reply_markup=km([[btn(f"{channel_title}", url=f"https://t.me/{username_ch}")]] )
            )
            os.remove(dl_path)
            if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        await msg.delete()
    except Exception as error:
        print(error)
        await msg.edit("**⚠️ صار خطأ.**")
