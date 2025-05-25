import telebot
import sqlite3
import random
import threading
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
    bot.send_message(msg.chat.id, 
        "❄️🍨 Добро пожаловать в IceCream Casino! 🍧\n\n"
        "Основные команды:\n"
        "🍧 Б - проверить баланс\n"
        "💣 Мины 100 - игра в мины\n"
        "🎰 100 1 2 3 - ставки на рулетку\n"
        "🔄 П 1000 (ответом) - передать мороженое\n"
        "🏆 /топ - топ игроков\n"
        "ℹ️ /info - информация о боте")

@bot.message_handler(commands=["info"])
def info(msg):
    bot.send_message(msg.chat.id, 
        "🍦 IceCream Casino Бот\n"
        "👑 Владелец: @admin\n"
        "🎮 Игры:\n"
        "• 💣 Мины (коэффициенты до x25)\n"
        "• 🎰 Рулетка (европейская)\n"
        "💎 Валюта: Мороженое 🍧")

@bot.message_handler(commands=["топ"])
def top(msg):
    top_users = get_top_users()
    txt = "🏆 Топ игроков по мороженому 🍧:\n\n"
    for i, (name, uname, ice) in enumerate(top_users, 1):
        txt += f"{i}. {name} (@{uname}) — {ice}🍨\n"
    bot.send_message(msg.chat.id, txt)

@bot.message_handler(func=lambda m: m.text.lower() == "б")
def balance(msg):
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    bot.send_message(msg.chat.id, 
        f"👤 Игрок: {msg.from_user.first_name}\n"
        f"📦 Баланс: {bal}🍧\n"
        f"🆔 ID: {msg.from_user.id}")

@bot.message_handler(commands=["выдать", "забрать", "бан"])
def admin_cmd(msg):
    if msg.from_user.id != ADMIN_ID or not msg.reply_to_message:
        return
    
    uid = msg.reply_to_message.from_user.id
    try:
        amount = int(msg.text.split()[1])
    except:
        return bot.reply_to(msg, "❌ Ошибка формата. Пример: /выдать 1000")
    
    if "/выдать" in msg.text:
        update_balance(uid, amount)
        bot.reply_to(msg, f"✅ Выдано {amount}🍧")
    elif "/забрать" in msg.text:
        current = get_balance(uid)
        amount = min(amount, current)
        if amount <= 0:
            return bot.reply_to(msg, "❌ Нечего забирать")
        update_balance(uid, -amount)
        bot.reply_to(msg, f"✅ Забрано {amount}🍧")
    elif "/бан" in msg.text:
        banned_users.add(uid)
        bot.reply_to(msg, "⛔ Пользователь забанен")

@bot.message_handler(func=lambda m: m.text.lower().startswith("мины"))
def mines(msg):
    uid = msg.from_user.id
    if uid in banned_users:
        return
    
    try:
        amount = int(msg.text.split()[1])
        if amount < 10:
            raise ValueError
    except:
        return bot.reply_to(msg, "⚠️ Пример: мины 100 (мин. ставка 10🍧)")
    
    balance = get_balance(uid)
    if balance < amount:
        return bot.send_message(msg.chat.id, "❌ Недостаточно мороженого! 🍨")
    
    update_balance(uid, -amount)
    mines = random.sample(range(25), 3)
    games[uid] = {
        "mines": mines,
        "opened": [],
        "bet": amount,
        "step": 0
    }
    send_mine_field(msg.chat.id, uid, "💣 Игра началась! Выбери клетку:")

def send_mine_field(chat_id, uid, text):
    markup = InlineKeyboardMarkup()
    for i in range(5):
        row = []
        for j in range(5):
            idx = i * 5 + j
            label = "❔" if idx not in games[uid]["opened"] else "🟢"
            row.append(InlineKeyboardButton(label, callback_data=f"open_{idx}"))
        markup.row(*row)
    markup.add(InlineKeyboardButton("🏁 Забрать выигрыш 🍧", callback_data="take"))
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("open_"))
def open_cell(call):
    uid = call.from_user.id
    if uid not in games:
        return
    
    idx = int(call.data.split("_")[1])
    g = games[uid]
    
    if idx in g["opened"] or idx in g["mines"]:
        return
    
    if idx in g["mines"]:
        del games[uid]
        return bot.edit_message_text("💥 Ты подорвался на мине! 🚫", call.message.chat.id, call.message.message_id)
    
    g["opened"].append(idx)
    g["step"] += 1
    
    if g["step"] >= len(COEFFS):
        win = int(g["bet"] * COEFFS[-1])
        update_balance(uid, win)
        del games[uid]
        return bot.edit_message_text(f"🎉 Полный проход! +{win}🍧", 
                                   call.message.chat.id, call.message.message_id)
    
    send_mine_field(call.message.chat.id, uid, f"🔍 Открыто клеток: {g['step']} | Коэф: x{COEFFS[g['step']-1]}")

