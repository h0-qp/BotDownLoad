import asyncio
import re
import aiohttp
from bs4 import BeautifulSoup
from pyrogram import filters, enums
from pyromod import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from pyrogram.errors import UserNotParticipant
from kvsqlite.sync import Client as KVSQ

# ------------------------------------------------------------------------
# الإعدادات الأساسية
# ------------------------------------------------------------------------
API_ID = 12588588  # استبدل بـ API_ID الخاص بك
API_HASH = "f2e0652152a45a25dc70f5bed7907d6e"
BOT_TOKEN = "8509012164:AAEfJcqsprCSlN2BHBX2td4UitXvK_Cu4nc"
OWNER_ID = 1160471152  # استبدل بـ الآيدي (ID) الخاص بك لتلقي الإشعارات والتحكم

# تهيئة البوت وقاعدة البيانات
app = Client("MyBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = KVSQ("bot_data.sqlite")
# إعداد قيم قاعدة البيانات الافتراضية
if not db.exists("users"):
    db.set("users", [])
if not db.exists("force_channel"):
    db.set("force_channel", "None")


# ------------------------------------------------------------------------
# دوال المساعدة والمحركات الأساسية (Helpers & Scrapers)
# ------------------------------------------------------------------------

async def is_subscribed(client, user_id):
    """التحقق من اشتراك المستخدم في القناة الإجبارية"""
    channel = db.get("force_channel")
    if channel == "None":
        return True
    try:
        member = await client.get_chat_member(channel, user_id)
        if member.status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except UserNotParticipant:
        return False
    except Exception:
        return True
    return False

async def fetch_tiktok_data(url: str) -> dict:
    """استخراج بيانات تيك توك عبر API خلفي (محدث)"""
    api_url = "https://www.tikwm.com/api/"
    data = {"url": url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
    
    # دالة فرعية لإصلاح الروابط الناقصة التي يرسلها الـ API
    def fix_url(link):
        if link and link.startswith("/"):
            return "https://www.tikwm.com" + link
        return link

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=data) as response:
            if response.status != 200:
                return None
            result = await response.json()
            if result.get("code") == 0:
                body = result.get("data")
                if "images" in body:
                    return {
                        "type": "images",
                        "images": [fix_url(img) for img in body["images"]],
                        "audio": fix_url(body.get("music"))
                    }
                else:
                    return {
                        "type": "video",
                        "video_url": fix_url(body.get("play")),
                        "title": body.get("title")
                    }
            return None

async def fetch_instagram_data(url: str) -> list:
    """استخراج بيانات إنستجرام عبر الهندسة العكسية (محدث)"""
    # تم تغيير الدومين المعطل إلى الدومين الرئيسي
    api_url = "https://saveig.app/api/ajaxSearch" 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://saveig.app",
        "Referer": "https://saveig.app/en"
    }
    payload = {"q": url, "t": "media", "lang": "en"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=payload, headers=headers) as response:
            if response.status != 200:
                return []
            result = await response.json()
            html_data = result.get("data", "")
            if not html_data:
                return []
            soup = BeautifulSoup(html_data, "html.parser")
            download_items = soup.find_all("div", class_="download-items")
            media_urls = []
            for item in download_items:
                btn = item.find("a", href=True)
                if btn:
                    link = btn['href']
                    if ".jpg" in link or ".webp" in link or ".png" in link:
                        media_urls.append({"type": "photo", "url": link})
                    else:
                        media_urls.append({"type": "video", "url": link})
            return media_urls


# ------------------------------------------------------------------------
# معالجات الأوامر (Command Handlers)
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
        try:
            await client.send_message(OWNER_ID, notification_text)
        except Exception:
            pass

    channel = db.get("force_channel")
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]
        ])
        await message.reply(
            "عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.\nبعد الاشتراك، أرسل /start مجدداً.",
            reply_markup=btn
        )
        return

    await message.reply("✅ مرحباً بك! أرسل لي رابط أي فيديو أو منشور من (تيك توك، إنستجرام) وسأقوم بتحميله فوراً.")


