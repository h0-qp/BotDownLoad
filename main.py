import asyncio
import time
import os
import uuid
import re
import cloudscraper
import yt_dlp
import instaloader
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
db = KVSQ("/app/data/bot_data.sqlite")

if not db.exists("users"): db.set("users", [])
if not db.exists("banned_users"): db.set("banned_users", [])
if not db.exists("force_channel"): db.set("force_channel", "None")

if not db.exists("welcome_message"):
    default_welcome = "- مرحبا بك {mention}\n- في بوت تحميل من جميع المواقع \n \nللتحميل ارسل الرابط فقط."
    db.set("welcome_message", default_welcome)

# ------------------------------------------------------------------------
# تهيئة وتجهيز مكتبة Instaloader للتحميل والستوريات
# ------------------------------------------------------------------------
il = instaloader.Instaloader(
    download_pictures=False, download_videos=False, 
    download_video_thumbnails=False, download_geotags=False, 
    download_comments=False, save_metadata=False
)

il.context._session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

SESSION_ID = "54331833835%3A7fPWDGnWJnUZCj%3A22%3AAYdgFUZ8fSyRh7xLnXc_7HnrMxPkQmVUEDI5cUoPLA"
try:
    il.context._session.cookies.set("sessionid", SESSION_ID, domain=".instagram.com")
    print("🔒 Instagram Engine: Session ID Injected!", flush=True)
