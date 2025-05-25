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
        icecream INTEGER DEFAULT 1000
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

@bot.message_handler(commands=["start"])
def start(msg):
    add_user(msg.from_user)
    bot.send_message(msg.chat.id, "Добро пожаловать в IceCream Бота!\nКоманды:\n• Б - баланс\n• П [сумма] (в ответ)\n• ставка: 100 1 2 3\n• Го - запуск рулетки\n• /promo создать код сумма использований")

@bot.message_handler(func=lambda m: m.text.lower() == "б")
def balance(msg):
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    bot.send_message(msg.chat.id, f"{msg.from_user.first_name}\nБаланс: {bal}🍦")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('П '))
def transfer(msg):
    if not msg.reply_to_message:
        return bot.reply_to(msg, "Ответь на сообщение пользователя для перевода.")
    try:
        amount = int(msg.text.split()[1])
        if amount <= 0:
            return bot.reply_to(msg, "Сумма должна быть положительной.")
    except:
        return bot.reply_to(msg, "Формат: П [сумма]")
    
    sender = msg.from_user
    recipient = msg.reply_to_message.from_user

    if get_balance(sender.id) < amount:
        return bot.reply_to(msg, "Недостаточно средств.")
    
    update_balance(sender.id, -amount)
    update_balance(recipient.id, amount)
    bot.reply_to(msg, f"✅ Переведено {amount}🍦 пользователю {recipient.first_name}!")

def process_bet(p):
    p = p.lower()
    if p == 'чет': return [n for n in range(1,37) if n%2 == 0]
    elif p == 'нечет': return [n for n in range(1,37) if n%2 != 0]
    elif p == 'красное': return RED_NUMBERS
    elif p == 'черное': return BLACK_NUMBERS
    elif p.isdigit() and 0 <= int(p) <= 36: return [int(p)]
    return None

@bot.message_handler(func=lambda m: True)
def parse_bets(msg):
    uid = msg.from_user.id
    parts = msg.text.split()
    if not parts or not parts[0].isdigit():
        return

    try:
        amount = int(parts[0])
        numbers = []
        types = []
        for p in parts[1:]:
            nums = process_bet(p)
            if nums:
                numbers.extend(nums)
                types.append(p)
        if not numbers:
            return bot.reply_to(msg, "Укажи числа или типы (чет, нечет, красное, черное)")
    except:
        return bot.reply_to(msg, "Ошибка в ставке.")

    total = amount * len(set(numbers))
    if get_balance(uid) < total:
        return bot.reply_to(msg, f"Нужно {total}🍦 на ставку!")

    update_balance(uid, -total)
    roulette_bets.setdefault(uid, []).append({
        'amount': amount,
        'numbers': list(set(numbers)),
        'type': types
    })
    bot.reply_to(msg, f"✅ Принято! Всего ставок: {len(set(numbers))}\nНапиши 'Го' для запуска!🎰")

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def roulette_start(msg):
    uid = msg.from_user.id
    if uid not in roulette_bets:
        return bot.reply_to(msg, "Ты ещё не сделал ставку!")

    anim = bot.send_message(msg.chat.id, "🎡 Рулетка запущена...")
    for _ in range(3):
        time.sleep(0.6)
        bot.edit_message_text(f"🎡 Крутим... {random.randint(0,36)}", msg.chat.id, anim.message_id)

    result = random.randint(0,36)
    color = 'красное' if result in RED_NUMBERS else 'черное' if result in BLACK_NUMBERS else ''
    parity = 'чет' if result % 2 == 0 and result != 0 else 'нечет' if result != 0 else ''

    bot.edit_message_text(f"🎯 Выпало: {result} {color} {parity}", msg.chat.id, anim.message_id)

    total_win = 0
    report = []

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    for bet in roulette_bets[uid]:
        amount = bet['amount']
        nums = bet['numbers']
        coeff = 36 / len(nums) if len(nums) < 18 else 2
        win = 0
        if result in nums:
            win = int(amount * coeff)
            update_balance(uid, win)
            total_win += win
            report.append(f"✅ {bet['type']} x{round(coeff,2)} → +{win}🍦")
        else:
            report.append(f"❌ {bet['type']} → 0")

        # Лог в базу
        c.execute("INSERT INTO roulette_log (user_id, username, bet_amount, bet_numbers, result, win_amount) VALUES (?, ?, ?, ?, ?, ?)",
                  (uid, msg.from_user.username, amount, str(bet['type']), result, win))

    conn.commit()
    conn.close()

    del roulette_bets[uid]
    bot.send_message(msg.chat.id, f"Результаты:\n" + "\n".join(report) + f"\n\nОбщий выигрыш: {total_win}🍦")

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()