# ------------------------------------------------------------------------
# لوحة التحكم والإدارة (Admin Panel & Broadcasting)
# ------------------------------------------------------------------------

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
        else:
            await answer.reply("❌ الرجاء إرسال نص صالح. تم الإلغاء.")
    except asyncio.TimeoutError:
        await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار، تم الإلغاء.")


@app.on_callback_query(filters.regex("broadcast") & filters.user(OWNER_ID))
async def broadcast_message(client, callback):
    chat_id = callback.message.chat.id
    try:
        answer = await client.ask(chat_id, "أرسل الآن رسالة الإذاعة (نص، صورة، فيديو، ملصق، إلخ):", timeout=120)
        users = db.get("users")
        await answer.reply(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم، يرجى الانتظار...")
        
        success_count = 0
        for uid in users:
            try:
                await answer.copy(uid)
                success_count += 1
            except Exception:
                pass
                
        await client.send_message(chat_id, f"✅ تمت الإذاعة بنجاح لـ {success_count} مستخدم.")
    except asyncio.TimeoutError:
        await client.send_message(chat_id, "⏱️ انتهى وقت الانتظار، تم الإلغاء.")


# ------------------------------------------------------------------------
# معالج الروابط ونظام التحميل (Media Downloader Router)
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
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 اضغط هنا للاشتراك", url=f"https://t.me/{channel.replace('@', '')}")]
        ])
        await message.reply(
            "عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.",
            reply_markup=btn
        )
        return

    url = message.text.strip()
    processing_msg = await message.reply("⏳ **جاري معالجة الرابط واستخراج البيانات...**", quote=True)
    
    try:
        # --- معالجة تيك توك ---
        if "tiktok.com" in url:
            data = await fetch_tiktok_data(url)
            if not data:
                return await processing_msg.edit("❌ فشل استخراج البيانات. الرابط غير صحيح أو الحساب خاص.")
            
            if data["type"] == "video":
                await client.send_video(
                    chat_id=message.chat.id,
                    video=data["video_url"],
                    caption=f"📝 {data.get('title', '')}\n\n🤖 بواسطة البوت",
                    reply_to_message_id=message.id
                )
            elif data["type"] == "images":
                media_group = [InputMediaPhoto(img) for img in data["images"]]
                await client.send_media_group(chat_id=message.chat.id, media=media_group, reply_to_message_id=message.id)
                if data.get("audio"):
                    await client.send_audio(chat_id=message.chat.id, audio=data["audio"])
                    
            await processing_msg.delete()

        # --- معالجة إنستجرام ---
        elif "instagram.com" in url:
            media_list = await fetch_instagram_data(url)
            if not media_list:
                return await processing_msg.edit("❌ فشل استخراج البيانات. تأكد أن الحساب عام وليس خاصاً أو الرابط غير مدعوم.")
            
            if len(media_list) == 1:
                media = media_list[0]
                if media["type"] == "video":
                    await client.send_video(message.chat.id, video=media["url"], reply_to_message_id=message.id)
                else:
                    await client.send_photo(message.chat.id, photo=media["url"], reply_to_message_id=message.id)
            else:
                media_group = []
                for m in media_list[:10]:
                    if m["type"] == "video":
                        media_group.append(InputMediaVideo(m["url"]))
                    else:
                        media_group.append(InputMediaPhoto(m["url"]))
                await client.send_media_group(chat_id=message.chat.id, media=media_group, reply_to_message_id=message.id)
            
            await processing_msg.delete()

        else:
            await processing_msg.edit("❌ هذا الرابط غير مدعوم حالياً في نظام التحميل.")

    except Exception as e:
        await processing_msg.edit(f"⚠️ حدث خطأ تقني أثناء المعالجة: `{str(e)}`")

# ------------------------------------------------------------------------
# نقطة الانطلاق
# ------------------------------------------------------------------------
if __name__ == "__main__":
    print("🤖 Bot is running...")
    app.run()
    
