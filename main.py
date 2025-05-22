
import telebot
import random
import sqlite3
import re  # Для проверки диапазонов в рулетке

# --------------- НАСТРОЙКИ БОТА -----------------
TOKEN = "YOUR_BOT_TOKEN"  # Замените на токен вашего бота
ADMIN_ID = YOUR_ADMIN_ID  # Замените на ваш Telegram ID
START_BALANCE_MIN = 5000
START_BALANCE_MAX = 100000
ROULETTE_NUMBERS = 37  # Числа в рулетке (0-36)
ADMIN_PASSWORD = "YOUR_ADMIN_PASSWORD" # Пароль для админских команд

bot = telebot.TeleBot(TOKEN)

# --------------- БАЗА ДАННЫХ -----------------
DATABASE_NAME = 'snowflakes.db'

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_tables(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def get_user_balance(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None
    except sqlite3.Error as e:
        print(e)
        return None

def update_user_balance(conn, user_id, amount):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, user_id))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def is_user_banned(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0] == 1
        else:
            return False
    except sqlite3.Error as e:
        print(e)
        return False

def ban_user(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def unban_user(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def add_new_user(conn, user_id, username):
    try:
        cursor = conn.cursor()
        start_balance = random.randint(START_BALANCE_MIN, START_BALANCE_MAX)
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, username, start_balance))
        conn.commit()
        return start_balance
    except sqlite3.Error as e:
        print(e)
        return None

def get_top_users(conn, limit=10):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(e)
        return []

conn = create_connection()
if conn:
    create_tables(conn)
    conn.close()

# --------------- ОБРАБОТЧИКИ КОМАНД -----------------

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username

    conn = create_connection()
    if conn:
        if get_user_balance(conn, user_id) is not None:
            bot.reply_to(message, "Привет! Ты уже зарегистрирован.")
        else:
            start_balance = add_new_user(conn, user_id, username)
            bot.reply_to(message, f"Привет! Ты получил стартовый бонус {start_balance} снежинок!")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

@bot.message_handler(commands=['balance']) # Баланс с /
@bot.message_handler(func=lambda message: message.text == "баланс")  # Баланс без /
def balance(message):
    user_id = message.from_user.id

    conn = create_connection()
    if conn:
        if is_user_banned(conn, user_id):
            bot.reply_to(message, "Ты забанен.")
        else:
            balance = get_user_balance(conn, user_id)
            if balance is not None:
                bot.reply_to(message, f"Твой баланс: {balance} снежинок")
            else:
                bot.reply_to(message, "Пользователь не найден. Используйте /start для регистрации.")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

@bot.message_handler(commands=['profile'])
def profile(message):
    user_id = message.from_user.id

    conn = create_connection()
    if conn:
        if is_user_banned(conn, user_id):
            bot.reply_to(message, "Ты забанен.")
        else:
            balance = get_user_balance(conn, user_id)
            if balance is not None:
                bot.reply_to(message, f"Твой баланс: {balance} снежинок")
            else:
                bot.reply_to(message, "Пользователь не найден. Используйте /start для регистрации.")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

@bot.message_handler(commands=['top'])
def top(message):
    conn = create_connection()
    if conn:
        top_users = get_top_users(conn)
        if top_users:
            text = "Топ игроков:\n"
            for i, user in enumerate(top_users):
                text += f"{i+1}. {user[1]} - {user[2]} снежинок (ID: {user[0]})\n"
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "Нет данных о пользователях.")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

roulette_players = {}  # {user_id: {'bet_amount': int, 'bet': str}}

@bot.message_handler(func=lambda message: message.text.lower() in ['go', 'го'])
def roulette_start(message):
    user_id = message.from_user.id
    roulette_players[user_id] = {} # Инициализация записи для игрока
    bot.reply_to(message, "Сделайте вашу ставку!  Пример: 100 15 (ставка 100 на число 15) или 50 1-10 (ставка 50 на диапазон 1-10)")

