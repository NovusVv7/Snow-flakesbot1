import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
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

# Команды администратора
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

# ... (остальные функции остаются без изменений из предыдущего кода) ...

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