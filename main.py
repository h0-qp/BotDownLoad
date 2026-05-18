import asyncio
import urllib.parse
import cloudscraper
from bs4 import BeautifulSoup
from pyrogram import filters, enums
from pyromod import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from pyrogram.errors import UserNotParticipant
from kvsqlite.sync import Client as KVSQ

# ------------------------------------------------------------------------
# الإعدادات الأساسية
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
# دوال المساعدة والمحركات الأساسية
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

def extract_tiktok(url: str) -> dict:
    """استخراج تيك توك باستخدام الموقع الثابت"""
    clean_url = url.split("?")[0] if "?" in url else url
    api_url = "https://www.tikwm.com/api/"
    data = {"url": clean_url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
    
    def fix_url(link):
        if link and link.startswith("/"): return "https://www.tikwm.com" + link
        return link

    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.post(api_url, data=data, timeout=15)
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

def extract_instagram_sharaf(url: str) -> list:
    """استخراج إنستجرام بالاعتماد على موقع واحد ثابت وتخطي الحماية باقتراحك (Cloudscraper)"""
    clean_url = url.split("?")[0]
    media_urls = []
    
    # تهيئة كاسر الحماية ليقلد متصفح جوجل كروم على ويندوز
    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    })
    
    # موقع SaveIG (الأقوى والأثبت عالمياً، ومعاه FastDL كاحتياط صامت)
    sites = [
        ("https://saveig.app/api/ajaxSearch", "https://saveig.app"),
        ("https://fastdl.app/api/ajaxSearch", "https://fastdl.app")
    ]
    
    for api_url, origin in sites:
        payload = {"q": clean_url, "t": "media", "lang": "en"}
        headers = {
            "Origin": origin, 
            "Referer": origin + "/", 
            "X-Requested-With": "XMLHttpRequest"
        }
        
        try:
            resp = scraper.post(api_url, data=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                html_data = resp.json().get("data", "")
                if html_data:
                    soup = BeautifulSoup(html_data, "html.parser")
                    for item in soup.find_all("div", class_="download-items"):
                        btn = item.find("a", href=True)
                        if btn:
                            link = btn['href']
                            t = "photo" if any(ext in link.lower() for ext in [".jpg", ".jpeg", ".webp", ".png"]) else "video"
                            media_urls.append({"type": t, "url": link})
                    
                    # إذا جلبنا الروابط بنجاح، نخرج من اللوب فوراً
                    if media_urls: 
                        return media_urls
        except Exception:
            continue
            
    return media_urls

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
        try: await client.send_message(OWNER_ID, f"🔔 **عضو جديد:**\nالاسم: {message.from_user.first_name}\nالآيدي: `{user_id}`\nإجمالي الأعضاء: {len(users)}")
        except: pass

    channel = db.get("force_channel")
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]])
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.", reply_markup=btn)
        return

    await message.reply("✅ مرحباً بك! أرسل لي رابط أي فيديو أو منشور من (تيك توك، إنستجرام) وسأقوم بتحميله فوراً.")

@app.on_message(filters.command("admin") & filters.user(OWNER_ID) & filters.private)
async def admin_panel(client, message):
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تغيير قناة الاشتراك", callback_data="change_fsub")],
        [InlineKeyboardButton("📣 إرسال إذاعة", callback_data="broadcast")]
    ])
    await message.reply("مرحباً بك في لوحة الإدارة:", reply_markup=btns)

@app.on_callback_query(filters.regex("change_fsub") & filters.user(OWNER_ID))
async def change_force_channel(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "الرجاء إرسال معرف القناة الجديدة (يجب أن يبدأ بـ @):\nلإلغاء الاشتراك الإجباري أرسل 'None'", timeout=60)
        if answer.text:
            db.set("force_channel", answer.text.strip())
            await answer.reply(f"✅ تم حفظ القناة بنجاح: {answer.text.strip()}")
        else: await answer.reply("❌ تم الإلغاء.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار.")

@app.on_callback_query(filters.regex("broadcast") & filters.user(OWNER_ID))
async def broadcast_message(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "أرسل الآن رسالة الإذاعة:", timeout=120)
        users = db.get("users")
        await answer.reply(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم...")
        success = 0
        for uid in users:
            try:
                await answer.copy(uid)
                success += 1
            except: pass
        await client.send_message(chat_id, f"✅ تمت الإذاعة لـ {success} مستخدم.")
    except asyncio.TimeoutError: await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار.")

# ------------------------------------------------------------------------
# معالج الروابط ونظام التحميل
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
        await message.reply("عذراً، يجب عليك الاشتراك أولاً.", reply_markup=btn)
        return

    url = message.text.strip()
    processing_msg = await message.reply("⏳ **جاري التحميل...**", quote=True)
    
    try:
        if "tiktok.com" in url:
            data = await asyncio.to_thread(extract_tiktok, url)
            if not data: return await processing_msg.edit("❌ فشل استخراج بيانات تيك توك.")
            
            if data["type"] == "video":
                await client.send_video(message.chat.id, video=data["video_url"], caption="🤖 بواسطة البوت", reply_to_message_id=message.id)
            elif data["type"] == "images":
                media_group = [InputMediaPhoto(img) for img in data["images"]]
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
                if data.get("audio"): await client.send_audio(message.chat.id, audio=data["audio"])
            await processing_msg.delete()

        elif "instagram.com" in url:
            media_list = await asyncio.to_thread(extract_instagram_sharaf, url)
            
            if not media_list:
                return await processing_msg.edit("❌ **فشل استخراج البيانات.** تأكد أن الحساب عام وليس خاصاً.")
            
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
        await processing_msg.edit(f"⚠️ حدث خطأ تقني: `{str(e)}`")

if __name__ == "__main__":
    print("🤖 Bot is running with Cloudscraper Bypass...", flush=True)
    app.run()
    
