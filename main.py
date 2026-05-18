import asyncio
import urllib.parse
import requests
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

app = Client("MyBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = KVSQ("bot_data.sqlite")

if not db.exists("users"):
    db.set("users", [])
if not db.exists("force_channel"):
    db.set("force_channel", "None")

# ------------------------------------------------------------------------
# دوال المساعدة والمحركات الأساسية (الهندسة العكسية للمواقع الأربعة)
# ------------------------------------------------------------------------

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

def extract_tiktok_requests(url: str) -> dict:
    """سحب بيانات تيك توك باستخدام requests المعزول لضمان استقرار الـ DNS"""
    clean_url = url.split("?")[0] if "?" in url else url
    api_url = "https://www.tikwm.com/api/"
    data = {"url": clean_url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
    
    def fix_url(link):
        if link and link.startswith("/"): return "https://www.tikwm.com" + link
        return link

    try:
        response = requests.post(api_url, data=data, timeout=15, verify=False)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                body = result.get("data")
                if "images" in body:
                    return {"type": "images", "images": [fix_url(i) for i in body["images"]], "audio": fix_url(body.get("music"))}
                else:
                    return {"type": "video", "video_url": fix_url(body.get("play")), "title": body.get("title")}
    except Exception as e:
        print(f"TikTok Error: {e}", flush=True)
    return None

def extract_instagram_from_your_sites(url: str) -> tuple:
    """
    تفكيك وهندسة المواقع الأربعة التي أرسلتها بالترتيب تسلسلياً
    """
    clean_url = url.split("?")[0]
    if not clean_url.endswith("/"):
        clean_url += "/"
        
    encoded_url = urllib.parse.quote(clean_url)
    media_urls = []
    debug_logs = []
    
    # إعداد هيدرز متكامل لتقليد متصفح حقيقي بالكامل
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    # 1️⃣ الموقع الأول: FastDL (تحليل الـ Ajax المباشر)
    try:
        headers = base_headers.copy()
        headers.update({"Origin": "https://fastdl.app", "Referer": "https://fastdl.app/en2"})
        payload = {"q": clean_url, "t": "media", "lang": "en"}
        
        resp = requests.post("https://fastdl.app/api/ajaxSearch", data=payload, headers=headers, timeout=12, verify=False)
        if resp.status_code == 200:
            html_content = resp.json().get("data", "")
            if html_content:
                soup = BeautifulSoup(html_content, "html.parser")
                for item in soup.find_all("div", class_="download-items"):
                    btn = item.find("a", href=True)
                    if btn:
                        link = btn['href']
                        t = "photo" if any(ext in link.lower() for ext in [".jpg", ".jpeg", ".webp"]) else "video"
                        media_urls.append({"type": t, "url": link})
                if media_urls: return media_urls, debug_logs
            else: debug_logs.append("FastDL: أرجع صفحة فارغة")
        else: debug_logs.append(f"FastDL: HTTP {resp.status_code}")
    except Exception as e: debug_logs.append(f"FastDL Error: {str(e)}")

    # 2️⃣ الموقع الثاني: SSSInstagram (استخراج الـ API الخلفي التابع له)
    try:
        headers = base_headers.copy()
        headers.update({"Origin": "https://sssinstagram.com", "Referer": "https://sssinstagram.com/en1"})
        # يتطلب إرسال الـ JSON مباشرة للسيرفر الخاص بهم
        payload = {"id": clean_url, "locale": "en"}
        resp = requests.post("https://sssinstagram.com/api/v1/instagram/video", json=payload, headers=headers, timeout=12, verify=False)
        if resp.status_code == 200:
            res_json = resp.json()
            data = res_json.get("data") or res_json.get("result") or res_json
            if isinstance(data, list):
                for item in data:
                    link = item.get("url") if isinstance(item, dict) else item
                    if link and str(link).startswith("http"):
                        t = "photo" if any(ext in link.lower() for ext in [".jpg", ".jpeg", ".webp"]) else "video"
                        media_urls.append({"type": t, "url": link})
                if media_urls: return media_urls, debug_logs
            else: debug_logs.append("SSSInstagram: مصفوفة البيانات فارغة")
        else: debug_logs.append(f"SSSInstagram: HTTP {resp.status_code}")
    except Exception as e: debug_logs.append(f"SSSInstagram Error: {str(e)}")

    # 3️⃣ الموقع الثالث: SnapInsta.to (هندسة كود الـ Action المطور)
    try:
        headers = base_headers.copy()
        headers.update({"Origin": "https://snapinsta.to", "Referer": "https://snapinsta.to/en2"})
        payload = {"url": clean_url, "action": "post"}
        resp = requests.post("https://snapinsta.to/action.php", data=payload, headers=headers, timeout=12, verify=False)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                link = a["href"]
                if link.startswith("http") and ("download" in a.text.lower() or "btn" in str(a.get("class"))):
                    t = "photo" if any(ext in link.lower() for ext in [".jpg", ".jpeg", ".webp"]) else "video"
                    media_urls.append({"type": t, "url": link})
            if media_urls: return media_urls, debug_logs
        else: debug_logs.append(f"SnapInsta.to: HTTP {resp.status_code}")
    except Exception as e: debug_logs.append(f"SnapInsta.to Error: {str(e)}")

    # 4️⃣ الموقع الرابع: Inflact (استدعاء محرك الذكاء الاصطناعي الخاص بهم)
    try:
        headers = base_headers.copy()
        headers.update({"Origin": "https://inflact.com", "Referer": "https://inflact.com/instagram-downloader/"})
        api_url = f"https://inflact.com/api/v1/downloader/instagram/?url={encoded_url}"
        resp = requests.get(api_url, headers=headers, timeout=12, verify=False)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items:
                link = item.get("url") or item.get("src")
                if link:
                    t = "photo" if item.get("type") == "image" else "video"
                    media_urls.append({"type": t, "url": link})
            if media_urls: return media_urls, debug_logs
        else: debug_logs.append(f"Inflact: HTTP {resp.status_code}")
    except Exception as e: debug_logs.append(f"Inflact Error: {str(e)}")

    return [], debug_logs


# ------------------------------------------------------------------------
# معالجات الأوامر ولوحة الإدارة
# ------------------------------------------------------------------------

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    users = db.get("users")
    if user_id not in users:
        users.append(user_id)
        db.set("users", users)
        notification_text = (
            "🔔 **عضو جديد في البوت!**\n\n"
            f"👤 الاسم: {message.from_user.first_name}\n"
            f"🆔 الآيدي: `{user_id}`\n"
            f"📊 إجمالي الأعضاء الآن: {len(users)}"
        )
        try: await client.send_message(OWNER_ID, notification_text)
        except: pass

    channel = db.get("force_channel")
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.\nبعد الاشتراك، أرسل /start مجدداً.", reply_markup=btn)
        return

    await message.reply("✅ مرحباً بك! أرسل لي رابط أي فيديو أو منشور من (تيك توك، إنستجرام) وسأقوم بتحميله فوراً.")

@app.on_message(filters.command("admin") & filters.user(OWNER_ID) & filters.private)
async def admin_panel(client, message):
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تغيير قناة الاشتراك", callback_data="change_fsub")],
        [InlineKeyboardButton("📣 إرسال إذاعة", callback_data="broadcast")]
    ])
    await message.reply("مرحباً بك في لوحة الإدارة، اختر الإجراء المطلوب:", reply_markup=btns)

