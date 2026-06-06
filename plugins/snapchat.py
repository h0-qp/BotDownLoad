from pyrogram import Client, filters, enums
import os
import config
from utils import check_subscription, run_sync, download_file
from sqldb import db
from api import snapchat

@Client.on_message(filters.regex("^(https|http)://(snapchat.com|t.snapchat.com)") & filters.private)
async def snapchat_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    m = await message.reply("**جاري التحميل...**")
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"

    try:
        response = await run_sync(snapchat, message.text)
        url = response["link"]
        dl_path = await download_file(url, ".mp4")
        if dl_path:
            await message.reply_chat_action(enums.ChatAction.UPLOAD_VIDEO)
            await message.reply_video(dl_path, caption=f"@{username_ch}")
            os.remove(dl_path)
        await m.delete()
    except Exception as error:
        print(error)
        await m.edit("حدث خطأ.")
