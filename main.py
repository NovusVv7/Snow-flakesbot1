import telebot
import sqlite3
import random
import datetime
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)

games = {}
roulette_bets = {}
banned_users = set()
roulette_history = []
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
        icecream INTEGER DEFAULT 1000,
        last_bonus TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS promos (
        promo TEXT PRIMARY KEY,
        amount INTEGER,
        max_uses INTEGER,
        used INTEGER DEFAULT 0)""")
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
        "🎁 Бонус - ежедневная награда (20к-30к)\n"
        "🍧 Б - проверить баланс\n"
        "💣 Мины 100 - игра в мины\n"
        "🎰 100 1 2 3 - ставки на рулетку\n"
        "🔄 П 1000 (ответом) - передать мороженое\n"
        "🏆 топ - топ игроков\n"
        "ℹ️ /info - информация о боте")

@bot.message_handler(commands=["info"])
def info(msg):
    add_user(msg.from_user)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT icecream, last_bonus FROM users WHERE user_id = ?", (msg.from_user.id,))
    row = c.fetchone()
    bal, last_bonus = row if row else (0, None)
    conn.close()
    
    status = "🟢 Доступен" if msg.from_user.id not in banned_users else "🔴 Забанен"
    last_bonus_time = "\n⏳ Последний бонус: " + datetime.datetime.fromisoformat(last_bonus).strftime("%d.%m %H:%M") if last_bonus else ""
    
    text = (
        f"❄️🍨 Личный кабинет IceCream Casino\n\n"
        f"👤 Имя: {msg.from_user.first_name}\n"
        f"🆔 ID: {msg.from_user.id}\n"
        f"💰 Баланс: {bal:,}🍧\n"
        f"📛 Статус: {status}"
        f"{last_bonus_time}"
    )
    bot.send_message(msg.chat.id, text.replace(',', ' '))

@bot.message_handler(func=lambda m: m.text.lower() == 'бонус')
def daily_bonus(msg):
    add_user(msg.from_user)
    uid = msg.from_user.id
    if uid in banned_users:
        return
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT last_bonus FROM users WHERE user_id = ?", (uid,))
    result = c.fetchone()
    last_bonus = result[0] if result else None
    
    if last_bonus:
        last_time = datetime.datetime.fromisoformat(last_bonus)
        if (datetime.datetime.now() - last_time) < datetime.timedelta(hours=24):
            delta = (last_time + datetime.timedelta(hours=24)) - datetime.datetime.now()
            hours = delta.seconds // 3600
            mins = (delta.seconds % 3600) // 60
            conn.close()
            return bot.send_message(msg.chat.id, 
                f"⏳ Следующий бонус через {hours}ч {mins}м")
    
    bonus = random.randint(20000, 30000)
    update_balance(uid, bonus)
    now = datetime.datetime.now().isoformat()
    c.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (now, uid))
    conn.commit()
    conn.close()
    
    bot.send_message(msg.chat.id, 
        f"🎁 Ежедневный бонус: {bonus:,}🍧\n"
        f"💳 Новый баланс: {get_balance(uid):,}🍨".replace(',', ' '))

@bot.message_handler(func=lambda m: m.text.lower() == "б")
def balance(msg):
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    bot.send_message(msg.chat.id, 
        f"👤 Игрок: {msg.from_user.first_name}\n"
        f"📦 Баланс: {bal:,}🍧\n"
        f"🆔 ID: {msg.from_user.id}".replace(',', ' '))

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

    if idx in g["mines"]:
        del games[uid]
        return bot.edit_message_text("💥 Ты подорвался на мине! 🚫", call.message.chat.id, call.message.message_id)

    if idx in g["opened"]:
        return

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
        except: pass

    threading.Timer(7.0, delete_animation).start()

    bets = roulette_bets.pop(uid)
    result = random.randint(0, 36)
    roulette_history.append(result)
    if len(roulette_history) > 10:
        roulette_history.pop(0)
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
            if target == "odd" and result % 2 == 1 and result !=0:
                prize = amount * 2
                win = True
            elif target == "even" and result !=0 and result % 2 ==0:
                prize = amount * 2
                win = True
            elif target == "red" and result in RED_NUMS:
                prize = amount * 2
                win = True
            elif target == "black" and result in BLACK_NUMS and result !=0:
                prize = amount * 2
                win = True
            elif target in ["1-12", "row1"] and 1 <= result <=12:
                prize = amount * 3
                win = True
            elif target in ["13-24", "row2"] and 13 <= result <=24:
                prize = amount * 3
                win = True
            elif target in ["25-36", "row3"] and 25 <= result <=36:
                prize = amount * 3
                win = True

        if win:
            update_balance(uid, prize)
            win_total += prize
            text += f"✅ {amount}🍧 на {target} → +{prize}🍨\n"
        else:
            text += f"❌ {amount}🍧 на {target} → Проигрыш\n"

    history_text = "📜 История: " + " ".join(
        [f"{n}{'🔴' if n in RED_NUMS else '⚫' if n !=0 else '🟣'}" for n in roulette_history[::-1]]
    )
    
    text += f"\n{history_text}"
    if win_total > 0:
        text += f"\n\n💸 Общий выигрыш: {win_total}🍧"
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

@bot.message_handler(func=lambda m: m.text.lower() == 'топ')
def top(msg):
    top_users = get_top_users()
    txt = "🏆 Топ игроков по мороженому 🍧:\n\n"
    for i, (name, uname, ice) in enumerate(top_users, 1):
        txt += f"{i}. {name} — {ice:,}🍨\n"
    bot.send_message(msg.chat.id, txt.replace(',', ' '))

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

@bot.message_handler(commands=["create_promo"])
def create_promo(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, promo, amount, max_uses = msg.text.split()
        amount = int(amount)
        max_uses = int(max_uses)
    except:
        return bot.reply_to(msg, "⚠️ Пример: /create_promo CODE 1000 5")
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO promos (promo, amount, max_uses) VALUES (?, ?, ?)",
                 (promo.upper(), amount, max_uses))
        conn.commit()
        bot.reply_to(msg, f"✅ Промокод {promo} создан!")
    except sqlite3.IntegrityError:
        bot.reply_to(msg, "❌ Промокод уже существует")
    conn.close()

@bot.message_handler(commands=["promo"])
def use_promo(msg):
    try:
        promo = msg.text.split()[1].upper()
    except:
        return bot.reply_to(msg, "⚠️ Пример: /promo CODE123")
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT amount, max_uses, used FROM promos WHERE promo = ?", (promo,))
    row = c.fetchone()
    if not row:
        conn.close()
        return bot.reply_to(msg, "❌ Промокод не найден")
    
    amount, max_uses, used = row
    if used >= max_uses:
        conn.close()
        return bot.reply_to(msg, "⚠️ Промокод закончился")
    
    c.execute("UPDATE promos SET used = used + 1 WHERE promo = ?", (promo,))
    update_balance(msg.from_user.id, amount)
    conn.commit()
    conn.close()
    bot.reply_to(msg, f"✅ Активирован промокод! +{amount}🍧")

@bot.message_handler(func=lambda m: True)
def parse_bets(msg):
    uid = msg.from_user.id
    if uid in banned_users:
        return

    parts = msg