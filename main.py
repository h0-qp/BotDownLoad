import asyncio
import time
import cloudscraper
import re
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

START_TIME = time.time() # لحساب وقت تشغيل البوت

app = Client("MyBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = KVSQ("bot_data.sqlite")

# تجهيز قواعد البيانات
if not db.exists("users"): db.set("users", [])
if not db.exists("banned_users"): db.set("banned_users", [])
if not db.exists("force_channel"): db.set("force_channel", "None")

# ------------------------------------------------------------------------
# دوال المساعدة والمحركات الأساسية
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
    except UserNotParticipant:
        return False
    except Exception:
        return True
    return False

# ==========================================
# 1. محرك استخراج التيك توك
# ==========================================
def extract_tiktok_data(url: str) -> dict:
    clean_url = url.split("?")[0] if "?" in url else url
    api_url = "https://www.tikwm.com/api/"
    data = {"url": clean_url, "hd": 1}
    def fix_url(link):
        return "https://www.tikwm.com" + link if link and link.startswith("/") else link

    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.post(api_url, data=data, timeout=15)
        if resp.status_code == 200:
            res = resp.json()
            if res.get("code") == 0:
                body = res.get("data")
                if "images" in body:
                    return {"type": "images", "images": [fix_url(i) for i in body["images"]], "audio": fix_url(body.get("music")), "title": body.get("title")}
                else:
                    return {"type": "video", "video_url": fix_url(body.get("play")), "title": body.get("title")}
    except Exception as e: print(f"TikTok Error: {e}", flush=True)
    return None

# ==========================================
# 2. محرك استخراج بنترست (Pinterest)
# ==========================================
def extract_pinterest_data(url: str) -> dict:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        resp = scraper.get(url, timeout=15)
        if resp.status_code == 200:
            mp4_matches = re.findall(r'https://[^"\'>\\]+\.mp4', resp.text)
            if mp4_matches:
                best_vid = next((v for v in mp4_matches if "720p" in v), mp4_matches[0])
                return {"type": "video", "url": best_vid}
                
            soup = BeautifulSoup(resp.text, "html.parser")
            image_tag = soup.find("meta", {"property": "og:image"}) or soup.find("meta", {"name": "og:image"})
            if image_tag and image_tag.get("content"):
                img_url = image_tag["content"].replace("236x", "originals").replace("474x", "originals").replace("736x", "originals")
                return {"type": "photo", "url": img_url}
    except Exception as e: print(f"Pinterest Error: {e}", flush=True)
    return None

# ==========================================
# 3. محرك يوتيوب وتويتر (X) المتكامل
# ==========================================
def extract_global_media(url: str) -> list:
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    instances = [
        "https://co.wuk.sh/api/json",
        "https://cobalt.cst.im/api/json",
        "https://api.cobalt.biz.ua/api/json"
    ]
    
    for inst in instances:
        try:
            resp = scraper.post(inst, json={"url": url}, headers=headers, timeout=15)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("status") in ["stream", "redirect"]:
                    return [{"type": "video", "url": res.get("url")}]
                elif res.get("status") == "picker":
                    media = []
                    for item in res.get("picker", []):
                        t = "photo" if item.get("type") == "photo" else "video"
                        media.append({"type": t, "url": item.get("url")})
                    return media
        except Exception: continue
    return []

# ==========================================
# 4. محرك استخراج إنستجرام (الخامل حالياً)
# ==========================================
def extract_snapinsta(url: str) -> tuple:
    clean_url = url.split("?")[0]
    media_urls = []
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        scraper.get("https://snapinsta.to/en2", timeout=10)
        api_url = "https://snapinsta.to/api/ajaxSearch"
        headers = {"Origin": "https://snapinsta.to", "Referer": "https://snapinsta.to/en2", "X-Requested-With": "XMLHttpRequest", "Accept": "*/*"}
        resp = scraper.post(api_url, data={"q": clean_url, "t": "media", "v": "v2", "lang": "en"}, headers=headers, timeout=15)
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
# لوحة الإدارة الاحترافية (Admin Panel Pro)
# ------------------------------------------------------------------------

@app.on_message(filters.command("admin") & filters.user(OWNER_ID) & filters.private)
async def admin_panel(client, message):
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 إذاعة (رسالة/ميديا)", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 حظر شخص", callback_data="admin_ban"), InlineKeyboardButton("✅ إلغاء حظر", callback_data="admin_unban")],
        [InlineKeyboardButton("🔄 تغيير قناة الاشتراك", callback_data="change_fsub")]
    ])
    await message.reply("👑 **مرحباً بك في لوحة الإدارة الاحترافية:**\nاختر الإجراء المطلوب من الأزرار أدناه:", reply_markup=btns)

