from pyrogram import Client, filters, enums
import os
import config
from utils import check_subscription, run_sync, download_file
from sqldb import db
from api import pinterest, pinterestV2

@Client.on_message(filters.regex("^(http|https)://pin.it") & filters.private)
async def pint_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
    
    if not await check_subscription(bot, message):
        return

    msg = await message.reply("__جاري التحميل__")
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"

    try:
        data = await run_sync(pinterestV2, message.text)
        link = data["link"]
        dl_path = await download_file(link)
        if dl_path:
            await bot.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
            if ".mp4" in dl_path:
                await message.reply_video(dl_path, caption=f"@{username_ch}")
            else:
                await message.reply_photo(dl_path, caption=f"@{username_ch}")
            os.remove(dl_path)
        await msg.delete()
        return
    except Exception as error:
        print("Pinterest V2 error:", error)

    try:
        url_data = await run_sync(pinterest, message.text)
        link = url_data["link"]
        photo = url_data["thmub"]
        
        thumb_path = await download_file(photo, ".png")
        video_path = await download_file(link, ".mp4")
        
        if video_path:
            await bot.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_VIDEO)
            await message.reply_video(
                video_path,
                caption=f'@{username_ch}',
                thumb=thumb_path
            )
            os.remove(video_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
        await msg.delete()
    except Exception as error:
        print(error)
        await msg.edit("**حدث خطأ**")
