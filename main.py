import telebot
import random
import threading
import sqlite3

bot = telebot.TeleBot("7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U")  # вставь сюда токен своего бота

emoji = "🍦"
roulette_bets = {}

RED_NUMS = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
BLACK_NUMS = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

# БД
conn = sqlite3.connect("roulette.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 100000
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS roulette_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    target TEXT,
    result INTEGER,
    win INTEGER,
    prize INTEGER
)
""")
conn.commit()

# Баланс
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return 100000

def update_balance(user_id, amount):
    current = get_balance(user_id)
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (current + amount, user_id))
    conn.commit()

# Обработка ставок
@bot.message_handler(func=lambda m: True)
def handle_bet(msg):
    uid = msg.from_user.id
    txt = msg.text.lower().replace(",", " ")
    parts = txt.split()

    if msg.text.lower() == "б":
        bal = get_balance(uid)
        return bot.send_message(msg.chat.id, f"Ваш баланс: {bal} {emoji}")

    if msg.text.lower() == "лог":
        cursor.execute("SELECT result FROM roulette_log ORDER BY id DESC LIMIT 10")
        results = [str(r[0]) for r in cursor.fetchall()]
        return bot.send_message(msg.chat.id, "Последние числа: " + ", ".join(results))

    if msg.text.lower() == "го":
        return start_roulette(msg)

    if len(parts) < 2:
        return

    try:
        amount = int(parts[0])
        if amount <= 0:
            return
    except:
        return

    balance = get_balance(uid)
    if balance < amount:
        return bot.reply_to(msg, f"Недостаточно {emoji}")

    targets = parts[1:]
    bets = roulette_bets.get(uid, [])

    for target in targets:
        target = target.strip()
        if '-' in target and target.count('-') == 1:
            try:
                a, b = map(int, target.split('-'))
                if 0 <= a <= 36 and 0 <= b <= 36:
                    bet_range = list(range(min(a, b), max(a, b)+1))
                    bets.append({'amount': amount, 'target': bet_range})
                    update_balance(uid, -amount)
            except:
                continue
        elif target in ['odd', 'even', 'red', 'black']:
            bets.append({'amount': amount, 'target': target})
            update_balance(uid, -amount)
        else:
            try:
                n = int(target)
                if 0 <= n <= 36:
                    bets.append({'amount': amount, 'target': [n]})
                    update_balance(uid, -amount)
            except:
                continue

    roulette_bets[uid] = bets
    bot.reply_to(msg, f"Ставка принята! {emoji}")

# Го — запускает рулетку
def start_roulette(msg):
    uid = msg.from_user.id
    if uid not in roulette_bets:
        return bot.send_message(msg.chat.id, "Сначала сделай ставку!")

    anim = bot.send_animation(msg.chat.id, animation="CgACAgIAAxkBAAICVGgyo8fx8r0-BW034uQ30js0atY1AAICWQAC96p5SC81RvIZJygENgQ")

    def resolve():
        bets = roulette_bets.pop(uid)
        result = random.randint(0, 36)
        text = f"Выпало: *{result}*\n\n"
        win_total = 0

        for bet in bets:
            amount = bet['amount']
            target = bet['target']
            win = False
            prize = 0

            if isinstance(target, list) and result in target:
                prize = amount * (36 // len(target))
                win = True
            elif target == "odd" and result % 2 == 1:
                prize = amount * 2
                win = True
            elif target == "even" and result != 0 and result % 2 == 0:
                prize = amount * 2
                win = True
            elif target == "red" and result in RED_NUMS:
                prize = amount * 2
                win = True
            elif target == "black" and result in BLACK_NUMS:
                prize = amount * 2
                win = True

            if win:
                update_balance(uid, prize)
                win_total += prize
                text += f"{emoji} {amount} на {target} — *выигрыш* +{prize}\n"
            else:
                text += f"{emoji} {amount} на {target} — проигрыш\n"

            cursor.execute("INSERT INTO roulette_log (user_id, amount, target, result, win, prize) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, amount, str(target), result, int(win), prize))
            conn.commit()

        try:
            bot.delete_message(msg.chat.id, anim.message_id)
        except:
            pass

        bot.send_message(msg.chat.id, text, parse_mode="Markdown")

    threading.Timer(7.0, resolve).start()

print("Бот запущен.")
bot.infinity_polling()