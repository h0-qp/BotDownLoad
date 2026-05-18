import asyncio
import time
import os
import uuid
import re
import cloudscraper
import yt_dlp
from bs4 import BeautifulSoup
from pyrogram import filters, enums
from pyromod import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from pyrogram.errors import UserNotParticipant
from kvsqlite.sync import Client as KVSQ

# ------------------------------------------------------------------------
# الإعدادات الأساسية الخاصة بك
# ------------------------------------------------------------------------
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
    default_welcome = "- مرحبا بك {mention}\n- في بوت تحميل من جميع المواقع \n \nللتحميل ارسل الرابط فقط."
    db.set("welcome_message", default_welcome)

# ------------------------------------------------------------------------
# دوال المساعدة والنظام
# ------------------------------------------------------------------------

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
        if member.status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except UserNotParticipant: return False
    except Exception: return True
    return False

def build_caption(client, media_title=""):
    custom_rights = db.get("caption_rights") if db.exists("caption_rights") else None
    if not custom_rights:
        bot_username = client.me.username if client.me else "Bot"
        custom_rights = f"تم التحميل بواسطة @{bot_username}"
    
    if media_title:
        return f"📝 {media_title}\n\n🤖 {custom_rights}"
    return f"🤖 {custom_rights}"

# ==========================================
# 1. محرك استخراج التيك توك
# ==========================================
def extract_tiktok_data(url: str) -> dict:
    clean_url = url.split("?")[0] if "?" in url else url
    api_url = "https://www.tikwm.com/api/"
    data = {"url": clean_url, "hd": 1}
    def fix_url(link): return "https://www.tikwm.com" + link if link and link.startswith("/") else link
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.post(api_url, data=data, timeout=15)
        if resp.status_code == 200:
            res = resp.json()
            if res.get("code") == 0:
                body = res.get("data")
                if "images" in body:
                    return {"type": "images", "images": [fix_url(i) for i in body["images"]], "audio": fix_url(body.get("music")), "title": body.get("title")}
                else: return {"type": "video", "video_url": fix_url(body.get("play")), "title": body.get("title")}
    except Exception: pass
    return None

# ==========================================
# 2. محرك استخراج بنترست 
# ==========================================
def extract_pinterest_data(url: str) -> dict:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        resp = scraper.get(url, timeout=15)
        if resp.status_code == 200:
            mp4_matches = re.findall(r'https://[^"\'>\\]+\.mp4', resp.text)
            if mp4_matches: return {"type": "video", "url": next((v for v in mp4_matches if "720p" in v), mp4_matches[0])}
            soup = BeautifulSoup(resp.text, "html.parser")
            image_tag = soup.find("meta", {"property": "og:image"}) or soup.find("meta", {"name": "og:image"})
            if image_tag and image_tag.get("content"):
                img_url = image_tag["content"].replace("236x", "originals").replace("474x", "originals").replace("736x", "originals")
                return {"type": "photo", "url": img_url}
    except Exception: pass
    return None

# ==========================================
# 3. محرك يوتيوب
# ==========================================
def download_youtube_video(url: str) -> dict:
    filename = f"temp_{uuid.uuid4().hex[:6]}.mp4"
    ydl_opts = {'outtmpl': filename, 'quiet': True, 'no_warnings': True, 'format': 'b[ext=mp4]/best', 'max_filesize': 50 * 1024 * 1024}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if os.path.exists(filename): return {"path": filename, "title": info.get("title", "")}
    except Exception:
        if os.path.exists(filename): os.remove(filename)
    return None

# ==========================================
# 4. محرك تويتر / X 
# ==========================================
def extract_twitter_data(url: str) -> list:
    match = re.search(r'(?:twitter\.com|x\.com)/([^/]+/status/\d+)', url)
    if not match: return []
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(f"https://api.vxtwitter.com/{match.group(1)}", timeout=10)
        if resp.status_code == 200:
            media_list = []
            for m in resp.json().get("media_extended", []):
                if m["type"] == "image": media_list.append({"type": "photo", "url": m["url"]})
                elif m["type"] in ["video", "gif"]: media_list.append({"type": "video", "url": m["url"]})
            return media_list
    except Exception: pass
    return []

