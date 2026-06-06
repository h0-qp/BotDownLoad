from pyrogram import Client, filters, enums
import os
import config
from utils import check_subscription, run_sync, download_file
from sqldb import db
from api import fb

@Client.on_message(filters.regex("^(https|http)://(fb.watch|.*?.facebook.com)") & filters.private)
async def facebook_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    m = await message.reply("**جاري التحميل...**")
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"

    try:
        url_data = await run_sync(fb, message.text)
        if not url_data or not url_data.get("result"):
            return await m.edit("**لم أجد الفيديو حاول برابط اخر.**")
            
        link = url_data["links"]
        await message.reply_chat_action(enums.ChatAction.UPLOAD_VIDEO)
        
        dl_path = await download_file(link, ".mp4")
        if dl_path:
            from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn
            await message.reply_video(
                dl_path,
                caption=f"@{username_ch}",
                reply_markup=km([[btn(text="•الرابط•", url=message.text)]])
            )
            os.remove(dl_path)
        await m.delete()
    except Exception as error:
        print(error)
        await m.edit("حدث خطأ ما.")
