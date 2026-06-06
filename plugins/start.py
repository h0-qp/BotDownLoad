from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn, WebAppInfo
import config
from sqldb import db
from utils import check_subscription

URL_HELP = "https://telegra.ph/DOWNLOADER-BOT-08-08"
WebAppButton = km([[btn(text="• help?", web_app=WebAppInfo(url=URL_HELP))]])

in_msg = """
دخل شخص جديد للبوت الخاص بك.

اسمه: {}
ايديه: {}
معرفه: @{}

عدد اعضاء البوت الان {} عضو
"""

@Client.on_message(filters.command("start") & filters.private)
async def welcome(bot, message):
    mention = message.from_user.mention
    id = message.from_user.id
    
    if not await check_subscription(bot, message):
        return

    if not db.exists("subs"): db.set("subs", "False")
    if not db.exists("startMSG"): 
        db.set("startMSG", "- مرحبا بك {mention}\n- في بوت تحميل من الانستكرام \n\nللتحميل ارسل الرابط فقط.")
    
    if message.from_user.id != int(config.dev):
        members = db.get("users") or []
        if id not in members:
            members.append(id)
            db.set("users", members)
            number = len(members)
            if db.get("dkhol") in ["True", True]:
                await bot.send_message(config.dev, in_msg.format(message.from_user.first_name, id, message.from_user.username, number))
        
        await message.reply(db.get("startMSG").replace("{mention}", mention), reply_markup=WebAppButton, disable_web_page_preview=True)
        if db.get("forward") in ["True", True]:
            await message.forward(config.channel_posts)
    else:
        subs = "❌" if db.get("subs") in ["False", 0, None] else "✅"
        dkhol = "❌" if db.get("dkhol") in ["False", 0, None] else "✅"
        forward = "❌" if db.get("forward") in ["False", 0, None] else "✅"
        
        me_ch = [ 
            [btn(text="الاحصائيات", callback_data="stats"), btn(text="اذاعة", callback_data="adaa")],
            [btn(text=f"اشعار الدخول {dkhol}", callback_data="dkhol"), btn(text=f"توجيه الرسائل {forward}", callback_data="forward")],
            [btn(f"الاشتراك الاجباري {subs}", callback_data="subs")],
            [btn(text="قناة الاشتراك الاجباري.", callback_data="channel"), btn(text="رسالة start.", callback_data="startMSG")]
        ]
        
        await message.reply(db.get("startMSG").replace("{mention}", mention), reply_markup=WebAppButton, disable_web_page_preview=True)
        await message.reply("مرحبا بك سيدي في بوتك اختر ادناه...", reply_markup=km(me_ch))
