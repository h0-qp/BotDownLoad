import asyncio
import time
import os
import re
from pyrogram import filters, enums
from pyromod import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from pyrogram.errors import UserNotParticipant
from kvsqlite.sync import Client as KVSQ

# استيراد محركات التحميل من الموديلات المنفصلة 🚀
from modules.tiktok import extract_tiktok_data
from modules.instagram import fetch_instagram_post, fetch_instagram_profile, fetch_instagram_stories
from modules.youtube import download_youtube_video
from modules.twitter import extract_twitter_data
from modules.pinterest import extract_pinterest_data
from modules.audio_track import download_audio_track
from modules.facebook import download_facebook_video
from modules.snapchat import download_snapchat_video


API_ID = 12588588 
API_HASH = "f2e0652152a45a25dc70f5bed7907d6e"
BOT_TOKEN = "8509012164:AAEfJcqsprCSlN2BHBX2td4UitXvK_Cu4nc"
OWNER_ID = 1160471152 

START_TIME = time.time()
app = Client("MyBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = KVSQ("bot_data.sqlite")

if not db.exists("users"): db.set("users", [])
if not db.exists("banned_users"): db.set("banned_users", [])
if not db.exists("force_channel"): db.set("force_channel", "None")
if not db.exists("welcome_message"):
    db.set("welcome_message", "- مرحبا بك {mention}\n- في بوت تحميل من جميع المواقع \n \nللتحميل ارسل الرابط فقط.")

def get_uptime():
    uptime_sec = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours} ساعة, {minutes} دقيقة"

async def is_subscribed(client, user_id):
    channel = db.get("force_channel")
    if channel == "None": return True
    try:
        member = await client.get_chat_member(channel, user_id)
        if member.status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]: return True
    except UserNotParticipant: return False
    except Exception: return True
    return False

def build_caption(client, media_title=""):
    custom_rights = db.get("caption_rights") if db.exists("caption_rights") else None
    if not custom_rights:
        custom_rights = f"تم التحميل بواسطة @{client.me.username if client.me else 'Bot'}"
    if media_title: return f"📝 {media_title}\n\n🤖 {custom_rights}"
    return f"🤖 {custom_rights}"

# ------------------------------------------------------------------------
# لوحة التحكم والأزرار والآدمن
# ------------------------------------------------------------------------
@app.on_message(filters.command("admin") & filters.user(OWNER_ID) & filters.private)
async def admin_panel(client, message):
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 إذاعة (رسالة/ميديا)", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 حظر شخص", callback_data="admin_ban"), InlineKeyboardButton("✅ إلغاء حظر", callback_data="admin_unban")],
        [InlineKeyboardButton("🔄 تغيير قناة الاشتراك", callback_data="change_fsub")],
        [InlineKeyboardButton("📝 كليشة الترحيب", callback_data="change_welcome"), InlineKeyboardButton("🏷️ تغيير حقوق القناة", callback_data="change_rights")]
    ])
    await message.reply("👑 **لوحة الإدارة الاحترافية:**", reply_markup=btns)

@app.on_callback_query()
async def callback_handler(client, callback):
    data = callback.data
    chat_id = callback.message.chat.id
    
    if data.startswith("dl_story_"):
        target_username = data.replace("dl_story_", "")
        await callback.answer("⏳ جاري جلب الستوريات...", show_alert=False)
        status_msg = await client.send_message(chat_id, "⏳ **جاري جلب الستوريات حالياً...**")
        
        stories = await asyncio.to_thread(fetch_instagram_stories, target_username)
        if not stories:
            await status_msg.edit("⚠️ لا توجد ستوريات نشطة حالياً.")
            return
            
        await status_msg.edit(f"📥 جاري إرسال `{len(stories)}` ستوري...")
        caption = build_caption(client, f"ستوري @{target_username}")
        for i in range(0, len(stories), 10):
            chunk = stories[i:i+10]
            media_group = [InputMediaVideo(m["url"], caption=caption if idx==0 else "") if m["type"]=="video" else InputMediaPhoto(m["url"], caption=caption if idx==0 else "") for idx, m in enumerate(chunk)]
            try: await client.send_media_group(chat_id, media=media_group)
            except Exception: pass
        await status_msg.delete()
        return

    if callback.from_user.id != OWNER_ID: return
    if data == "admin_stats":
        text = f"📊 **إحصائيات البوت:**\n\n👥 الأعضاء: `{len(db.get('users'))}`\n🚫 المحظورين: `{len(db.get('banned_users'))}`\n⏳ التشغيل: `{get_uptime()}`"
        await callback.message.edit_text(text, reply_markup=callback.message.reply_markup)
    elif data == "admin_broadcast":
        try:
            answer = await client.ask(chat_id, "📣 أرسل الآن رسالة الإذاعة:", timeout=120)
            users = db.get("users")
            await answer.reply(f"⏳ جاري الإذاعة...")
            success = sum([1 for uid in users if (await answer.copy(uid) or True) if not asyncio.sleep(0.05)])
            await client.send_message(chat_id, f"✅ تمت الإذاعة لـ {success} مستخدم.")
        except asyncio.TimeoutError: pass

# ------------------------------------------------------------------------
# معالجات الأوامر والرسائل
# ------------------------------------------------------------------------
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users"): return
    users = db.get("users")
    if user_id not in users:
        users.append(user_id)
        db.set("users", users)
    if not await is_subscribed(client, user_id):
        channel = db.get("force_channel")
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]]))
        return
    await message.reply(db.get("welcome_message").replace("{mention}", message.from_user.mention))

