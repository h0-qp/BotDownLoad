import asyncio
import urllib.parse
import aiohttp
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

async def fetch_tiktok_data(url: str) -> dict:
    clean_url = url.split("?")[0] if "?" in url else url
    api_url = "https://www.tikwm.com/api/"
    data = {"url": clean_url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
    
    def fix_url(link):
        if link and link.startswith("/"): return "https://www.tikwm.com" + link
        return link

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, data=data, timeout=15) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("code") == 0:
                        body = result.get("data")
                        if "images" in body:
                            return {"type": "images", "images": [fix_url(i) for i in body["images"]], "audio": fix_url(body.get("music"))}
                        else:
                            return {"type": "video", "video_url": fix_url(body.get("play")), "title": body.get("title")}
    except Exception as e:
        print(f"TikTok API Error: {e}", flush=True)
    return None

async def fetch_instagram_data(url: str) -> tuple:
    clean_url = url.split("?")[0]
    if not clean_url.endswith("/"):
        clean_url += "/"
        
    media_urls = []
    debug_logs = []
    
    # مصفوفة سيرفرات Cobalt المستقلة (تعمل كخطة A, B, C, D, E)
    cobalt_instances = [
        "https://co.wuk.sh/api/json",
        "https://cobalt.cst.im/api/json",
        "https://api.cobalt.zluqe.com/api/json",
        "https://cobalt.seasi.dev/api/json",
        "https://cobalt-api.pepegapi.heyturi.com/api/json"
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # التكرار عبر السيرفرات: إذا فشل واحد، ينتقل للثاني مباشرة
    async with aiohttp.ClientSession() as session:
        for instance in cobalt_instances:
            instance_name = instance.split("//")[1].split("/")[0]
            try:
                async with session.post(instance, json={"url": clean_url}, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        if res.get("status") in ["stream", "redirect"]:
                            link = res.get("url")
                            t = "photo" if ".jpg" in link.lower() or ".webp" in link.lower() else "video"
                            return [{"type": t, "url": link}], debug_logs
                        elif res.get("status") == "picker":
                            for item in res.get("picker", []):
                                link = item.get("url")
                                t = "photo" if item.get("type") == "photo" else "video"
                                media_urls.append({"type": t, "url": link})
                            if media_urls: return media_urls, debug_logs
                    else:
                        debug_logs.append(f"{instance_name}: HTTP {resp.status}")
            except Exception as e:
                debug_logs.append(f"{instance_name} Error: {str(e)}")

        # محرك طوارئ أخير في حال سقوط كل سيرفرات كوبالت
        try:
            encoded_url = urllib.parse.quote(clean_url)
            async with session.get(f"https://api.agatz.my.id/api/instagram?url={encoded_url}", timeout=10) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if res.get("status") == 200 and res.get("data"):
                        for link in res["data"]:
                            t = "photo" if ".jpg" in link.lower() or ".webp" in link.lower() else "video"
                            media_urls.append({"type": t, "url": link})
                        if media_urls: return media_urls, debug_logs
                else:
                    debug_logs.append(f"Agatz API: HTTP {resp.status}")
        except Exception as e:
            debug_logs.append(f"Agatz API Error: {str(e)}")

    return [], debug_logs


# ------------------------------------------------------------------------
# معالجات الأوامر واللوحة
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
        await message.reply("عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.", reply_markup=btn)
        return

    url = message.text.strip()
    processing_msg = await message.reply("⏳ **جاري التحميل...**", quote=True)
    
    try:
        if "tiktok.com" in url:
            data = await fetch_tiktok_data(url)
            if not data: return await processing_msg.edit("❌ فشل استخراج البيانات. الرابط غير صحيح أو الحساب خاص.")
            
            if data["type"] == "video":
                await client.send_video(message.chat.id, video=data["video_url"], caption=f"🤖 بواسطة البوت", reply_to_message_id=message.id)
            elif data["type"] == "images":
                media_group = [InputMediaPhoto(img) for img in data["images"]]
                await client.send_media_group(message.chat.id, media=media_group, reply_to_message_id=message.id)
                if data.get("audio"): await client.send_audio(message.chat.id, audio=data["audio"])
            await processing_msg.delete()

        elif "instagram.com" in url:
            media_list, debug_logs = await fetch_instagram_data(url)
            
            if not media_list:
                error_text = "❌ **فشل استخراج البيانات.**\n"
                error_text += "🛠️ **سجل تشخيص الأخطاء (للمطور):**\n"
                for log in debug_logs: error_text += f"- `{log}`\n"
                return await processing_msg.edit(error_text)
            
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
            await processing_msg.edit("⚠️ تم جلب الرابط بنجاح، لكن تيليجرام رفض رفعه. جرب رابطاً آخر.")
        else:
            await processing_msg.edit(f"⚠️ حدث خطأ تقني: `{str(e)}`")

if __name__ == "__main__":
    print("🤖 Bot is starting...", flush=True)
    app.run()
    
