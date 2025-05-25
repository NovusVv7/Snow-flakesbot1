import telebot
import sqlite3
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)

games = {}
roulette_bets = {}
banned_users = set()
COEFFS = [1.7, 2.5, 3, 4.67, 25]

RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMS = set(range(1, 37)) - RED_NUMS

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        first_name TEXT, 
        icecream INTEGER DEFAULT 1000)""")
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
    c.execute("UPDATE users SET icecream = icecream + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    conn.close()

def get_top_users():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, username, icecream FROM users ORDER BY icecream DESC LIMIT 10")
    top = c.fetchall()
    conn.close()
    return top

@bot.message_handler(commands=["start"])
def start(msg):
    add_user(msg.from_user)
    bot.send_message(msg.chat.id, "Добро пожаловать в IceCream Бота!\n"
                                  "Команды:\n• Б — баланс\n• мины 100 — игра мины\n"
                                  "• 100 1 2 3 — ставки на рулетку\n• Го — запуск рулетки\n"
                                  "• П 1000 (в ответ) — передать\n• /топ — топ игроков\n"
                                  "• /info — инфо")

@bot.message_handler(commands=["info"])
def info(msg):
    bot.send_message(msg.chat.id, "IceCream Бот\nВладелец: @admin\nИгры: Мины, Рулетка\nВалюта: Мороженое")

@bot.message_handler(commands=["топ"])
def top(msg):
    top = get_top_users()
    txt = "Топ игроков по мороженому:\n\n"
    for i, (name, uname, ice) in enumerate(top, 1):
        txt += f"{i}. {name} (@{uname}) — {ice}\n"
    bot.send_message(msg.chat.id, txt)

@bot.message_handler(func=lambda m: m.text.lower() == "б")
def balance(msg):
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    bot.send_message(msg.chat.id, f"Игрок: {msg.from_user.first_name} (@{msg.from_user.username})\nБаланс: {bal} мороженого")

@bot.message_handler(commands=["выдать", "забрать", "бан"])
def admin_cmd(msg):
    if msg.from_user.id != ADMIN_ID or not msg.reply_to_message:
        return
    uid = msg.reply_to_message.from_user.id
    try:
        amount = int(msg.text.split()[1])
    except:
        return bot.reply_to(msg, "Неверный формат. Пример: /выдать 1000")
    if "/выдать" in msg.text:
        update_balance(uid, amount)
        bot.reply_to(msg, f"Выдано {amount}")
    elif "/забрать" in msg.text:
        update_balance(uid, -amount)
        bot.reply_to(msg, f"Забрано {amount}")
    elif "/бан" in msg.text:
        banned_users.add(uid)
        bot.reply_to(msg, "Пользователь забанен")

@bot.message_handler(func=lambda m: m.text.lower().startswith("мины"))
def mines(msg):
    uid = msg.from_user.id
    if uid in banned_users: return
    try: amount = int(msg.text.split()[1])
    except: return bot.reply_to(msg, "Пример: мины 100")
    if get_balance(uid) < amount:
        return bot.send_message(msg.chat.id, "Недостаточно мороженого!")
    update_balance(uid, -amount)
    mines = random.sample(range(25), 3)
    games[uid] = {"mines": mines, "opened": [], "bet": amount, "step": 0}
    send_mine_field(msg.chat.id, uid, "Мины разбросаны!")

def send_mine_field(chat_id, uid, text):
    markup = InlineKeyboardMarkup()
    for i in range(5):
        row = []
        for j in range(5):
            idx = i * 5 + j
            label = "❔" if idx not in games[uid]["opened"] else "✅"
            row.append(InlineKeyboardButton(label, callback_data=f"open_{idx}"))
        markup.row(*row)
    markup.add(InlineKeyboardButton("ЗАБРАТЬ", callback_data="take"))
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("open_"))
def open_cell(call):
    uid = call.from_user.id
    if uid not in games: return
    idx = int(call.data.split("_")[1])
    g = games[uid]
    if idx in g["opened"]: return
    if idx in g["mines"]:
        del games[uid]
        return bot.edit_message_text("Мина! Проигрыш.", call.message.chat.id, call.message.message_id)
    g["opened"].append(idx)
    g["step"] += 1
    if g["step"] >= len(COEFFS):
        win = int(g["bet"] * COEFFS[-1])
        update_balance(uid, win)
        del games[uid]
        return bot.edit_message_text(f"Ты прошёл всё поле! +{win} мороженого", call.message.chat.id, call.message.message_id)
    send_mine_field(call.message.chat.id, uid, f"Клеток: {g['step']}. Коэф: {COEFFS[g['step']-1]}")

@bot.callback_query_handler(func=lambda c: c.data == "take")
def take_win(call):
    uid = call.from_user.id
    if uid not in games: return
    g = games[uid]
    if g["step"] == 0:
        del games[uid]
        return bot.edit_message_text("Ты не открыл ни одной клетки.", call.message.chat.id, call.message.message_id)
    win = int(g["bet"] * COEFFS[g["step"]-1])
    update_balance(uid, win)
    del games[uid]
    bot.edit_message_text(f"Ты забрал {win} мороженого", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def go_roulette(msg):
    uid = msg.from_user.id
    if uid not in roulette_bets:
        return bot.send_message(msg.chat.id, "Ты не сделал ставок.")
    
    # Отправляем гифку
    bot.send_animation(msg.chat.id, animation="CgACAgIAAxkBAAICVGgyo8fx8r0-BW034uQ30js0atY1AAICWQAC96p5SC81RvIZJygENgQ")

    bets = roulette_bets.pop(uid)
    result = random.randint(0, 36)
    win_total = 0
    text = f"Выпало: {result}\n\n"
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
            text += f"Ставка {amount} на {target} — победа +{prize}\n"
        else:
            text += f"Ставка {amount} на {target} — проигрыш\n"
    bot.send_message(msg.chat.id, text)

@bot.message_handler(func=lambda m: m.text.lower().startswith("п") and m.reply_to_message)
def transfer(msg):
    uid = msg.from_user.id
    try:
        amount = int(msg.text.split()[1])
        to_uid = msg.reply_to_message.from_user.id
        if get_balance(uid) < amount:
            return bot.reply_to(msg, "Недостаточно мороженого.")
        update_balance(uid, -amount)
        update_balance(to_uid, amount)
        bot.reply_to(msg, f"Передано {amount} мороженого!")
    except:
        return

@bot.message_handler(func=lambda m: True)
def parse_bets(msg):
    uid = msg.from_user.id
    if uid in banned_users: return
    parts = msg.text.lower().split()
    if not parts or not parts[0].isdigit():
        return
    try:
        amount = int(parts[0])
        targets = parts[1:]
        bets = []
        for t in targets:
            if t in ["odd", "even", "red", "black"]:
                bets.append({"amount": amount, "target": t})
            elif "-" in t:
                a, b = map(int, t.split("-"))
                bets.append({"amount": amount, "target": list(range(a, b + 1))})
            else:
                bets.append({"amount": amount, "target": [int(t)]})
        total = amount * len(bets)
        if get_balance(uid) < total:
            return bot.reply_to(msg, f"Недостаточно мороженого для {len(bets)} ставок по {amount}!")
        update_balance(uid, -total)
        if uid not in roulette_bets:
            roulette_bets[uid] = []
        roulette_bets[uid].extend(bets)
        bot.reply_to(msg, f"Принято {len(bets)} ставок по {amount}. Напиши 'Го' для запуска!")
    except:
        return

# Хендлер для получения file_id гифки
@bot.message_handler(content_types=["animation"])
def get_gif_id(msg):
    bot.reply_to(msg, f"file_id: {msg.animation.file_id}")

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()