@bot.callback_query_handler(func=lambda c: c.data == "take")
def take_win(call):
    uid = call.from_user.id
    if uid not in games:
        return
    
    g = games[uid]
    if g["step"] == 0:
        update_balance(uid, g["bet"])
        del games[uid]
        return bot.edit_message_text("🔄 Ставка возвращена 🍨", call.message.chat.id, call.message.message_id)
    
    win = int(g["bet"] * COEFFS[g["step"]-1])
    update_balance(uid, win)
    del games[uid]
    bot.edit_message_text(f"💰 Выигрыш: {win}🍧", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def go_roulette(msg):
    uid = msg.from_user.id
    if uid not in roulette_bets:
        return bot.send_message(msg.chat.id, "❌ Сначала сделай ставки! 🎰")
    
    sent_animation = bot.send_animation(msg.chat.id, animation="CgACAgIAAxkBAAICVGgyo8fx8r0-BW034uQ30js0atY1AAICWQAC96p5SC81RvIZJygENgQ")
    
    def delete_animation():
        try:
            bot.delete_message(msg.chat.id, sent_animation.message_id)
        except Exception as e:
            print(f"Ошибка удаления гифки: {e}")
    
    threading.Timer(7.0, delete_animation).start()
    
    bets = roulette_bets.pop(uid)
    result = random.randint(0, 36)
    win_total = 0
    text = f"🎰 Выпало: {result} {'🔴' if result in RED_NUMS else '⚫' if result !=0 else '🟣'}\n\n"
    
    for bet in bets:
        amount = bet['amount']
        target = bet['target']
        win = False
        prize = 0
        
        if isinstance(target, int):
            if result == target:
                prize = amount * 36
                win = True
        elif isinstance(target, str):
            if target == "odd" and result % 2 == 1 and result != 0:
                prize = amount * 2
                win = True
            elif target == "even" and result != 0 and result % 2 == 0:
                prize = amount * 2
                win = True
            elif target == "red" and result in RED_NUMS:
                prize = amount * 2
                win = True
            elif target == "black" and result in BLACK_NUMS and result != 0:
                prize = amount * 2
                win = True
        
        if win:
            update_balance(uid, prize)
            win_total += prize
            text += f"✅ {amount}🍧 на {target} → +{prize}🍨\n"
        else:
            text += f"❌ {amount}🍧 на {target} → Проигрыш\n"
    
    text += f"\n💸 Общий выигрыш: {win_total}🍧" if win_total else ""
    bot.send_message(msg.chat.id, text)

@bot.message_handler(func=lambda m: m.text.lower().startswith("п") and m.reply_to_message)
def transfer(msg):
    try:
        amount = int(msg.text.split()[1])
        if amount < 1:
            raise ValueError
    except:
        return bot.reply_to(msg, "⚠️ Пример: П 100 (ответом на сообщение)")
    
    from_uid = msg.from_user.id
    to_user = msg.reply_to_message.from_user
    
    if from_uid == to_user.id:
        return bot.reply_to(msg, "❌ Нельзя передать самому себе 🚫")
    
    balance = get_balance(from_uid)
    if balance < amount:
        return bot.reply_to(msg, "❌ Недостаточно мороженого 🍨")
    
    update_balance(from_uid, -amount)
    update_balance(to_user.id, amount)
    bot.reply_to(msg, f"✅ Передано {amount}🍧 игроку {to_user.first_name}")

@bot.message_handler(commands=["рассылка"])
def broadcast(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    
    text = msg.text.split(" ", 1)[1] if " " in msg.text else ""
    if not text:
        return bot.reply_to(msg, "❌ Укажите текст рассылки")
    
    success = 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 Рассылка от администратора ❄️🍧\n\n{text}")
            success += 1
        except:
            continue
    
    bot.reply_to(msg, f"✅ Рассылка отправлена {success} пользователям 🍦")

@bot.message_handler(func=lambda m: True)
def parse_bets(msg):
    uid = msg.from_user.id
    if uid in banned_users:
        return
    
    parts = msg.text.lower().split()
    if not parts or not parts[0].isdigit():
        return
    
    try:
        amount = int(parts[0])
        if amount < 10:
            return bot.reply_to(msg, "⚠️ Мин. ставка: 10🍧")
        
        targets = parts[1:]
        valid_targets = []
        for t in targets:
            if t.isdigit():
                num = int(t)
                if 0 <= num <= 36:
                    valid_targets.append(num)
            elif t in ['red', 'black', 'even', 'odd']:
                valid_targets.append(t)
        
        if not valid_targets:
            return bot.reply_to(msg, "❌ Нет валидных ставок")
        
        total = amount * len(valid_targets)
        
        if get_balance(uid) < total:
            return bot.reply_to(msg, f"❌ Недостаточно мороженого для {len(valid_targets)} ставок 🍨")
        
        update_balance(uid, -total)
        roulette_bets[uid] = []
        
        for t in valid_targets:
            roulette_bets[uid].append({
                'amount': amount,
                'target': t
            })
        
        bot.reply_to(msg, f"✅ Принято {len(valid_targets)} ставок по {amount}🍧. Пиши 'Го' для запуска! 🎰")
    except Exception as e:
        print(f"Ошибка в ставках: {e}")
        return

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()