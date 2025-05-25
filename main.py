import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)

games = {}
roulette_bets = {}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            icecream INTEGER DEFAULT 1000
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            amount INTEGER,
            uses_left INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            user_id INTEGER,
            bet_text TEXT,
            result TEXT,
            win INTEGER,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
              (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT icecream FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def update_balance(uid, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    c.execute("UPDATE users SET icecream = icecream + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    conn.close()

def log_bet(user_id, bet_text, result, win):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO bets (user_id, bet_text, result, win, time) VALUES (?, ?, ?, ?, ?)",
              (user_id, bet_text, result, win, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

@bot.message_handler(commands=["start"])
def start(msg):
    add_user(msg.from_user)
    bot.send_message(msg.chat.id, "Добро пожаловать в IceCream Бота!\nКоманды:\n• Б - баланс\n• П [сумма] — перевод\n• мины 100 — игра\n• ставка: 100 1 2 3\n• Го — рулетка\n• /promo [код] — промокод\n• /выдать ID сумма")

@bot.message_handler(func=lambda m: m.text.lower() == "б")
def balance(msg):
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    name = msg.from_user.first_name
    bot.send_message(msg.chat.id, f"{name}\nБаланс: {bal}🍦")

@bot.message_handler(commands=["выдать"])
def give(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, uid, amount = msg.text.split()
        update_balance(int(uid), int(amount))
        bot.send_message(msg.chat.id, f"Выдано {amount}🍦 пользователю {uid}")
    except:
        bot.reply_to(msg, "Пример: /выдать 123456789 1000000")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('П '))
def transfer(msg):
    if not msg.reply_to_message:
        return bot.reply_to(msg, "Ответь на сообщение пользователя для перевода.")
    try:
        amount = int(msg.text.split()[1])
        if amount <= 0:
            return bot.reply_to(msg, "Сумма должна быть положительной.")
    except:
        return bot.reply_to(msg, "Используй: П [сумма]")
    
    sender = msg.from_user
    recipient = msg.reply_to_message.from_user
    if get_balance(sender.id) < amount:
        return bot.reply_to(msg, "Недостаточно средств.")
    
    update_balance(sender.id, -amount)
    update_balance(recipient.id, amount)
    bot.reply_to(msg, f"✅ Переведено {amount}🍦 пользователю {recipient.first_name}!")

@bot.message_handler(commands=["promo"])
def promo_handler(msg):
    args = msg.text.split()[1:]
    if msg.from_user.id != ADMIN_ID:
        return
    if len(args) < 4 or args[0] != "создать":
        return bot.reply_to(msg, "Используй: /promo создать [код] [сумма] [использований]")
    code = args[1].upper()
    amount = int(args[2])
    uses = int(args[3])
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO promocodes VALUES (?, ?, ?)", (code, amount, uses))
    conn.commit()
    conn.close()
    bot.reply_to(msg, f"Промокод {code} создан!🎁")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("промо "))
def use_promo(msg):
    code = msg.text.split()[1].upper()
    user_id = msg.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT amount, uses_left FROM promocodes WHERE code = ?", (code,))
    promo = c.fetchone()
    if not promo:
        conn.close()
        return bot.reply_to(msg, "Промокод не найден.❌")
    amount, uses = promo
    if uses <= 0:
        conn.close()
        return bot.reply_to(msg, "Промокод израсходован.😢")
    
    c.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
    update_balance(user_id, amount)
    conn.commit()
    conn.close()
    bot.reply_to(msg, f"🎉 Получено {amount}🍦! Промокод применен.")

def process_bet(p):
    p = p.lower()
    if p == 'чет': return [n for n in range(1,37) if n%2 ==0]
    elif p == 'нечет': return [n for n in range(1,37) if n%2 !=0]
    elif p == 'красное': return RED_NUMBERS
    elif p == 'черное': return BLACK_NUMBERS
    elif p.isdigit() and 0 <= int(p) <=36: return [int(p)]
    return None

@bot.message_handler(func=lambda m: True)
def parse_bets(msg):
    uid = msg.from_user.id
    if not msg.text or not msg.text.split()[0].isdigit():
        return

    parts = msg.text.split()
    amount = int(parts[0])
    numbers = []
    for p in parts[1:]:
        result = process_bet(p)
        if result:
            numbers.extend(result)

    if not numbers:
        return bot.reply_to(msg, "Укажи правильные числа/типы (чет, нечет, красное, черное, 0-36)")

    total = amount * len(numbers)
    if get_balance(uid) < total:
        return bot.reply_to(msg, f"Недостаточно средств: нужно {total}🍦")

    update_balance(uid, -total)
    roulette_bets.setdefault(uid, []).append({
        'amount': amount,
        'numbers': numbers,
        'type': parts[1:]
    })
    bot.reply_to(msg, f"✅ Принято! Ставок: {len(numbers)}\nНапиши 'Го' для запуска рулетки.🎰")

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def roulette_start(msg):
    uid = msg.from_user.id
    add_user(msg.from_user)
    if uid not in roulette_bets:
        return bot.reply_to(msg, "Сначала сделай ставку.")

    anim = bot.send_message(msg.chat.id, "🎡 Рулетка запущена...")
    for _ in range(3):
        time.sleep(0.7)
        bot.edit_message_text(f"🎡 Крутим... {random.randint(0, 36)}", msg.chat.id, anim.message_id)

    result = random.randint(0, 36)
    color = 'красное' if result in RED_NUMBERS else 'черное' if result != 0 else ''
    parity = 'чет' if result % 2 == 0 and result != 0 else 'нечет' if result != 0 else ''

    final_text = f"🎯 Выпало: {result} {color} {parity}".strip()
    bot.edit_message_text(final_text, msg.chat.id, anim.message_id)

    total_win = 0
    report = []
    for bet in roulette_bets[uid]:
        amount = bet['amount']
        nums = bet['numbers']
        coeff = 36 / len(nums) if len(nums) < 18 else 2

        if result in nums:
            win = int(amount * coeff)
            update_balance(uid, win)
            total_win += win
            report.append(f"✅ {bet['type']} x{round(coeff,2)} → +{win}🍦")
            log_bet(uid, str(bet['type']), f"{result}", win)
        else:
            report.append(f"❌ {bet['type']} → 0")
            log_bet(uid, str(bet['type']), f"{result}", 0)

    del roulette_bets[uid]
    bot.send_message(msg.chat.id, f"Результаты:\n" + "\n".join(report) + f"\n\nОбщий выигрыш: {total_win}🍦")

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()