from kvsqlite.sync import Client as C
from config import database_name

db = C(f"{database_name}.sqlite")
db.autocommit = True
