from pyrogram import Client, filters, enums
import os
import re
import requests
import config
from utils import check_subscription, run_sync, download_file
from sqldb import db

@Client.on_message(filters.regex("^(https|http)://t.me/.*?/[0-9]+") & filters.private)
async def telegram_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return
        
    m = await message.reply("**__جاري التحميل...__**")
    try:
        r = await run_sync(lambda tx: requests.get(tx).text, message.text)
        links = re.findall('<meta property="twitter:image" content="(.*?)">', r)
        if links:
            url = links[0]
            extension = ".mp4" if ".mp4" in url else ".jpg"
            dl_path = await download_file(url, extension)
            if dl_path:
                await message.reply_document(dl_path)
                os.remove(dl_path)
        await m.delete()
    except Exception as e:
        print(e)
        await m.edit("**حدث خطأ.**")
