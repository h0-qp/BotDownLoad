from os import getenv
from dotenv import load_dotenv

load_dotenv()

database_name = getenv("DATABASE_NAME", "mustafa")
api_id = getenv("API_ID", 20170388)
api_hash = getenv("API_HASH", "5eded27e4e9b44c519694cda605b1129")
# التوكن الجديد اللي طلبته
token = getenv("TOKEN", "8509012164:AAEfJcqsprCSlN2BHBX2td4UitXvK_Cu4nc")
ch_id = getenv("CH_ID", -1001787630863)
channel_posts = getenv("CHANNEL_POSTS", "frftrdffh")
error_receiver = getenv("ERROR_RECEIVER", "frftrdffh")
dev = getenv("DEV", "2010789056")
