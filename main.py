
import telebot
import sqlite3
import random
import time
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from flask import Flask, request

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002
WEBHOOK_URL = 'https://yourdomain.com'  # Замените на ваш URL

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Базы данных
roulette_bets = {}
mines_games = {}
guess_games = {}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

def init_db():
    try:
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
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

init_db()

# Вебхуки
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return 'Bot is running!'

# Основные функции
def get_balance(uid):
    try:
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT icecream FROM users WHERE user_id = ?", (uid,))
        balance = c.fetchone()
        return balance[0] if balance else 0
    except Exception as e:
        print(f"Balance error: {e}")
        return 0
    finally:
        conn.close()

def update_balance(uid, amount):
    try:
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        c.execute("UPDATE users SET icecream = icecream + ? WHERE user_id = ?", (amount, uid))
        conn.commit()
    except Exception as e:
        print(f"Update balance error: {e}")
    finally:
        conn.close()

def is_admin(uid):
    try:
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE user_id = ?", (uid,))
        result = c.fetchone()
        return result is not None or uid == ADMIN_ID
    except Exception as e:
        print(f"Admin check error: {e}")
        return False
    finally:
        conn.close()

# Игра "Угадай число"
@bot.message_handler(commands=['guess'])
def guess_number(msg):
    try:
        if len(msg.text.split()) < 2:
            return bot.reply_to(msg, "❌ Используй: /guess [ставка]")
        
        bet = int(msg.text.split()[1])
        uid = msg.from_user.id

        if get_balance(uid) < bet:
            return bot.reply_to(msg, "❌ Недостаточно средств!")

        guess_games[uid] = {'bet': bet, 'secret': random.randint(1, 10)}
        update_balance(uid, -bet)

        bot.send_message(
            msg.chat.id,
            "🎮 Угадай число от 1 до 10!\n"
            f"💰 Ставка: {bet}🍦\n"
            "Введи число:"
        )

        bot.register_next_step_handler(msg, process_guess)

    except ValueError:
        bot.reply_to(msg, "❌ Введите число для ставки!")
    except Exception as e:
        print(f"Guess error: {e}")

def process_guess(msg):
    uid = None
    try:
        uid = msg.from_user.id
        if uid not in guess_games:
            return
        number = int(msg.text)
        game = guess_games[uid]
        if number == game['secret']:
            win = game['bet'] * 5
            update_balance(uid, win)
            bot.send_message(msg.chat.id, f"🎉 Победа! Выигрыш: {win}🍦")
        else:
            bot.send_message(msg.chat.id, f"❌ Не угадал! Число было: {game['secret']}")
    except ValueError:
        bot.reply_to(msg, "❌ Нужно ввести число!")
    except Exception as e:
        print(f"Process guess error: {e}")
    finally:
        if uid is not None and uid in guess_games:
            del guess_games[uid]

# Админ-команды
@bot.message_handler(commands=['addadmin'])
def add_admin(msg):
    if not is_admin(msg.from_user.id):
        return
    conn = None
    try:
        _, uid_str = msg.text.split()
        uid = int(uid_str)
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO admins VALUES (?)", (uid,))
        conn.commit()
        bot.reply_to(msg, f"✅ Пользователь {uid} добавлен в админы!")
    except:
        bot.reply_to(msg, "❌ Используй: /addadmin [ID]")
    finally:
        if conn:
            conn.close()

@bot.message_handler(commands=['ban'])
def ban_user(msg):
    if not is_admin(msg.from_user.id):
        return
    conn = None
    try:
        _, uid_str = msg.text.split()
        uid = int(uid_str)
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET banned = TRUE WHERE user_id = ?", (uid,))
        conn.commit()
        bot.reply_to(msg, f"⛔ Пользователь {uid} забанен!")
    except:
        bot.reply_to(msg, "❌ Используй: /ban [ID]")
    finally:
        if conn:
            conn.close()

# Запуск приложения
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL + '/' + TOKEN)
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
    except Exception as e:
        print(f"Startup error: {e}")