@app.on_callback_query(filters.regex("change_fsub") & filters.user(OWNER_ID))
async def change_force_channel(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "الرجاء إرسال معرف القناة الجديدة (يجب أن يبدأ بـ @):\nلإلغاء الاشتراك الإجباري أرسل 'None'", timeout=60)
        if answer.text:
            new_channel = answer.text.strip()
            db.set("force_channel", new_channel)
            await answer.reply(f"✅ تم حفظ القناة بنجاح!\nالقناة الحالية: {new_channel}")
        else: await answer.reply("❌ الرجاء إرسال نص صالح. تم الإلغاء.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار، تم الإلغاء.")

@app.on_callback_query(filters.regex("broadcast") & filters.user(OWNER_ID))
async def broadcast_message(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "أرسل الآن رسالة الإذاعة:", timeout=120)
        users = db.get("users")
        await answer.reply(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم، يرجى الانتظار...")
        success_count = 0
        for uid in users:
            try:
                await answer.copy(uid)
                success_count += 1
            except: pass
        await client.send_message(chat_id, f"✅ تمت الإذاعة بنجاح لـ {success_count} مستخدم.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار، تم الإلغاء.")


# ------------------------------------------------------------------------
# معالج الروابط ونظام التحميل المتكامل
# ------------------------------------------------------------------------

@app.on_message(filters.regex(r"https?://[^\s]+") & filters.private)
async def media_downloader_router(client, message):
    user_id = message.from_user.id
    users = db.get("users")
    if user_id not in users:
        users.append(user_id)
        db.set("users", users)
    
    channel = db.get("force_channel")
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.", reply_markup=btn)
        return

    url = message.text.strip()
    processing_msg = await message.reply("⏳ **جاري معالجة الرابط عبر الأنظمة العالمية المتطورة...**", quote=True)
    
    try:
        # --- معالجة تيك توك المعززة ---
        if "tiktok.com" in url:
            data = await asyncio.to_thread(extract_tiktok_requests, url)
            if not data: return await processing_msg.edit("❌ فشل استخراج بيانات تيك توك. الرابط معطوب أو خاص.")
            
            if data["type"] == "video":
                await client.send_video(message.chat.id, video=data["video_url"], caption=f"🤖 بواسطة البوت", reply_to_message_id=message.id)
            elif data["type"] == "images":
                media_group = [InputMediaPhoto(img) for img in data["images"]]
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
                if data.get("audio"): await client.send_audio(message.chat.id, audio=data["audio"])
            await processing_msg.delete()

        # --- معالجة إنستجرام بناءً على مواقعك الـ 4 المفضلة ---
        elif "instagram.com" in url:
            # تشغيل السحب في ثريد منفصل لحماية الـ DNS ومنع تجمد البوت
            media_list, debug_logs = await asyncio.to_thread(extract_instagram_from_your_sites, url)
            
            if not media_list:
                error_text = "❌ **فشل استخراج البيانات من المواقع الأربعة المحددة.**\n\n"
                error_text += "🛠️ **سجل تشخيص الأخطاء للشبكة (للمطور):**\n"
                for log in debug_logs: error_text += f"- `{log}`\n"
                return await processing_msg.edit(error_text)
            
            # في حال نجاح الاستخراج من أي موقع
            if len(media_list) == 1:
                media = media_list[0]
                if media["type"] == "video": await client.send_video(message.chat.id, video=media["url"], reply_to_message_id=message.id)
                else: await client.send_photo(message.chat.id, photo=media["url"], reply_to_message_id=message.id)
            elif len(media_list) > 1:
                media_group = []
                for m in media_list[:10]: # حد أقصى 10 وسائط في الرسالة الواحدة لتيليجرام
                    if m["type"] == "video": media_group.append(InputMediaVideo(m["url"]))
                    else: media_group.append(InputMediaPhoto(m["url"]))
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
            await processing_msg.delete()

        else:
            await processing_msg.edit("❌ هذا الرابط غير مدعوم في البوت حالياً.")

    except Exception as e:
        if "WebpageCurlFailed" in str(e):
            await processing_msg.edit("⚠️ تم جلب الفيديو بنجاح، لكن خوادم تيليجرام رفضت رفعه بسبب الحجم الكبير جداً.")
        else:
            await processing_msg.edit(f"⚠️ حدث خطأ تقني غير متوقع: `{str(e)}`")

if __name__ == "__main__":
    print("🤖 Bot is running perfectly with System Network Layer...", flush=True)
    app.run()
    