# ==========================================
# 5. محرك الصوتيات (تخطي حماية سبوتيفاي الذكي 🚀)
# ==========================================
def download_audio_track(url: str) -> dict:
    scraper = cloudscraper.create_scraper()
    
    # 🎧 التكتيك الذكي لسبوتيفاي (جلب الاسم والتحميل من يوتيوب)
    if "spotify.com" in url:
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            resp = scraper.get(oembed_url, timeout=10)
            if resp.status_code == 200:
                track_title = resp.json().get("title") # اسم الأغنية والفنان
                if track_title:
                    ydl_opts = {
                        'outtmpl': f"audio_{uuid.uuid4().hex[:6]}.%(ext)s", 
                        'quiet': True, 'no_warnings': True,
                        'format': 'bestaudio/best', 'noplaylist': True,
                        'max_filesize': 30 * 1024 * 1024
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # البحث في يوتيوب وتحميل أول نتيجة كملف صوتي
                        info = ydl.extract_info(f"ytsearch1:{track_title} audio", download=True)
                        if 'entries' in info and info['entries']:
                            entry = info['entries'][0]
                            actual_filename = ydl.prepare_filename(entry)
                            if os.path.exists(actual_filename):
                                return {"path": actual_filename, "title": track_title}
        except Exception as e:
            print(f"Spotify Bypass Error: {e}", flush=True)
        return None

    # 🎧 ساوند كلاود وباقي المنصات الصوتية (تعمل بشكل ممتاز)
    filename = f"audio_{uuid.uuid4().hex[:6]}.mp3"
    instances = ["https://co.wuk.sh/api/json", "https://cobalt.cst.im/api/json", "https://api.cobalt.biz.ua/api/json"]
    for inst in instances:
        try:
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            resp = scraper.post(inst, json={"url": url, "isAudioOnly": True}, headers=headers, timeout=15)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("status") in ["stream", "redirect"]:
                    r = scraper.get(res.get("url"), timeout=30)
                    with open(filename, 'wb') as f:
                        f.write(r.content)
                    return {"path": filename, "title": res.get("text", "Audio Track 🎵")}
        except Exception: continue
            
    ydl_opts = {'outtmpl': filename, 'quiet': True, 'no_warnings': True, 'format': 'bestaudio/best'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            actual_filename = ydl.prepare_filename(info)
            if os.path.exists(actual_filename):
                return {"path": actual_filename, "title": info.get("title", "Audio Track 🎵")}
    except Exception:
        if os.path.exists(filename): os.remove(filename)
    return None

# ==========================================
# 6. محرك استخراج إنستجرام 
# ==========================================
def extract_snapinsta(url: str) -> tuple:
    clean_url = url.split("?")[0]
    media_urls = []
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        scraper.get("https://snapinsta.to/en2", timeout=10)
        resp = scraper.post("https://snapinsta.to/api/ajaxSearch", data={"q": clean_url, "t": "media", "v": "v2", "lang": "en"}, timeout=15)
        if resp.status_code == 200 and resp.json().get("data"):
            soup = BeautifulSoup(resp.json()["data"], "html.parser")
            for item in soup.find_all("div", class_="download-items"):
                btn = item.find("a", href=True)
                if btn:
                    t = "photo" if any(ext in btn['href'].lower() for ext in [".jpg", ".jpeg", ".webp"]) else "video"
                    media_urls.append({"type": t, "url": btn['href']})
    except Exception: pass
    return media_urls, []

# ------------------------------------------------------------------------
# لوحة الإدارة الاحترافية 
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
    await message.reply("👑 **مرحباً بك في لوحة الإدارة الاحترافية:**\nاختر الإجراء المطلوب من الأزرار أدناه:", reply_markup=btns)

@app.on_callback_query(filters.user(OWNER_ID))
async def admin_callbacks(client, callback):
    data = callback.data
    chat_id = callback.message.chat.id
    
    if data == "admin_stats":
        text = f"📊 **إحصائيات البوت:**\n\n👥 الأعضاء النشطين: `{len(db.get('users'))}`\n🚫 المحظورين: `{len(db.get('banned_users'))}`\n⏳ مدة التشغيل: `{get_uptime()}`"
        await callback.answer("تم التحديث!")
        await callback.message.edit_text(text, reply_markup=callback.message.reply_markup)

    elif data == "admin_broadcast":
        try:
            answer = await client.ask(chat_id, "📣 أرسل الآن رسالة الإذاعة:", timeout=120)
            users = db.get("users")
            await answer.reply(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم...")
            success = sum([1 for uid in users if (await answer.copy(uid) or True) if not asyncio.sleep(0.05)])
            await client.send_message(chat_id, f"✅ تمت الإذاعة لـ {success} مستخدم.")
        except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى الوقت.")

    elif data in ["admin_ban", "admin_unban"]:
        action = "تحظره" if data == "admin_ban" else "تفك حظره"
        try:
            answer = await client.ask(chat_id, f"أرسل آيدي (ID) الشخص اللي تريد {action}:", timeout=60)
            if answer.text and answer.text.isdigit():
                uid = int(answer.text)
                banned = db.get("banned_users")
                if data == "admin_ban" and uid not in banned: banned.append(uid)
                elif data == "admin_unban" and uid in banned: banned.remove(uid)
                db.set("banned_users", banned)
                await answer.reply(f"✅ تمت العملية بنجاح للمستخدم: `{uid}`")
        except asyncio.TimeoutError: pass

    elif data == "change_fsub":
        try:
            answer = await client.ask(chat_id, "الرجاء إرسال معرف القناة الجديدة:\nلإلغاء الاشتراك أرسل 'None'", timeout=60)
            if answer.text:
                db.set("force_channel", answer.text.strip())
                await answer.reply(f"✅ تم الحفظ: {answer.text.strip()}")
        except asyncio.TimeoutError: pass

    elif data == "change_welcome":
        try:
            answer = await client.ask(chat_id, "📝 أرسل كليشة الترحيب الجديدة:", timeout=120)
            if answer.text:
                db.set("welcome_message", answer.text.strip())
                await answer.reply("✅ تم حفظ كليشة الترحيب!")
        except asyncio.TimeoutError: pass

    elif data == "change_rights":
        try:
            answer = await client.ask(chat_id, "🏷️ أرسل نص الحقوق (أو 'None' للعودة ليوزر البوت):", timeout=120)
            if answer.text:
                if answer.text.strip().lower() == "none":
                    if db.exists("caption_rights"): db.delete("caption_rights")
                else: db.set("caption_rights", answer.text.strip())
                await answer.reply("✅ تم تحديث الحقوق بنجاح!")
        except asyncio.TimeoutError: pass

# ------------------------------------------------------------------------
# معالجات الأوامر الأساسية 
# ------------------------------------------------------------------------

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users"): return
    
    users = db.get("users")
    if user_id not in users:
        users.append(user_id)
        db.set("users", users)
        try: await client.send_message(OWNER_ID, f"🔔 **عضو جديد:**\nالاسم: {message.from_user.first_name}\nالآيدي: `{user_id}`")
        except: pass

    if not await is_subscribed(client, user_id):
        channel = db.get("force_channel")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.", reply_markup=btn)
        return

    welcome_template = db.get("welcome_message")
    await message.reply(welcome_template.replace("{mention}", message.from_user.mention))

# ------------------------------------------------------------------------
# معالج الروابط المتكامل
# ------------------------------------------------------------------------

@app.on_message(filters.regex(r"https?://[^\s]+") & filters.private)
async def media_downloader_router(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users"): return
    
    if not await is_subscribed(client, user_id):
        channel = db.get("force_channel")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك أولاً.", reply_markup=btn)
        return

    url = message.text.strip()
    processing_msg = await message.reply("⏳ **جاري معالجة الرابط والتحميل...**", quote=True)
    
    try:
        # ==========================================
        # قسم سبوتيفاي وساوند كلاود 🎵
        # ==========================================
        if "spotify.com" in url or "soundcloud.com" in url:
            await processing_msg.edit("⏳ **جاري سحب الملف الصوتي بدقة عالية...**")
            data = await asyncio.to_thread(download_audio_track, url)
            if not data: 
                return await processing_msg.edit("❌ فشل تحميل التراك الصوتي. الرابط غير متاح أو الأغنية غير متوفرة.")
            
            caption = build_caption(client, data['title'])
            try: await client.send_audio(message.chat.id, audio=data['path'], caption=caption, reply_to_message_id=message.id)
            finally:
                if os.path.exists(data['path']): os.remove(data['path'])
            await processing_msg.delete()

        # ==========================================
        # قسم تويتر (X) 
        # ==========================================
        elif "twitter.com" in url or "x.com" in url:
            media_list = await asyncio.to_thread(extract_twitter_data, url)
            if not media_list: return await processing_msg.edit("❌ فشل التحميل أو التغردية فارغة.")
            
            caption = build_caption(client)
            if len(media_list) == 1:
                if media_list[0]["type"] == "video": await client.send_video(message.chat.id, video=media_list[0]["url"], caption=caption, reply_to_message_id=message.id)
                else: await client.send_photo(message.chat.id, photo=media_list[0]["url"], caption=caption, reply_to_message_id=message.id)
            elif len(media_list) > 1:
                media_group = [InputMediaVideo(m["url"], caption=caption if i==0 else "") if m["type"]=="video" else InputMediaPhoto(m["url"], caption=caption if i==0 else "") for i,m in enumerate(media_list[:4])]
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
            await processing_msg.delete()

        # ==========================================
        # قسم يوتيوب
        # ==========================================
        elif "youtube.com" in url or "youtu.be" in url:
            data = await asyncio.to_thread(download_youtube_video, url)
            if not data: return await processing_msg.edit("❌ فشل التحميل أو حجم الفيديو كبير.")
            caption = build_caption(client, data['title'])
            try: await client.send_video(message.chat.id, video=data['path'], caption=caption, reply_to_message_id=message.id)
            finally:
                if os.path.exists(data['path']): os.remove(data['path']) 
            await processing_msg.delete()

        # ==========================================
        # قسم التيك توك 
        # ==========================================
        elif "tiktok.com" in url:
            data = await asyncio.to_thread(extract_tiktok_data, url)
            if not data: return await processing_msg.edit("❌ فشل جلب بيانات تيك توك.")
            
            if data["type"] == "video":
                caption = build_caption(client, data.get('title'))
                await client.send_video(message.chat.id, video=data["video_url"], caption=caption, reply_to_message_id=message.id)
            elif data["type"] == "images":
                for i in range(0, len(data["images"]), 10):
                    media_group = [InputMediaPhoto(img) for img in data["images"][i:i+10]]
                    await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
                    await asyncio.sleep(1.5)
                await client.send_message(message.chat.id, text=build_caption(client, data.get("title")), reply_to_message_id=message.id)
                if data.get("audio"): await client.send_audio(message.chat.id, audio=data["audio"], reply_to_message_id=message.id)
            await processing_msg.delete()

        # ==========================================
        # قسم بنترست 
        # ==============================
        elif "pinterest.com" in url or "pin.it" in url:
            data = await asyncio.to_thread(extract_pinterest_data, url)
            if not data: return await processing_msg.edit("❌ فشل استخراج بيانات بنترست.")
            caption = build_caption(client)
            if data["type"] == "video": await client.send_video(message.chat.id, video=data["url"], caption=caption, reply_to_message_id=message.id)
            else: await client.send_photo(message.chat.id, photo=data["url"], caption=caption, reply_to_message_id=message.id)
            await processing_msg.delete()

        # ==========================================
        # قسم إنستجرام 
        # ==========================================
        elif "instagram.com" in url:
            media_list, _ = await asyncio.to_thread(extract_snapinsta, url)
            if not media_list: return await processing_msg.edit("❌ السيرفر لا يستجيب حالياً لإنستجرام.")
            caption = build_caption(client)
            if len(media_list) == 1:
                if media_list[0]["type"] == "video": await client.send_video(message.chat.id, video=media_list[0]["url"], caption=caption, reply_to_message_id=message.id)
                else: await client.send_photo(message.chat.id, photo=media_list[0]["url"], caption=caption, reply_to_message_id=message.id)
            elif len(media_list) > 1:
                media_group = [InputMediaVideo(m["url"], caption=caption if i==0 else "") if m["type"]=="video" else InputMediaPhoto(m["url"], caption=caption if i==0 else "") for i,m in enumerate(media_list[:10])]
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
            await processing_msg.delete()

        else: await processing_msg.edit("❌ هذا الرابط غير مدعوم حالياً.")

    except Exception as e: await processing_msg.edit(f"⚠️ خطأ تقني: `{str(e)}`")

if __name__ == "__main__":
    print("🤖 Bot is running with Smart Spotify Bypass...", flush=True)
    app.run()
