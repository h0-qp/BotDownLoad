from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn
import yt_dlp
import os
from uuid import uuid4

import config
from utils import check_subscription, run_sync, download_file
from sqldb import db

def extract_yt_info(url, is_audio=False):
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]' if is_audio else 'best[ext=mp4]',
        'outtmpl': f'{uuid4()}.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info

def search_yt(query):
    from youtube_search import YoutubeSearch
    return YoutubeSearch(query, max_results=1).to_dict()

# ⚙️ استخدام `async def` مع Pyrogram بشكل سليم للتزامن
@Client.on_message(filters.regex("^(http|https)://(watch\?v=|youtu\.be/|shorts/|www\.youtube\.com/|youtube\.com/|music\.youtube\.com/)") & filters.private)
async def youtube_handler(bot, message):
    if db.get(f"forward") in ["True", True]:
        await message.forward(config.channel_posts)

    if not await check_subscription(bot, message):
        return

    link = message.text.replace("music.", "").split("&")[0]
    vid_id = None
    for pattern in ["watch?v=", "youtu.be/", "shorts/"]:
        if pattern in link:
            parts = link.split(pattern)
            if len(parts) > 1:
                vid_id = parts[1].split("?")[0]
            break
            
    if not vid_id:
        return await message.reply("عذرا لم استطع استخراج المعرف.")

    try:
        # تشغيل مهمة بطيئة في Thread لتجنب تجميد البوت
        yt = await run_sync(search_yt, f'https://youtu.be/{vid_id}')
        if not yt: return await message.reply("لم يتم العثور على المقطع.")
        
        title = yt[0]['title']
        url = f'https://youtu.be/{vid_id}'
        
        reply_markup = km([
            [btn("صوت 💿", callback_data=f'AUDIO_{vid_id}'), btn("فيديو 🎥", callback_data=f'VIDEO_{vid_id}')]
        ])
        
        await message.reply_photo(
            str(yt[0]["thumbnails"][0].split("?")[0]),
            caption=f"**⤶ العنوان - [{title}]({url})**",
            reply_markup=reply_markup
        )
    except Exception as e:
        await message.reply("حدث خطأ أثناء الاتصال بيوتيوب.")

@Client.on_callback_query(filters.regex("^(AUDIO|VIDEO)_"))
async def youtube_callback(bot, query):
    action, vid_id = query.data.split("_")
    is_audio = (action == "AUDIO")
    url = f'https://youtu.be/{vid_id}'
    
    await query.edit_message_text("**جاري التحميل ..**")
    
    try:
        # الإنزال يتم في Thread منفصل لكي لا يتوقف البوت عن خدمة الآخرين
        filename, info = await run_sync(extract_yt_info, url, is_audio)
        
        if int(info.get('duration', 0)) > 10555:
            if os.path.exists(filename): os.remove(filename)
            return await query.edit_message_text("**⚠️ حد التحميل ساعة ونص فقط**")
            
        await query.edit_message_text("**جاري الإرسال ..**")
        
        # Async AIOHTTP download for thumbnails
        thumb_path = await download_file(info.get('thumbnail', ''), ".jpg")
        
        username_ch = db.get("channel")
        username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"
        markup = km([[btn("قناة البوت", url=f"https://t.me/{username_ch}")]])

        if is_audio:
            await query.message.reply_audio(
                filename,
                title=info.get('title'),
                duration=int(info.get('duration', 0)),
                performer=info.get('uploader'),
                thumb=thumb_path,
                reply_markup=markup
            )
        else:
            await query.message.reply_video(
                filename,
                duration=int(info.get('duration', 0)),
                thumb=thumb_path,
                reply_markup=markup
            )
            
        await query.edit_message_text("**تم التحميل.**")
        
        if os.path.exists(filename): os.remove(filename)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
            
    except Exception as e:
        await query.edit_message_text("**⚠️ صار خطأ.**")
        print(e)
