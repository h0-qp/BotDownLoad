from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup as km, InlineKeyboardButton as btn
import config
from sqldb import db
from utils import check_subscription
import requests

what = {
    "adaa": False,
    "replace_channel": False,
    "replace_startMSG": False
}

@Client.on_message(filters.all & filters.private, group=-1)
async def admin_messages_handler(bot, message):
    if not await check_subscription(bot, message):
        return

    dev_id = int(config.dev)
    if message.from_user.id == dev_id:
        if what["adaa"]:
            done = 0
            users = db.get("users") or []
            for user in users:
                try:
                    await message.copy(user)
                    done += 1
                except Exception:
                    continue
            await message.reply(f"تم ارسال الاذاعة الى {done} من الاعضاء")
            what["adaa"] = False
            message.stop_propagation()
            
        elif what["replace_channel"]:
            if message.text and "-100" in message.text:
                try:
                    info = requests.get(f"https://api.telegram.org/bot{config.token}/getChat?chat_id={message.text}").json()
                    if not info.get("ok"):
                        await message.reply("البوت ليس ادمن في القناة، او ليس لديه صلاحية دعوة المستخدمين.")
                        message.stop_propagation()
                        return
                    
                    data = {
                        "title": info["result"].get("title", ""),
                        "id": info["result"].get("id", ""),
                        "username": info["result"].get("username", ""),
                        "link": info["result"].get("invite_link", "")
                    }
                    db.set("channel", data)
                    await message.reply(f"- تم وضع القناة بنجاح.")
                    what["replace_channel"] = False
                except Exception as e:
                    await message.reply(f"Error: {e}")
            else:
                await message.reply("ارسل ID القناة الصحيح.")
            message.stop_propagation()
            
        elif what["replace_startMSG"]:
            if message.text:
                db.set("startMSG", message.text)
                await message.reply("تم تغيير رسالة start.")
                what["replace_startMSG"] = False
            message.stop_propagation()

@Client.on_callback_query(filters.regex("^(stats|adaa|back|dkhol|forward|channel|startMSG|replace_channel|replace_startMSG|subs)$"))
async def admin_callback(bot, query):
    back = km([[btn(text="رجوع", callback_data="back")]])
    replace_channel = km([
        [btn(text="تغيير/وضع قناة اشتراك اجباري", callback_data="replace_channel")],
        [btn(text="رجوع", callback_data="back")]
    ])
    replace_startMSG = km([
        [btn(text="تغيير رسالة ستارت", callback_data="replace_startMSG")],
        [btn(text="رجوع", callback_data="back")]
    ])
    
    if query.data == "stats":
        users = len(db.get("users") or [])
        await query.message.edit(f"قائمة الاعضاء.\n\nعدد الاعضاء: {users}", reply_markup=back)
    elif query.data == "adaa":
        await query.message.edit("تمام، دز الرسالة وراح ادزها للكل.", reply_markup=back)
        what["adaa"] = True
    elif query.data == "subs":
        current = db.get("subs")
        new_val = "False" if current in ["True", True] else "True"
        db.set("subs", new_val)
        await query.answer("تم التعديل.")
    elif query.data == "dkhol":
        current = db.get("dkhol")
        new_val = "False" if current in ["True", True] else "True"
        db.set("dkhol", new_val)
        await query.answer("تم التعديل.")
    elif query.data == "forward":
        current = db.get("forward")
        new_val = "False" if current in ["True", True] else "True"
        db.set("forward", new_val)
        await query.answer("تم التعديل.")
    elif query.data == "channel":
        channel = db.get("channel") or "لا يوجد."
        if isinstance(channel, dict):
            msg = f"قناة الاشتراك الاجباري:\ntitle: {channel.get('title')}\nid: {channel.get('id')}\nusername: @{channel.get('username')}"
        else:
            msg = "لا يوجد."
        await query.message.edit(msg, reply_markup=replace_channel)
    elif query.data == "replace_channel":
        what["replace_channel"] = True
        await query.message.edit("الان عليك رفع البوت أدمن بقناتك، وإرسال ID القناة\nمثال -1003445791104", reply_markup=back)
    elif query.data == "startMSG":
        await query.message.edit(db.get("startMSG") or "لا توجد رسالة", reply_markup=replace_startMSG)
    elif query.data == "replace_startMSG":
        what["replace_startMSG"] = True
        await query.message.edit("الان عليك ارسال الرسالة الجديدة يمكنك ارفاق `{mention}` ليكون منشن للعضو الذي دخل.", reply_markup=back)
    elif query.data == "back":
        what["adaa"] = False
        what["replace_channel"] = False
        what["replace_startMSG"] = False

    if query.data in ["dkhol", "forward", "subs", "back"]:
        subs = "❌" if db.get("subs") in ["False", 0, None] else "✅"
        dkhol = "❌" if db.get("dkhol") in ["False", 0, None] else "✅"
        forward = "❌" if db.get("forward") in ["False", 0, None] else "✅"
            
        me_ch = [ 
            [btn(text="الاحصائيات", callback_data="stats"), btn(text="اذاعة", callback_data="adaa")],
            [btn(text=f"اشعار الدخول {dkhol}", callback_data="dkhol"), btn(text=f"توجيه الرسائل {forward}", callback_data="forward")],
            [btn(f"الاشتراك الاجباري {subs}", callback_data="subs")],
            [btn(text="قناة الاشتراك الاجباري.", callback_data="channel"), btn(text="رسالة start.", callback_data="startMSG")]
        ]
        await query.message.edit("مرحبا بك سيدي في بوتك اختر ادناه.", reply_markup=km(me_ch))