@bot.message_handler(func=lambda message: True)
def roulette_bet(message):
    user_id = message.from_user.id
    if user_id in roulette_players:
        if 'bet_amount' not in roulette_players[user_id]:
            try:
                parts = message.text.split()
                bet_amount = int(parts[0])
                bet = parts[1]

                conn = create_connection()
                if conn:
                    if is_user_banned(conn, user_id):
                        bot.reply_to(message, "Ты забанен.")
                        del roulette_players[user_id]  # Удаляем игрока из игры
                        conn.close()
                        return

                    balance = get_user_balance(conn, user_id)
                    if balance is None:
                        bot.reply_to(message, "Пользователь не найден. Используйте /start для регистрации.")
                        del roulette_players[user_id]  # Удаляем игрока из игры
                        conn.close()
                        return

                    if bet_amount <= 0:
                        bot.reply_to(message, "Сумма ставки должна быть больше 0.")
                        del roulette_players[user_id]  # Удаляем игрока из игры
                        conn.close()
                        return

                    if bet_amount > balance:
                        bot.reply_to(message, "У тебя недостаточно снежинок.")
                        del roulette_players[user_id]  # Удаляем игрока из игры
                        conn.close()
                        return

                    roulette_players[user_id]['bet_amount'] = bet_amount
                    roulette_players[user_id]['bet'] = bet
                    bot.reply_to(message, "Ставка принята! Ждем результатов...")

                    winning_number = random.randint(0, ROULETTE_NUMBERS - 1)

                    if '-' in bet:  # Ставка на диапазон
                        try:
                            start, end = map(int, bet.split('-'))
                            if 0 <= start <= end <= 36:
                                numbers = list(range(start, end + 1))
                                if winning_number in numbers:
                                    winnings = bet_amount * (36 / len(numbers)) # примерный коэффициент
                                    new_balance = balance - bet_amount + winnings
                                    update_user_balance(conn, user_id, new_balance)
                                    bot.reply_to(message, f"Выпало {winning_number}! Ты выиграл {int(winnings)} снежинок!\nНовый баланс: {int(new_balance)}")
                                else:
                                    new_balance = balance - bet_amount
                                    update_user_balance(conn, user_id, new_balance)
                                    bot.reply_to(message, f"Выпало {winning_number}. Ты проиграл {bet_amount} снежинок.\nНовый баланс: {new_balance}")

                            else:
                                bot.reply_to(message, "Неверный диапазон чисел. Должны быть от 0 до 36.")


                        except ValueError:
                            bot.reply_to(message, "Неправильный формат диапазона. Используйте: 1-10")


                    else: # Ставка на одно число
                        try:
                            bet_number = int(bet)
                            if not (0 <= bet_number <= 36):
                                bot.reply_to(message, "Пожалуйста, выберите число от 0 до 36.")
                            elif winning_number == bet_number:
                                winnings = bet_amount * 35
                                new_balance = balance - bet_amount + winnings
                                update_user_balance(conn, user_id, new_balance)
                                bot.reply_to(message, f"Выпало {winning_number}! Ты выиграл {winnings} снежинок!\nНовый баланс: {new_balance}")
                            else:
                                new_balance = balance - bet_amount
                                update_user_balance(conn, user_id, new_balance)
                                bot.reply_to(message, f"Выпало {winning_number}. Ты проиграл {bet_amount} снежинок.\nНовый баланс: {new_balance}")
                        except ValueError:
                            bot.reply_to(message, "Неправильный формат числа.  Введите число от 0 до 36, или диапазон.")


                    del roulette_players[user_id] # Удаляем игрока из игры
                    conn.close()
                else:
                    bot.reply_to(message, "Ошибка подключения к базе данных.")
                    del roulette_players[user_id] # Удаляем игрока из игры

            except (ValueError, IndexError):
                bot.reply_to(message, "Неправильный формат ставки. Используйте: <ставка> <число или диапазон>")
                del roulette_players[user_id] # Удаляем игрока из игры


# --------------- АДМИН КОМАНДЫ -----------------

@bot.message_handler(commands=['give'])
def give_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Нет прав.")
        return
    try:
        password = message.text.split()[1] # Добавлен пароль
        if password != ADMIN_PASSWORD:
            bot.reply_to(message, "Неверный пароль администратора.")
            return

        user_id = int(message.text.split()[2])
        amount = int(message.text.split()[3])

    except (IndexError, ValueError):
        bot.reply_to(message, "Используй: /give <пароль> <user_id> <количество>")
        return

    conn = create_connection()
    if conn:
        if get_user_balance(conn, user_id) is None:
            bot.reply_to(message, "Пользователь не найден.")
            conn.close()
            return

        balance = get_user_balance(conn, user_id)
        new_balance = balance + amount
        update_user_balance(conn, user_id, new_balance)

        bot.reply_to(message, f"Выдано {amount} снежинок для {user_id}")
        bot.send_message(user_id, f"Тебе выдано {amount} снежинок. Новый баланс: {new_balance}")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

@bot.message_handler(commands=['take'])
def take_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Нет прав.")
        return
    try:
        password = message.text.split()[1] # Добавлен пароль
        if password != ADMIN_PASSWORD:
            bot.reply_to(message, "Неверный пароль администратора.")
            return

        user_id = int(message.text.split()[2])
        amount = int(message.text.split()[3])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй: /take <пароль> <user_id> <количество>")
        return

    conn = create_connection()
    if conn:
        if get_user_balance(conn, user_id) is None:
            bot.reply_to(message, "Пользователь не найден.")
            conn.close()
            return
        balance = get_user_balance(conn, user_id)
        new_balance = max(0, balance - amount)
        update_user_balance(conn, user_id, new_balance)

        bot.reply_to(message, f"Забрано {amount} снежинок для {user_id}")
        bot.send_message(user_id, f"У тебя забрали {amount} снежинок. Новый баланс: {new_balance}")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

@bot.message_handler(commands=['ban'])
def ban_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Нет прав.")
        return
    try:
        password = message.text.split()[1] # Добавлен пароль
        if password != ADMIN_PASSWORD:
            bot.reply_to(message, "Неверный пароль администратора.")
            return

        user_id = int(message.text.split()[2])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй: /ban <пароль> <user_id>")
        return

    conn = create_connection()
    if conn:
        ban_user(conn, user_id)
        bot.reply_to(message, f"Пользователь {user_id} забанен.")
        bot.send_message(user_id, "Ты забанен.")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Нет прав.")
        return
    try:
        password = message.text.split()[1] # Добавлен пароль
        if password != ADMIN_PASSWORD: baz18
            bot.reply_to(message, "Неверный пароль администратора.")
            return
        user_id = int(message.text.split()[2])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй: /unban <пароль> <user_id>")
        return

    conn = create_connection()
    if conn:
        unban_user(conn, user_id)
        bot.reply_to(message, f"Пользователь {user_id} разбанен.")
        bot.send_message(user_id, "Ты разбанен.")
        conn.close()
    else:
        bot.reply_to(message, "Ошибка подключения к базе данных.")

# --------------- ЗАПУСК БОТА -----------------
if __name__ == '__main__':
    bot.polling(none_stop=True)