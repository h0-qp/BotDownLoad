from pyrogram import Client, filters, enums
from pyrogram.types import InputMediaPhoto, InputMediaVideo
import os
import glob
import instaloader
from uuid import uuid4

import config
from sqldb import db
from utils import check_subscription, download_file, run_sync
from api import download_media, reels, instagram_reel, best_reels, highlights, stories, story, Instagram_Info_v1
from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn

# إعداد Instaloader
insta = instaloader.Instaloader(
    download_pictures=True,
    download_video_thumbnails=False,
    download_videos=True,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    post_metadata_txt_pattern=""
)
SESSION_ID = "54331833835%3A7fPWDGnWJnUZCj%3A22%3AAYdgFUZ8fSyRh7xLnXc_7HnrMxPkQmVUEDI5cUoPLA"
insta.context._session.cookies.set("sessionid", SESSION_ID, domain=".instagram.com")

def download_instaloader_post(shortcode):
    target_dir = f"insta_{uuid4()}"
    try:
        post = instaloader.Post.from_shortcode(insta.context, shortcode)
        insta.download_post(post, target=target_dir)
        
        files = []
        if os.path.exists(target_dir):
            for f in os.listdir(target_dir):
                if f.endswith(".mp4") or f.endswith(".jpg") or f.endswith(".png"):
                    files.append(os.path.join(target_dir, f))
        
        files.sort()
        return files, post.caption, target_dir
    except Exception as e:
        print(f"Instaloader error: {e}")
        return [], "", target_dir


# ✨ Pyrogram Smart Plugin - مجلد منعزل للتعامل مع انستجرام فقط

