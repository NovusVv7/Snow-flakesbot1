import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import sqlite3
import random
import config
from contextlib import contextmanager
import re

# Настройка базы данных
conn = sqlite3.connect('snowflakes.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, 
              username TEXT,
              snowflakes INTEGER DEFAULT 0,
              banned BOOLEAN DEFAULT FALSE)''')
conn.commit()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Константы
CREATOR_ID = config.CREATOR_ID
active_bets = {}
PAYOUTS = {
    1: 35,   # Прямая ставка
    2: 17,   # Сплит
    3: 11,   # Стрит
    4: 8,    # Угол
    6: 5,    # Линия
    12: 2,   # Дюжины/колонки
    18: 1    # Чет/нечет, красное/черное
}

@contextmanager
def db_transaction():
    try:
        yield
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Database error: {str(e)}")

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.full_name
    try:
        with db_transaction():
            cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            update.message.reply_text("❄️ Добро пожаловать в Snowflake Bot! Используй команды:\n"
                                    "💎 Баланс/Б - показать снежинки\n"
                                    "🎰 Рулетка [сумма] числа... - сделать ставку\n"
                                    "🏁 Го - запустить рулетку\n"
                                    "🎁 Передать @юзер сумма\n"
                                    "❌ Отмена - отменить текущую ставку")
    except Exception as e:
        logging.error(f"Start error: {str(e)}")
        update.message.reply_text("❌ Ошибка регистрации")

def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        with db_transaction():
            user = cursor.execute("SELECT username, snowflakes FROM users WHERE user_id=?", (user_id,)).fetchone()
            if user:
                username = user[0] or "Без ника"
                update.message.reply_text(
                    f"👤 Профиль: {username}\n"
                    f"❄️ Баланс: {user[1]} снежинок"
                )
            else:
                update.message.reply_text("❌ Вы не зарегистрированы. Используйте /start")
    except Exception as e:
        logging.error(f"Balance error: {str(e)}")
        update.message.reply_text("❌ Ошибка получения баланса")

def transfer(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = update.message.text.split()[1:]

    if len(args) != 2 or not args[1].isdigit():
        update.message.reply_text("❌ Формат: Передать @юзер сумма")
        return

    recipient_username = args[0].lstrip('@')
    amount = int(args[1])

    if amount <= 0:
        update.message.reply_text("❌ Сумма должна быть положительной")
        return

    try:
        with db_transaction():
            sender = cursor.execute("SELECT snowflakes, banned FROM users WHERE user_id=?", (user_id,)).fetchone()
            if not sender:
                update.message.reply_text("❌ Вы не зарегистрированы")
                return
            if sender[1]:
                update.message.reply_text("⛔ Вы забанены!")
                return
            if sender[0] < amount:
                update.message.reply_text("❌ Недостаточно снежинок")
                return

            recipient = cursor.execute("SELECT user_id FROM users WHERE username=?", (recipient_username,)).fetchone()
            if not recipient:
                update.message.reply_text("❌ Пользователь не найден")
                return

            cursor.execute("UPDATE users SET snowflakes = snowflakes - ? WHERE user_id=?", (amount, user_id))
            cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE user_id=?", (amount, recipient[0]))
            update.message.reply_text(f"✅ Успешно передано {amount} снежинок пользователю @{recipient_username}")

    except Exception as e:
        logging.error(f"Transfer error: {str(e)}")
        update.message.reply_text("❌ Ошибка при переводе средств")

def roulette(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = update.message.text.split()[1:]

    if not args:
        update.message.reply_text("❌ Формат: Рулетка [ставка] числа через пробел\nПример: Рулетка 20000 2 4 6 9 14...")
        return

    try:
        bet = int(args[0])
        if bet < 10:
            update.message.reply_text("❌ Минимальная ставка: 10 снежинок")
            return
    except ValueError:
        update.message.reply_text("❌ Неверная сумма ставки")
        return

    numbers = []
    for item in args[1:]:
        if item.isdigit():
            num = int(item)
            if 0 <= num <= 36:
                numbers.append(num)
            else:
                update.message.reply_text(f"❌ Некорректное число: {item}")
                return
        else:
            update.message.reply_text(f"❌ Некорректный формат: {item}")
            return

    if not numbers:
        update.message.reply_text("❌ Укажите числа для ставки")
        return

    active_bets[user_id] = {
        'bet': bet,
        'numbers': numbers,
        'payout': 35 // len(numbers)
    }

    update.message.reply_text(
        f"❄️ Ставка {bet} снежинок на числа: {', '.join(map(str, numbers))}\n"
        f"Коэффициент: x{active_bets[user_id]['payout']}\n"
        "Напишите 'ГО' чтобы запустить рулетку или 'ОТМЕНА' для отмены"
    )

def start_roulette(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in active_bets:
        update.message.reply_text("❌ Нет активных ставок")
        return

    bet_data = active_bets.pop(user_id)

    try:
        with db_transaction():
            user = cursor.execute("SELECT snowflakes, banned FROM users WHERE user_id=?", (user_id,)).fetchone()
            if not user:
                update.message.reply_text("❌ Вы не зарегистрированы")
                return
            if user[1]:
                update.message.reply_text("⛔ Вы забанены!")
                return
            if user[0] < bet_data['bet']:
                update.message.reply_text("❌ Недостаточно снежинок")
                return

            cursor.execute("UPDATE users SET snowflakes = snowflakes - ? WHERE user_id=?", (bet_data['bet'], user_id))
            
            result = random.randint(0, 36)
            red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
            color = 'красное' if result in red_numbers else 'черное' if result !=0 else 'зеленое'

            if result in bet_data['numbers']:
                win_amount = bet_data['bet'] * bet_data['payout']
                cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE user_id=?", (win_amount, user_id))
                message = (
                    f"🎉 ВЫИГРЫШ!\n"
                    f"Выпало: {result} ({color})\n"
                    f"💰 +{win_amount} снежинок!"
                )
            else:
                message = (
                    f"💔 ПРОИГРЫШ\n"
                    f"Выпало: {result} ({color})\n"
                    f"❄️ -{bet_data['bet']} снежинок"
                )

            update.message.reply_text(message)

    except Exception as e:
        logging.error(f"Roulette error: {str(e)}")
        update.message.reply_text("❌ Ошибка в игре")

def cancel_bet(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in active_bets:
        del active_bets[user_id]
        update.message.reply_text("❄️ Ставка отменена!")
    else:
        update.message.reply_text("❌ Нет активных ставок")

def add_snowflakes(update: Update, context: CallbackContext):
    if update.effective_user.id != CREATOR_ID:
        update.message.reply_text("❌ У вас нет прав на эту команду.")
        return

    args = context.args
    if len(args) < 2:
        update.message.reply_text("❌ Формат: /add_snowflakes @username количество")
        return

    username = args[0].lstrip('@')
    try:
        amount = int(args[1])
        if amount <= 0:
            update.message.reply_text("❌ Количество должно быть положительным числом.")
            return
    except ValueError:
        update.message.reply_text("❌ Неверное количество снежинок.")
        return

    try:
        with db_transaction():
            user = cursor.execute(
                "SELECT user_id FROM users WHERE username=?", 
                (username,)
            ).fetchone()
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return

            cursor.execute(
                "UPDATE users SET snowflakes = snowflakes + ? WHERE user_id=?",
                (amount, user[0])
            )

            update.message.reply_text(f"✅ Успешно выдано {amount} снежинок пользователю @{username}.")
            
            try:
                context.bot.send_message(
                    chat_id=user[0], 
                    text=f"🎁 Вам было начислено {amount} снежинок!"
                )
            except Exception as e:
                logging.error(f"Ошибка уведомления: {e}")

    except Exception as e:
        logging.error(f"Ошибка выдачи: {e}")
        update.message.reply_text("❌ Ошибка выполнения команды.")

def main():
    updater = Updater(config.TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex(re.compile(r'^(баланс|б)$', re.IGNORECASE)), balance))
    dp.add_handler(MessageHandler(Filters.regex(r'^рулетка '), roulette))
    dp.add_handler(MessageHandler(Filters.regex(r'^го$'), start_roulette))
    dp.add_handler(MessageHandler(Filters.regex(r'^отмена$'), cancel_bet))
    dp.add_handler(MessageHandler(Filters.regex(r'^передать '), transfer))
    dp.add_handler(CommandHandler(
        "add_snowflakes", 
        add_snowflakes, 
        filters=Filters.user(user_id=CREATOR_ID)
    ))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()