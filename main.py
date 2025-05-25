import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)

# Базы данных
roulette_bets = {}
mines_games = {}
guess_games = {}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            icecream INTEGER DEFAULT 1000,
            banned BOOLEAN DEFAULT FALSE
        );
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            amount INTEGER,
            uses_left INTEGER
        );
        CREATE TABLE IF NOT EXISTS bets (
            user_id INTEGER,
            bet_text TEXT,
            result TEXT,
            win INTEGER,
            time TEXT
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        );
    """)
    conn.commit()
    conn.close()

init_db()

# Основные функции
def get_balance(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT icecream FROM users WHERE user_id = ?", (uid,))
    balance = c.fetchone()[0] if c.fetchone() else 0
    conn.close()
    return balance

def update_balance(uid, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    c.execute("UPDATE users SET icecream = icecream + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    conn.close()

def is_admin(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id = ?", (uid,))
    result = c.fetchone()
    conn.close()
    return result is not None or uid == ADMIN_ID

# Игра "Угадай число"
@bot.message_handler(commands=['guess'])
def guess_number(msg):
    try:
        bet = int(msg.text.split()[1])
        uid = msg.from_user.id
        
        if get_balance(uid) < bet:
            return bot.reply_to(msg, "❌ Недостаточно средств!")
        
        guess_games[uid] = {'bet': bet, 'secret': random.randint(1, 10)}
        update_balance(uid, -bet)
        
        bot.send_message(msg.chat.id, 
            "🎮 Угадай число от 1 до 10!\n"
            f"💰 Ставка: {bet}🍦\n"
            "Введи число:")
        
        bot.register_next_step_handler(msg, process_guess)
    
    except Exception as e:
        print(e)
        bot.reply_to(msg, "❌ Используй: /guess [ставка]")

def process_guess(msg):
    uid = msg.from_user.id
    if uid not in guess_games:
        return
    
    try:
        number = int(msg.text)
        game = guess_games[uid]
        
        if number == game['secret']:
            win = game['bet'] * 5
            update_balance(uid, win)
            bot.send_message(msg.chat.id, f"🎉 Победа! Выигрыш: {win}🍦")
        else:
            bot.send_message(msg.chat.id, f"❌ Не угадал! Число было: {game['secret']}")
        
        del guess_games[uid]
    
    except:
        bot.reply_to(msg, "❌ Нужно ввести число!")
        del guess_games[uid]

# Админ-панель
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    if not is_admin(msg.from_user.id):
        return
    
    text = (
        "👑 Админ-панель:\n"
        "/broadcast - Рассылка сообщения\n"
        "/addadmin [ID] - Добавить админа\n"
        "/stats - Статистика бота\n"
        "/ban [ID] - Забанить пользователя\n"
        "/unban [ID] - Разбанить"
    )
    bot.send_message(msg.chat.id, text)

@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if not is_admin(msg.from_user.id):
        return
    
    text = ' '.join(msg.text.split()[1:])
    if not text:
        return bot.reply_to(msg, "❌ Введите сообщение для рассылки")
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    
    success = 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 Рассылка:\n{text}")
            success += 1
        except:
            continue
    
    bot.send_message(msg.chat.id, f"✅ Сообщение доставлено {success} пользователям")

# Остальные функции (рулетка, мины, логи и т.д.)
# ... [Ваш существующий код с исправлениями] ...

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()