@Client.on_message(filters.regex("^(http|https)://(www.|)instagram.com/[a-zA-Z0-9_/]+") & filters.private)
async def instagram(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
    
    if not await check_subscription(bot, message):
        return

    link = message.text
    chat_id = message.chat.id
    m = await message.reply("جاري التحميل انتظر...")
    
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"
    
    if "/p/" in link or "/reel/" in link:
        try:
            pattern = "/p/" if "/p/" in link else "/reel/"
            shortcode = link.split(pattern)[1].split("/")[0].split("?")[0]
            
            # Use instaloader in run_sync to avoid blocking
            files, caption, target_dir = await run_sync(download_instaloader_post, shortcode)
            
            if not files:
                await m.edit("لم يتم العثور على الوسائط أو حدث خطأ أثناء التحميل.")
                return

            media = []
            caption_text = f"**{caption[:100]}...**\n\n@{username_ch}" if caption else f"@{username_ch}"
            
            for i, file in enumerate(files):
                if len(media) >= 10:
                    await bot.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
                    await message.reply_media_group(media)
                    media.clear()
                    
                is_photo = file.endswith(".jpg") or file.endswith(".png")
                
                # إرفاق الوصف فقط مع أول ملف في المجموعة
                cap = caption_text if i == 0 else ""
                
                if is_photo:
                    media.append(InputMediaPhoto(file, caption=cap))
                else:
                    media.append(InputMediaVideo(file, caption=cap))
                    
            if media:
                await bot.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
                if len(media) == 1:
                    if media[0].__class__.__name__ == "InputMediaPhoto":
                        await message.reply_photo(media[0].media, caption=caption_text)
                    else:
                        await message.reply_video(media[0].media, caption=caption_text)
                else:
                    await message.reply_media_group(media)
                
            await m.delete()
            
            # Clean up the directory
            if os.path.exists(target_dir):
                import shutil
                shutil.rmtree(target_dir)
                        
        except Exception as error:
            print(error)
            await m.edit("حدث خطأ في تحميل المنشور.")
                
    elif "/s/" in link:
        response = await run_sync(highlights, link)
        if response.get("msg") != "OK" or response.get("code") != 200:
            return await m.edit("صار خطأ تأكد من الرابط")
        try:
            media = []
            files = []
            for video in response["result"]["insBos"]:
                if len(media) >= 10:
                    await bot.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
                    await message.reply_media_group(media)
                    media.clear()
                    
                video_url = video["url"]
                is_mp4 = ".mp4" in video_url
                dl_path = await download_file(video_url, ".mp4" if is_mp4 else ".jpg")
                if dl_path:
                    files.append(dl_path)
                    if is_mp4:
                        media.append(InputMediaVideo(dl_path, caption=f"@{username_ch}"))
                    else:
                        media.append(InputMediaPhoto(dl_path, caption=f"@{username_ch}"))
                        
            if media:
                await bot.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
                await message.reply_media_group(media)
            await m.delete()
            for file in files: os.remove(file)
        except Exception as e:
            await m.edit("حدث خطأ.")
    else:
        # Stories
        link_cleaned = link.split("instagram.com/")[1].split("/")[0].split("?")[0]
        try:
            response = await run_sync(stories, link_cleaned)
            if not response or len(response.get("result", [])) < 1:
                return await m.edit("لا يوجد ستوريات في هذا الحساب")
            
            media = []
            files = []
            for video in response["result"]:
                if "video_versions" in video:
                    url = video["video_versions"][0]["url"]
                    dl_path = await download_file(url, ".mp4")
                    if dl_path:
                        media.append(InputMediaVideo(dl_path, caption=f"@{username_ch}"))
                        files.append(dl_path)
                else:
                    url = video["image_versions2"]["candidates"][0]["url"]
                    dl_path = await download_file(url, ".jpg")
                    if dl_path:
                        media.append(InputMediaPhoto(dl_path, caption=f"@{username_ch}"))
                        files.append(dl_path)
                        
            if media:
                await bot.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
                await message.reply_media_group(media)
            await m.delete()
            for file in files: os.remove(file)
        except Exception as e:
            await m.edit("صار خطأ او لم يتم أيجاد ستوري في الحساب.")

@Client.on_callback_query(filters.regex("GET_STORY_"))
async def get_story_from_info_instagram(bot, query):
    user = query.data.split("GET_STORY_")[1]
    chat_id = query.message.chat.id
    m = await query.message.reply("**جاري التحميل...**")
    
    username_ch = db.get("channel")
    username_ch = username_ch.get("username") if isinstance(username_ch, dict) else "cn_world"

    try:
        response = await run_sync(stories, user)
        if not response or len(response.get("result", [])) < 1:
            return await m.edit("لا يوجد ستوريات في هذا الحساب")
            
        media = []
        files = []
        for video in response["result"]:
            if "video_versions" in video:
                url = video["video_versions"][0]["url"]
                dl_path = await download_file(url, ".mp4")
                if dl_path:
                    media.append(InputMediaVideo(dl_path, caption=f"@{username_ch}"))
                    files.append(dl_path)
            else:
                url = video["image_versions2"]["candidates"][0]["url"]
                dl_path = await download_file(url, ".jpg")
                if dl_path:
                    media.append(InputMediaPhoto(dl_path, caption=f"@{username_ch}"))
                    files.append(dl_path)
                    
        if media:
            await bot.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
            await query.message.reply_media_group(media)
            
        await m.delete()
        from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn
        await query.message.edit_reply_markup(reply_markup=km([[btn("تم التحميل.", callback_data="DONE_DOWNLOAD")]]))
        
        for file in files: os.remove(file)
    except Exception as e:
        print(e)
        await m.edit("صار خطأ.")

@Client.on_message(filters.regex("^(@|)[a-zA-Z0-9_.]+$") & filters.private)
async def instagram_profile_handler(bot, message):
    if db.get("forward") in ["True", True]:
        await message.forward(config.channel_posts)
        
    if not await check_subscription(bot, message):
        return

    text = message.text
    if text.startswith("http") or text.startswith("/"):
        # Ignore commands and URLs
        return

    user = text.replace("@", "")
    m = await message.reply("جاري التحميل...")
    
    try:
        info = await run_sync(Instagram_Info_v1, user)
        if not info:
            return await m.edit("**حصل خطأ في جلب المعلومات أو الحساب غير موجود.**")
            
        name = info.get("full_name") or "لا يوجد اسم"
        bio = info.get("biography") or "لا يوجد"
        followed = info.get("follower_count", 0)
        follow = info.get("following_count", 0)
        photo = info.get("photo")
        is_private = "عام" if not info.get("is_private") else "خاص"
        
        button = km([[btn("تحميل الاستوريات 🔰", callback_data=f"GET_STORY_{user}")]]) if not info.get("is_private") else km([[btn("الحساب خاص ⚠️", callback_data="is_private_error")]])
        
        msg_text = f"**الاسم: [{name}](https://instagram.com/{user})\nالمتابعين: {followed}\nيتابع: {follow}\nالخصوصية: {is_private}\n\nالبايو: {bio}**"
        
        await m.delete()
        if photo:
            dl_path = await download_file(photo, ".jpg")
            if dl_path:
                await message.reply_photo(dl_path, caption=msg_text, reply_markup=button)
                os.remove(dl_path)
            else:
                await message.reply(msg_text, reply_markup=button)
        else:
            await message.reply(msg_text, reply_markup=button)
            
    except Exception as e:
        print(e)
        await m.edit("**حصل خطأ في جلب المعلومات.**")