@app.on_callback_query(filters.regex("admin_stats") & filters.user(OWNER_ID))
async def show_stats(client, callback):
    users = db.get("users")
    banned = db.get("banned_users")
    uptime = get_uptime()
    text = f"📊 **إحصائيات البوت:**\n\n👥 الأعضاء النشطين: `{len(users)}`\n🚫 المحظورين: `{len(banned)}`\n⏳ مدة التشغيل: `{uptime}`"
    await callback.answer("تم تحديث الإحصائيات!", show_alert=False)
    await callback.message.edit_text(text, reply_markup=callback.message.reply_markup)

@app.on_callback_query(filters.regex("admin_broadcast") & filters.user(OWNER_ID))
async def broadcast_message(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "📣 أرسل الآن رسالة الإذاعة (تكدر تدز نص، صورة، أو فيديو):", timeout=120)
        users = db.get("users")
        await answer.reply(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم...")
        success = 0
        for uid in users:
            try:
                await answer.copy(uid)
                success += 1
            except: pass
        await client.send_message(chat_id, f"✅ تمت الإذاعة بنجاح لـ {success} مستخدم.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار.")

@app.on_callback_query(filters.regex("admin_ban") & filters.user(OWNER_ID))
async def ban_user(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "🚫 أرسل آيدي (ID) الشخص اللي تريد تحظره:", timeout=60)
        if answer.text and answer.text.isdigit():
            uid = int(answer.text)
            banned = db.get("banned_users")
            if uid not in banned:
                banned.append(uid)
                db.set("banned_users", banned)
            await answer.reply(f"✅ تم حظر المستخدم: `{uid}` بنجاح!")
        else: await answer.reply("❌ الآيدي غير صحيح.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار.")

@app.on_callback_query(filters.regex("admin_unban") & filters.user(OWNER_ID))
async def unban_user(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "✅ أرسل آيدي (ID) الشخص اللي تريد تفك حظره:", timeout=60)
        if answer.text and answer.text.isdigit():
            uid = int(answer.text)
            banned = db.get("banned_users")
            if uid in banned:
                banned.remove(uid)
                db.set("banned_users", banned)
                await answer.reply(f"✅ تم إلغاء حظر المستخدم: `{uid}` بنجاح!")
            else: await answer.reply("⚠️ هذا المستخدم غير محظور أصلاً.")
        else: await answer.reply("❌ الآيدي غير صحيح.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار.")

@app.on_callback_query(filters.regex("change_fsub") & filters.user(OWNER_ID))
async def change_force_channel(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "الرجاء إرسال معرف القناة الجديدة (يجب أن يبدأ بـ @):\nلإلغاء الاشتراك الإجباري أرسل 'None'", timeout=60)
        if answer.text:
            db.set("force_channel", answer.text.strip())
            await answer.reply(f"✅ تم حفظ القناة بنجاح!\nالقناة الحالية: {answer.text.strip()}")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ تم الإلغاء.")

# ------------------------------------------------------------------------
# معالجات الأوامر الأساسية (كليشة الترحيب الجديدة)
# ------------------------------------------------------------------------

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users"): return # تجاهل المحظورين
    
    users = db.get("users")
    if user_id not in users:
        users.append(user_id)
        db.set("users", users)
        try: await client.send_message(OWNER_ID, f"🔔 **عضو جديد:**\nالاسم: {message.from_user.first_name}\nالآيدي: `{user_id}`")
        except: pass

    channel = db.get("force_channel")
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.", reply_markup=btn)
        return

    # الكليشة الجديدة المطلوبة مع المنشن الاحترافي
    welcome_text = (
        f"- مرحبا بك {message.from_user.mention}\n"
        f"- في بوت تحميل من جميع المواقع \n\n"
        f"للتحميل ارسل الرابط فقط."
    )
    await message.reply(welcome_text)

# ------------------------------------------------------------------------
# معالج الروابط ونظام التحميل
# ------------------------------------------------------------------------

@app.on_message(filters.regex(r"https?://[^\s]+") & filters.private)
async def media_downloader_router(client, message):
    user_id = message.from_user.id
    if user_id in db.get("banned_users"): return # لا يرد على المحظورين
    
    users = db.get("users")
    if user_id not in users:
        users.append(user_id)
        db.set("users", users)
    
    channel = db.get("force_channel")
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك أولاً.", reply_markup=btn)
        return

    url = message.text.strip()
    processing_msg = await message.reply("⏳ **جاري التحميل...**", quote=True)
    
    try:
        # ==========================================
        # قسم يوتيوب (Shorts) و تويتر (X)
        # ==========================================
        if any(domain in url for domain in ["youtube.com", "youtu.be", "twitter.com", "x.com"]):
            media_list = await asyncio.to_thread(extract_global_media, url)
            if not media_list: return await processing_msg.edit("❌ فشل استخراج البيانات. الرابط معطوب أو غير متاح.")
            
            if len(media_list) == 1:
                media = media_list[0]
                if media["type"] == "video": await client.send_video(message.chat.id, video=media["url"], caption="🤖 بواسطة البوت", reply_to_message_id=message.id)
                else: await client.send_photo(message.chat.id, photo=media["url"], caption="🤖 بواسطة البوت", reply_to_message_id=message.id)
            elif len(media_list) > 1:
                media_group = []
                for m in media_list[:10]:
                    if m["type"] == "video": media_group.append(InputMediaVideo(m["url"]))
                    else: media_group.append(InputMediaPhoto(m["url"]))
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
            await processing_msg.delete()

        # ==========================================
        # قسم التيك توك
        # ==========================================
        elif "tiktok.com" in url:
            data = await asyncio.to_thread(extract_tiktok_data, url)
            if not data: return await processing_msg.edit("❌ فشل استخراج بيانات تيك توك.")
            
            if data["type"] == "video":
                caption_text = f"📝 {data.get('title', '')}\n\n🤖 بواسطة البوت" if data.get('title') else "🤖 بواسطة البوت"
                await client.send_video(message.chat.id, video=data["video_url"], caption=caption_text, reply_to_message_id=message.id)
            elif data["type"] == "images":
                images = data["images"]
                for i in range(0, len(images), 10):
                    chunk = images[i:i + 10]
                    media_group = [InputMediaPhoto(img) for img in chunk]
                    await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
                    await asyncio.sleep(1.5)
                title = data.get("title")
                if title: await client.send_message(message.chat.id, text=f"📝 **العنوان:**\n{title}\n\n🤖 بواسطة البوت", reply_to_message_id=message.id)
                if data.get("audio"): await client.send_audio(message.chat.id, audio=data["audio"], reply_to_message_id=message.id)
            await processing_msg.delete()

        # ==========================================
        # قسم بنترست
        # ==========================================
        elif "pinterest.com" in url or "pin.it" in url:
            data = await asyncio.to_thread(extract_pinterest_data, url)
            if not data: return await processing_msg.edit("❌ فشل استخراج البيانات من بنترست.")
            
            if data["type"] == "video": await client.send_video(message.chat.id, video=data["url"], caption="🤖 بواسطة البوت", reply_to_message_id=message.id)
            else: await client.send_photo(message.chat.id, photo=data["url"], caption="🤖 بواسطة البوت", reply_to_message_id=message.id)
            await processing_msg.delete()

        # ==========================================
        # قسم إنستجرام
        # ==========================================
        elif "instagram.com" in url:
            media_list, debug = await asyncio.to_thread(extract_snapinsta, url)
            if not media_list: return await processing_msg.edit("❌ **فشل استخراج البيانات.** السيرفر لا يستجيب.")
            
            if len(media_list) == 1:
                media = media_list[0]
                if media["type"] == "video": await client.send_video(message.chat.id, video=media["url"], reply_to_message_id=message.id)
                else: await client.send_photo(message.chat.id, photo=media["url"], reply_to_message_id=message.id)
            elif len(media_list) > 1:
                media_group = []
                for m in media_list[:10]:
                    if m["type"] == "video": media_group.append(InputMediaVideo(m["url"]))
                    else: media_group.append(InputMediaPhoto(m["url"]))
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
            await processing_msg.delete()

        else:
            await processing_msg.edit("❌ هذا الرابط غير مدعوم حالياً.")

    except Exception as e:
        if "WebpageCurlFailed" in str(e):
            await processing_msg.edit("⚠️ تم جلب الرابط، لكن تيليجرام رفض رفعه لحجمه. جرب رابطاً آخر.")
        else:
            await processing_msg.edit(f"⚠️ حدث خطأ تقني: `{str(e)}`")

if __name__ == "__main__":
    print("🤖 Bot is running with the new Welcome Template...", flush=True)
    app.run()
        
