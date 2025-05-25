import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)
roulette_bets = {}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        icecream INTEGER DEFAULT 1000,
        banned BOOLEAN DEFAULT FALSE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        amount INTEGER,
        uses_left INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS roulette_log (
        user_id INTEGER,
        username TEXT,
        bet_amount INTEGER,
        bet_numbers TEXT,
        result INTEGER,
        win_amount INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id == ADMIN_ID

# ... (остальные функции остаются без изменений до обработчиков)

@bot.message_handler(commands=["give"])
def give_icecream(msg):
    if not is_admin(msg.from_user.id):
        return
    
    try:
        args = msg.text.split()[1:]
        if msg.reply_to_message:
            amount = int(args[0])
            user = msg.reply_to_message.from_user
        else:
            amount = int(args[0])
            user_id = int(args[1])
            user = bot.get_chat_member(user_id, user_id).user
    except:
        return bot.reply_to(msg, "Формат:\n/give [сумма] [user_id]\nили ответом на сообщение /give [сумма]")
    
    update_balance(user.id, amount)
    bot.reply_to(msg, f"✅ {amount}🍦 выдано пользователю {user.first_name}")

@bot.message_handler(commands=["stats"])
def stats(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(icecream) FROM users")
    total_icecream = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM roulette_log")
    total_bets = c.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""📊 Статистика бота:
👥 Пользователей: {total_users}
🍦 Всего мороженого: {total_icecream}
🎰 Сыграно ставок: {total_bets}"""
    bot.reply_to(msg, stats_text)

@bot.message_handler(commands=["top"])
def top_balance(msg):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, icecream FROM users ORDER BY icecream DESC LIMIT 10")
    top_users = c.fetchall()
    conn.close()
    
    top_text = "🏆 Топ пользователей:\n"
    for i, (uid, uname, balance) in enumerate(top_users, 1):
        top_text += f"{i}. {uname or uid} - {balance}🍦\n"
    
    bot.reply_to(msg, top_text)

@bot.message_handler(commands=["take"])
def take_icecream(msg):
    if not is_admin(msg.from_user.id):
        return
    
    try:
        args = msg.text.split()[1:]
        user_id = int(args[1])
        amount = int(args[0])
    except:
        return bot.reply_to(msg, "Формат: /take [сумма] [user_id]")
    
    current = get_balance(user_id)
    take = min(amount, current)
    update_balance(user_id, -take)
    bot.reply_to(msg, f"✅ Изъято {take}🍦 у пользователя {user_id}")

@bot.message_handler(commands=["ban"])
def ban_user(msg):
    if not is_admin(msg.from_user.id):
        return
    
    try:
        user_id = int(msg.text.split()[1])
    except:
        return bot.reply_to(msg, "Формат: /ban [user_id]")
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET banned = TRUE WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(msg, f"⛔ Пользователь {user_id} забанен")

# Обновляем проверки в других функциях
def check_ban(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id = ?", (uid,))
    banned = c.fetchone()[0]
    conn.close()
    return banned

# Добавляем проверки в основные обработчики
@bot.message_handler(func=lambda m: m.text and m.text.startswith('П '))
def transfer(msg):
    if check_ban(msg.from_user.id):
        return bot.reply_to(msg, "❌ Вы забанены!")
    # ... остальной код

@bot.message_handler(func=lambda m: True)
def parse_bets(msg):
    if check_ban(msg.from_user.id):
        return bot.reply_to(msg, "❌ Вы забанены!")
    # ... остальной код

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()