except Exception as e:
    print(f"⚠️ Instagram Engine Login Error: {e}", flush=True)

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
    if media_title: return f"📝 {media_title}\n\n🤖 {custom_rights}"
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
# 5. محرك الصوتيات (Spotify & SoundCloud)
# ==========================================
def download_audio_track(url: str) -> dict:
    scraper = cloudscraper.create_scraper()
    if "spotify.com" in url:
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            resp = scraper.get(oembed_url, timeout=10)
            if resp.status_code == 200:
                track_title = resp.json().get("title")
                if track_title:
                    ydl_opts = {
                        'outtmpl': f"audio_{uuid.uuid4().hex[:6]}.%(ext)s", 'quiet': True, 'no_warnings': True,
                        'format': 'bestaudio[ext=m4a]/m4a/bestaudio/best', 'noplaylist': True, 'max_filesize': 30 * 1024 * 1024
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(f"ytsearch1:{track_title} audio", download=True)
                        if 'entries' in info and info['entries']:
                            actual_filename = ydl.prepare_filename(info['entries'][0])
                            if os.path.exists(actual_filename): return {"path": actual_filename, "title": track_title}
        except Exception: pass
        return None

    filename = f"audio_{uuid.uuid4().hex[:6]}.mp3"
    instances = ["https://co.wuk.sh/api/json", "https://cobalt.cst.im/api/json", "https://api.cobalt.biz.ua/api/json"]
    for inst in instances:
        try:
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            resp = scraper.post(inst, json={"url": url, "isAudioOnly": True}, headers=headers, timeout=15)
            if resp.status_code == 200 and resp.json().get("status") in ["stream", "redirect"]:
                r = scraper.get(resp.json().get("url"), timeout=30)
                with open(filename, 'wb') as f: f.write(r.content)
                return {"path": filename, "title": resp.json().get("text", "Audio Track 🎵")}
        except Exception: continue
    return None

# ==========================================
# 6. محرك إنستجرام الهجين المتكامل (تخطي حظر 403) 🚀
# ==========================================
def fetch_instagram_post(url: str) -> list:
    try:
        match = re.search(r'/(?:p|reel|tv|share/reel)/([A-Za-z0-9_-]+)', url)
        if not match: return []
        shortcode = match.group(1)
        post = instaloader.Post.from_shortcode(il.context, shortcode)
        media_list = []
        if post.typename == 'GraphSidecar':
            for node in post.get_sidecar_nodes():
                if node.is_video: media_list.append({"type": "video", "url": node.video_url})
                else: media_list.append({"type": "photo", "url": node.display_url})
        else:
            if post.is_video: media_list.append({"type": "video", "url": post.video_url})
            else: media_list.append({"type": "photo", "url": post.display_url})
        return media_list
    except Exception:
        # خط دفاع بديل للتحميل في حال انحظر شوركتكود التابع لـ Instaloader
        try:
            scr = cloudscraper.create_scraper()
            resp = scr.post("https://co.wuk.sh/api/json", json={"url": url}, headers={"Accept": "application/json", "Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200 and resp.json().get("url"):
                return [{"type": "video", "url": resp.json()["url"]}]
        except Exception: pass
    return []

def fetch_instagram_profile(username: str) -> dict:
    """[🔥 تحديث جوهري] جلب البروفايل عبر الـ Scraper المفتوح لتخطي حظر الـ GraphQL 403"""
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        # استخدام دوت كوم الام للبحث السريع وعزل البيانات بدون دالات محظورة
        url = f"https://www.instagram.com/{username}/"
        resp = scraper.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # محاولة استخراج الاسم والبايو من الميتادات المفتوحة للجميع
            title_tag = soup.find("meta", {"property": "og:title"})
            desc_tag = soup.find("meta", {"property": "og:description"})
            img_tag = soup.find("meta", {"property": "og:image"})
            
            name = username
            followers = "غير محدد"
            following = "غير محدد"
            bio = "لم يتم جلب البايو"
            
            if title_tag and title_tag.get("content"):
                name = title_tag["content"].split("•")[0].strip()
            
            if desc_tag and desc_tag.get("content"):
                desc = desc_tag["content"]
                # استخراج المتابعين بالـ Regex الذكي
                f_match = re.search(r'([0-9kM\.,]+)\s*Followers', desc)
                if f_match: followers = f_match.group(1)
                l_match = re.search(r'([0-9kM\.,]+)\s*Following', desc)
                if l_match: following = l_match.group(1)
                
            pic_url = img_tag["content"] if img_tag else "https://telegram.org/img/t_logo.png"
            
            return {
                "name": name, "username": username, "bio": bio,
                "followers": followers, "following": following,
                "is_verified": "Verified" in resp.text,
                "is_private": "🔒 الحساب قد يكون خاصاً" if "isPrivate\":true" in resp.text else "🔓 حساب عام",
                "pic_url": pic_url, "id": "مخفي للآمان"
            }
    except Exception as e:
        print(f"Bypass Profile Error: {e}", flush=True)
    return None

def fetch_instagram_stories(username: str) -> list:
    try:
        profile = instaloader.Profile.from_username(il.context, username)
        stories_media = []
        for story in il.get_stories(userids=[profile.userid]):
            for item in story.get_items():
                if item.is_video: stories_media.append({"type": "video", "url": item.video_url})
                else: stories_media.append({"type": "photo", "url": item.display_url})
        return stories_media
    except Exception:
        # طريقة بديلة لقراءة الستوريات عبر API سحابي سريع ومفتوح في حال حظر السيرفر
        try:
            scr = cloudscraper.create_scraper()
            res = scr.post("https://api.cobalt.biz.ua/api/json", json={"url": f"https://instagram.com/stories/{username}/"}, timeout=10)
            if res.status_code == 200 and res.json().get("picker"):
                return [{"type": "video" if "video" in item["url"] else "photo", "url": item["url"]} for item in res.json()["picker"]]
        except Exception: pass
    return []

# ------------------------------------------------------------------------
# لوحة الإدارة الاحترافية والرسائل
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

@app.on_callback_query()
async def callback_handler(client, callback):
    data = callback.data
    chat_id = callback.message.chat.id
    
    if data.startswith("dl_story_"):
        target_username = data.replace("dl_story_", "")
        await callback.answer("⏳ جاري سحب الستوريات بالخفاء...", show_alert=False)
        status_msg = await client.send_message(chat_id, "⏳ **جاري جلب الستوريات حالياً...**")
        
        stories = await asyncio.to_thread(fetch_instagram_stories, target_username)
        if not stories:
            await status_msg.edit("⚠️ لا توجد ستوريات نشطة حالياً، أو السيرفر تحت الضغط الافتراضي.")
            return
            
        await status_msg.edit(f"📥 جاري إرسال `{len(stories)}` ستوري...")
        caption = build_caption(client, f"ستوري العضو @{target_username}")
        
        for i in range(0, len(stories), 10):
            chunk = stories[i:i+10]
            media_group = [InputMediaVideo(m["url"], caption=caption if idx==0 else "") if m["type"]=="video" else InputMediaPhoto(m["url"], caption=caption if idx==0 else "") for idx, m in enumerate(chunk)]
            try:
                await client.send_media_group(chat_id, media=media_group)
                await asyncio.sleep(1.5)
            except Exception: pass
            
        await status_msg.delete()
        return

    if callback.from_user.id != OWNER_ID: return
    if data == "admin_stats":
        text = f"📊 **إحصائيات البوت:**\n\n👥 الأعضاء النشطين: `{len(db.get('users'))}`\n🚫 المحظورين: `{len(db.get('banned_users'))}`\n⏳ مدة التشغيل: `{get_uptime()}`"
        await callback.message.edit_text(text, reply_markup=callback.message.reply_markup)
    elif data == "admin_broadcast":
        try:
            answer = await client.ask(chat_id, "📣 أرسل الآن رسالة الإذاعة:", timeout=120)
            users = db.get("users")
            await answer.reply(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم...")
            success = sum([1 for uid in users if (await answer.copy(uid) or True) if not asyncio.sleep(0.05)])
            await client.send_message(chat_id, f"✅ تمت الإذاعة لـ {success} مستخدم.")
        except asyncio.TimeoutError: pass

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

@app.on_message(filters.private & filters.text)
async def central_handler(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users"): return
    
    if not await is_subscribed(client, user_id):
        channel = db.get("force_channel")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك أولاً.", reply_markup=btn)
        return

    text_input = message.text.strip()
    
    if re.match(r"https?://[^\s]+", text_input):
        processing_msg = await message.reply("⏳ **جاري معالجة الرابط والتحميل...**", quote=True)
        try:
            if "instagram.com" in text_input:
                await processing_msg.edit("⏳ **جاري سحب ميديا إنستجرام بدقة عالية...**")
                media_list = await asyncio.to_thread(fetch_instagram_post, text_input)
                if not media_list: return await processing_msg.edit("❌ فشل تحميل المنشور. جرب لاحقاً.")
                
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
            elif "twitter.com" in text_input or "x.com" in text_input:
                media_list = await asyncio.to_thread(extract_twitter_data, text_input)
                if len(media_list) == 1: await client.send_video(message.chat.id, video=media_list[0]["url"], caption=build_caption(client), reply_to_message_id=message.id)
                await processing_msg.delete()
            elif "youtube.com" in text_input or "youtu.be" in text_input:
                data = await asyncio.to_thread(download_youtube_video, text_input)
                try: await client.send_video(message.chat.id, video=data['path'], caption=build_caption(client, data['title']), reply_to_message_id=message.id)
                finally: os.remove(data['path'])
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
        except Exception as e: await processing_msg.edit(f"⚠️ خطأ: `{str(e)}`")

    else:
        username = text_input.replace("@", "").strip()
        if " " in username or len(username) > 30 or "/" in username: return 
        
        processing_msg = await message.reply("🔍 **جاري فحص الحساب عبر الرادار البديل...**")
        profile = await asyncio.to_thread(fetch_instagram_profile, username)
        
        if not profile:
            return await processing_msg.edit("❌ فشل الاتصال بخوادم إنستجرام حالياً، يرجى إعادة المحاولة لاحقاً.")
            
        verified_badge = "☑️ موثق" if profile["is_verified"] else ""
        
        profile_card = (
            f"👤 **معلومات البروفايل {verified_badge}**\n\n"
            f"📝 **الاسم المتاح:** {profile['name']}\n"
            f"🆔 **اليوزر نيم:** @{profile['username']}\n"
            f"🌐 **حالة الحساب:** {profile['is_private']}\n\n"
            f"👥 **المتابعين (Followers):** `{profile['followers']}`\n"
            f"📉 **المُتابَعين (Following):** `{profile['following']}`\n"
        )
        
        btns = InlineKeyboardMarkup([[InlineKeyboardButton("📥 تحميل الستوريات الحالية", callback_data=f"dl_story_{profile['username']}")]])
        
        try:
            await client.send_photo(message.chat.id, photo=profile["pic_url"], caption=profile_card, reply_markup=btns, reply_to_message_id=message.id)
            await processing_msg.delete()
        except Exception:
            await message.reply(profile_card, reply_markup=btns, quote=True)
            await processing_msg.delete()

if __name__ == "__main__":
    app.run()
