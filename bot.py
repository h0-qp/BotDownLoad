import asyncio
from pyrogram import Client
import config

bot = Client(
    "mybot",
    api_id=config.api_id,
    api_hash=config.api_hash,
    bot_token=config.token,
    plugins=dict(root="plugins") # 🏗️ Smart Plugins Architecture Enabled ✅
)

if __name__ == "__main__":
    print("Bot is started asynchronously! 🚀")
    bot.run()