@app.on_message(filters.private & filters.text)
async def central_handler(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users") or not await is_subscribed(client, user_id): return

    text_input = message.text.strip()
    
    if re.match(r"https?://[^\s]+", text_input):
        processing_msg = await message.reply("⏳ **جاري معالجة الرابط والتحميل...**", quote=True)
        try:
            if "instagram.com" in text_input:
                media_list = await asyncio.to_thread(fetch_instagram_post, text_input)
                if not media_list: return await processing_msg.edit("❌ فشل تحميل المنشور.")
                caption = build_caption(client)
                if len(media_list) == 1:
                    if media_list[0]["type"] == "video": await client.send_video(message.chat.id, video=media_list[0]["url"], caption=caption, reply_to_message_id=message.id)
                    else: await client.send_photo(message.chat.id, photo=media_list[0]["url"], caption=caption, reply_to_message_id=message.id)
                elif len(media_list) > 1:
                    media_group = [InputMediaVideo(m["url"], caption=caption if i==0 else "") if m["type"]=="video" else InputMediaPhoto(m["url"], caption=caption if i==0 else "") for i, m in enumerate(media_list[:10])]
                    await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
                await processing_msg.delete()

            elif "tiktok.com" in text_input:
                data = await asyncio.to_thread(extract_tiktok_data, text_input)
                if data["type"] == "video": await client.send_video(message.chat.id, video=data["video_url"], caption=build_caption(client, data.get('title')), reply_to_message_id=message.id)
                await processing_msg.delete()
                
            elif "youtube.com" in text_input or "youtu.be" in text_input:
                data = await asyncio.to_thread(download_youtube_video, text_input)
                try: await client.send_video(message.chat.id, video=data['path'], caption=build_caption(client, data['title']), reply_to_message_id=message.id)
                finally: os.remove(data['path'])
                await processing_msg.delete()
                
            elif "twitter.com" in text_input or "x.com" in text_input:
                media_list = await asyncio.to_thread(extract_twitter_data, text_input)
                if len(media_list) == 1: await client.send_video(message.chat.id, video=media_list[0]["url"], caption=build_caption(client), reply_to_message_id=message.id)
                await processing_msg.delete()
                
            elif "pinterest.com" in text_input or "pin.it" in text_input:
                data = await asyncio.to_thread(extract_pinterest_data, text_input)
                if data["type"] == "video": await client.send_video(message.chat.id, video=data["url"], caption=build_caption(client), reply_to_message_id=message.id)
                else: await client.send_photo(message.chat.id, photo=data["url"], caption=build_caption(client), reply_to_message_id=message.id)
                await processing_msg.delete()
                
            elif "spotify.com" in text_input or "soundcloud.com" in text_input:
                data = await asyncio.to_thread(download_audio_track, text_input)
                try: await client.send_audio(message.chat.id, audio=data['path'], caption=build_caption(client, data['title']), reply_to_message_id=message.id)
                finally: os.remove(data['path'])
                await processing_msg.delete()
            elif "facebook.com" in text_input or "fb.watch" in text_input:
                await processing_msg.edit("⏳ **جاري سحب فيديو الفيسبوك...**")
                data = await asyncio.to_thread(download_facebook_video, text_input)
                if not data: return await processing_msg.edit("❌ فشل تحميل فيديو الفيسبوك.")
                try: await client.send_video(message.chat.id, video=data['path'], caption=build_caption(client, data['title']), reply_to_message_id=message.id)
                finally: os.remove(data['path'])
                await processing_msg.delete()

            elif "snapchat.com" in text_input:
                await processing_msg.edit("⏳ **جاري سحب مقطع السناب شات...**")
                data = await asyncio.to_thread(download_snapchat_video, text_input)
                if not data: return await processing_msg.edit("❌ فشل تحميل مقطع السناب.")
                try: await client.send_video(message.chat.id, video=data['path'], caption=build_caption(client, data['title']), reply_to_message_id=message.id)
                finally: os.remove(data['path'])
                await processing_msg.delete()
        except Exception as e: await processing_msg.edit(f"⚠️ خطأ: `{str(e)}`")
    else:
        username = text_input.replace("@", "").strip()
        if " " in username or len(username) > 30 or "/" in username: return 
        processing_msg = await message.reply("🔍 **جاري فحص الحساب عبر الرادار البديل...**")
        profile = await asyncio.to_thread(fetch_instagram_profile, username)
        if not profile: return await processing_msg.edit("❌ فشل الاتصال بخوادم إنستجرام.")
        profile_card = f"👤 **معلومات البروفايل**\n\n📝 **الاسم المتاح:** {profile['name']}\n🆔 **اليوزر نيم:** @{profile['username']}\n🌐 **حالة الحساب:** {profile['is_private']}\n\n👥 **المتابعين:** `{profile['followers']}`\n📉 **المُتابَعين:** `{profile['following']}`"
        btns = InlineKeyboardMarkup([[InlineKeyboardButton("📥 تحميل الستوريات الحالية", callback_data=f"dl_story_{profile['username']}")]])
        try:
            await client.send_photo(message.chat.id, photo=profile["pic_url"], caption=profile_card, reply_markup=btns, reply_to_message_id=message.id)
            await processing_msg.delete()
        except Exception:
            await message.reply(profile_card, reply_markup=btns, quote=True)
            await processing_msg.delete()

if __name__ == "__main__":
    app.run()
            
