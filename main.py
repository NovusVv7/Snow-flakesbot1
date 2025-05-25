
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import random
import threading
import sqlite3

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные
COEFFS = [1.2, 1.5, 2, 3, 5]  # Пример коэффициентов для игры с минами
games = {}  # Хранение игр по user_id
roulette_bets = {}
roulette_history = []

# --- Функции обновления баланса и отправки поля с минами ---

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT icecream FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        new_balance = row[0] + amount
        c.execute("UPDATE users SET icecream=? WHERE user_id=?", (new_balance, user_id))
    else:
        c.execute("INSERT INTO users (user_id, icecream) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

def send_mine_field(chat_id, user_id, text):
    # Заглушка: нужно реализовать отправку игрового поля с кнопками
    markup = InlineKeyboardMarkup()
    for i in range(1, 10):
        btn = InlineKeyboardButton(str(i), callback_data=f"open_{i}")
        markup.add(btn)
    markup.add(InlineKeyboardButton("🏁 Забрать выигрыш 🍧", callback_data="take"))
    bot.edit_message_text(chat_id=chat_id, message_id=games[user_id]['message_id'], text=text, reply_markup=markup)

# --- Обработчики игры с минами (твой код с исправлениями) ---

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
        return bot.edit_message_text("🔄 Ставка возвращена 🍧", call.message.chat.id, call.message.message_id)

    win = int(g["bet"] * COEFFS[g["step"]-1])
    update_balance(uid, win)
    del games[uid]
    bot.edit_message_text(f"💰 Выигрыш: {win}🍧", call.message.chat.id, call.message.message_id)

# --- Рулетка (твой код с исправлениями) ---

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def go_roulette(msg):
    uid = msg.from_user.id
    if uid not in roulette_bets:
        return bot.send_message(msg.chat.id, "❌ Сначала сделай ставки! 🎰")

    sent_animation = bot.send_animation(msg.chat.id, animation="CgACAgIAAxkBAAICVGgyo8fx8r0-BW034uQ30js0atY1AAICWQAC96p5SC81RvIZJygENgQ")

    def delete_animation():
        try:
            bot.delete_message(msg.chat.id, sent_animation.message_id)
        except: 
            pass

    threading.Timer(7.0, delete_animation).start()

    bets = roulette_bets.pop(uid)
    result = random.randint(0, 36)
    roulette_history.append(result)

    text = f"🎲 Выпало число: {result}\n\n"
    win_total = 0
    RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    BLACK_NUMS = set(range(1, 37)) - RED_NUMS

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
            text += f"Ставка {amount} на {target} — победа +{prize}🍧\n"
        else:
            text += f"Ставка {amount} на {target} — проигрыш\n"

    if win_total > 0:
        text += f"\n💰 Итого выигрыш: {win_total}🍧"
    else:
        text += "\n😞 К сожалению, вы ничего не выиграли."

    bot.send_message(msg.chat.id, text)

# --- Игра "Кто кубы сумма" ---

@bot.message_handler(commands=['dicegame'])
def start_dice_game(msg):
    uid = msg.from_user.id
    text = "🎲 Игра 'Кто кубы сумма'!\nНажми кнопку, чтобы бросить кубики."
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Бросить кубики 🎲🎲", callback_data="dice_roll"))
    bot.send_message(msg.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "dice_roll")
def dice_roll(call):
    uid = call.from_user.id
    # Бросаем два кубика у пользователя
    user_dice_1 = random.randint(1, 6)
    user_dice_2 = random.randint(1, 6)
    user_sum = user_dice_1 + user_dice_2

    # Бросаем два кубика у бота
    bot_dice_1 = random.randint(1, 6)
    bot_dice_2 = random.randint(1, 6)
    bot_sum = bot_dice_1 + bot_dice_2

    text = (f"Ты бросил: {user_dice_1} и {user_dice_2} (сумма {user_sum})\n"
            f"Бот бросил: {bot_dice_1} и {bot_dice_2} (сумма {bot_sum})\n\n")

    if user_sum > bot_sum:
        text += "🎉 Ты выиграл!"
    elif user_sum < bot_sum:
        text += "😞 Ты проиграл!"
    else:
        text += "🤝 Ничья!"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

# --- Инициализация базы и запуск бота ---

if __name__ == "__main__":
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        icecream INTEGER DEFAULT 100000,
        last_bonus TEXT DEFAULT '1970-01-01T00:00:00'
    )""")
    conn.commit()
    conn.close()

    print("Бот запущен...")
    bot.infinity_polling()