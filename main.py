import sqlite3
import random
import time
from telebot import TeleBot, types

TOKEN = "7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U"
ADMIN_ID = 6359584002
bot = TeleBot(TOKEN)

# Константы для рулетки
RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMS = set(range(1, 37)) - RED_NUMS
ROULETTE_MULTI_BETS = {
    1: 36, 2: 18, 3: 12, 4: 9, 6: 6, 12: 3
}

def init_db():
    conn = sqlite3.connect("waifubot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        icecream INTEGER DEFAULT 0,
        waifu TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        reward INTEGER,
        used_by TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS girls (
        user_id INTEGER PRIMARY KEY,
        number INTEGER,
        income INTEGER DEFAULT 0,
        hunger INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect("waifubot.db")
    c = conn.cursor()
    c.execute("SELECT icecream FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect("waifubot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    c.execute("UPDATE users SET icecream = icecream + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ... (остальные функции из оригинального кода остаются без изменений)

@bot.message_handler(func=lambda m: m.text.lower().startswith(('рулетка', 'ставка')))
def roulette_handler(msg):
    try:
        args = msg.text.split()[1:]
        if len(args) < 2:
            return bot.reply_to(msg, "🌀 Формат: Рулетка [Сумма] [Числа через пробел]\nПример: Рулетка 200 4 8 36")

        uid = msg.from_user.id
        bet_amount = int(args[0])
        numbers = list(map(int, args[1:]))
        
        # Валидация
        if bet_amount < 10:
            return bot.reply_to(msg, "❗ Минимальная ставка 10 🍦")
        if any(n < 0 or n > 36 for n in numbers):
            return bot.reply_to(msg, "❌ Числа должны быть от 0 до 36!")
        if len(numbers) not in ROULETTE_MULTI_BETS:
            return bot.reply_to(msg, "⚠ Недопустимое количество чисел. Допустимо: 1,2,3,4,6,12")

        total_bet = bet_amount * len(numbers)
        if get_balance(uid) < total_bet:
            return bot.reply_to(msg, f"💸 Недостаточно средств! Нужно: {total_bet} 🍦")

        # Делаем ставку
        update_balance(uid, -total_bet)
        result = random.randint(0, 36)
        color = "красное" if result in RED_NUMS else "черное" if result != 0 else "зеленое"
        
        # Проверяем выигрыш
        win_numbers = [n for n in numbers if n == result]
        multiplier = ROULETTE_MULTI_BETS[len(numbers)] if win_numbers else 0
        total_win = bet_amount * multiplier * len(win_numbers)

        if total_win > 0:
            update_balance(uid, total_win)

        # Формируем отчет
        report = [
            f"🎰 Результат: {result} {['🔴','⚫','🟢'][result%3]}",
            f"▫ Ставка: {bet_amount} 🍦 x{len(numbers)}",
            f"▫ Числа: {', '.join(map(str, numbers))}",
            f"▫ Выигрыш: {total_win} 🍦 (x{multiplier})" if total_win > 0 else "▫ Выигрыша нет 😢"
        ]

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🔄 Повторить", callback_data=f"roulette_retry_{bet_amount}"),
            types.InlineKeyboardButton("📊 Статистика", callback_data="roulette_stats")
        )
        
        bot.send_message(
            msg.chat.id,
            "\n".join(report),
            reply_markup=markup
        )

    except Exception as e:
        bot.reply_to(msg, f"⚠ Ошибка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('roulette_retry_'))
def retry_roulette(call):
    bet_amount = call.data.split('_')[-1]
    bot.send_message(call.message.chat.id, 
                    f"♻ Введите числа для повторной ставки на {bet_amount} 🍦\nПример: 4 8 36")

# ... (остальные обработчики из оригинального кода остаются без изменений)

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()