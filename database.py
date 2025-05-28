import sqlite3

conn = sqlite3.connect("stars_bot.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    stars INTEGER DEFAULT 0,
    referrer_id INTEGER,
    banned INTEGER DEFAULT 0
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    referred_id INTEGER
)""")

conn.commit()