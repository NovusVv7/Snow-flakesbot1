
import telebot
import sqlite3
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)

games = {}
roulette_bets = {}

COEFFS = [1.7, 2.5, 3, 4.67, 25]

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    # Удалите следующую строку, если не хотите удалять таблицу при каждом запуске
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            icecream INTEGER DEFAULT 1000
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

@bot.message_handler(commands=["start"])
def start(msg):
    add_user(msg.from_user)
    bot.send_message(msg.chat.id, "Добро пожаловать в IceCream Бота!\nКоманды:\n• Б — баланс\n• мины 100 — игра мины\n• ставка: 100 1 2 3\n• Го — запуск рулетки\n• /выдать ID сумма\n• /поиск — найти собеседника\n• /skip — пропустить")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "б")
def balance(msg):
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    name = msg.from_user.first_name
    bot.send_message(msg.chat.id, f"{name}\nБаланс: {bal} мороженого")

@bot.message_handler(commands=["выдать"])
def give(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, uid, amount = msg.text.split()
        uid = int(uid)
        amount = int(amount)
        update_balance(uid, amount)
        bot.send_message(msg.chat.id, f"Выдано {amount} мороженого пользователю {uid}")
    except:
        bot.reply_to(msg, "Пример: /выдать 123456789 1000000")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("мины"))
def mines(msg):
    uid = msg.from_user.id
    try:
        amount = int(msg.text.split()[1])
    except:
        return bot.reply_to(msg, "Пример: мины 100")
    if get_balance(uid) < amount:
        return bot.send_message(msg.chat.id, "Недостаточно мороженого!")
    update_balance(uid, -amount)
    mines = random.sample(range(25), 3)
    games[uid] = {"mines": mines, "opened": [], "bet": amount, "step": 0}
    send_mine_field(msg.chat.id, uid, "Мины разбросаны!")

def send_mine_field(chat_id, uid, text):
    markup = InlineKeyboardMarkup()
    g = games[uid]
    for i in range(5):
        row = []
        for j in range(5):
            idx = i * 5 + j
            label = "❔" if idx not in g["opened"] else "✅"
            row.append(InlineKeyboardButton(label, callback_data=f"open_{idx}"))
        markup.row(*row)
    markup.add(InlineKeyboardButton("ЗАБРАТЬ", callback_data="take"))
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("open_"))
def open_cell(call):
    uid = call.from_user.id
    if uid not in games:
        return
    idx = int(call.data.split("_")[1])
    g = games[uid]
    if idx in g["opened"]:
        return
    if idx in g["mines"]:
        del games[uid]
        bot.edit_message_text("Мина! Проигрыш.", call.message.chat.id, call.message.message_id)
        return
    g["opened"].append(idx)
    g["step"] += 1
    if g["step"] >= len(COEFFS):
        win = int(g["bet"] * COEFFS[-1])
        update_balance(uid, win)
        del games[uid]
        bot.edit_message_text(f"Ты прошёл всё поле! +{win} мороженого", call.message.chat.id, call.message.message_id)
    else:
        send_mine_field(call.message.chat.id, uid, f"Клеток: {g['step']}. Коэф: {COEFFS[g['step']-1]}")

@bot.message_handler(commands=["поиск"])
def search_command(msg):
    uid = msg.from_user.id
    # Удаляем из пар, если есть
    for u, v in list(games.items()):
        if u == uid:
            del games[u]
    # Ищем нового собеседника
    # В данном примере реализуем простую логику
    # В реальной реализации необходимо сохранять пары и искать их
    bot.send_message(msg.chat.id, "Ищу собеседника... Пожалуйста, подождите.")
    # Здесь должна быть логика поиска
    # Для примера просто отправляем сообщение
    # В реальности нужно реализовать очередь или список ожидания

@bot.message_handler(commands=["skip"])
def skip_command(msg):
    uid = msg.from_user.id
    # Удаляем пару
    # В реальности нужно хранить пары
    # Для примера просто сообщение
    bot.send_message(msg.chat.id, "Вы пропустили собеседника. Ищу нового...")
    # Логика поиска нового собеседника

# Обработка текстовых и мультимедийных сообщений
@bot.message_handler(content_types=["text", "photo", "video", "voice", "document"])
def handle_media(msg):
    # Если пользователь в паре, пересылаем мультимедиа
    # Для этого нужно хранить пары, например, в глобальном словаре
    # В данном примере пропущено
    pass

# Обработка команд /профиль
@bot.message_handler(commands=["профиль"])
def profile(msg):
    user_id = msg.from_user.id
    # Получить профиль из базы
    # Для примера
    bot.send_message(msg.chat.id, "Ваш профиль:\nКомментарии:\nНет комментариев.\nРеакции: 0")

# Запуск бота
bot.polling()