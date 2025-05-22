
import telebot
import random
import sqlite3

# --------------- НАСТРОЙКИ БОТА -----------------
TOKEN = "YOUR_BOT_TOKEN"  # Замените на токен вашего бота
ADMIN_ID = YOUR_ADMIN_ID  # Замените на ваш Telegram ID
START_BALANCE_MIN = 5000
START_BALANCE_MAX = 100000
ROULETTE_NUMBERS = 37  # Числа в рулетке (0-36)
DUEL_DAMAGE = 20  # Урон от выстрела в дуэли
DUEL_MAX_HEALTH = 100

bot = telebot.TeleBot(TOKEN)

# --------------- БАЗА ДАННЫХ -----------------
def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('snowflakes.db')
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
                banned INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100 
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

def get_user_health(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT health FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return DUEL_MAX_HEALTH # Default health
    except sqlite3.Error as e:
        print(e)
        return DUEL_MAX_HEALTH

def update_user_health(conn, user_id, health):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET health=? WHERE user_id=?", (health, user_id))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

conn = create_connection()
if conn:
    create_tables(conn)

# --------------- ОБРАБОТЧИКИ КОМАНД -----------------

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    if is_user_registered(user_id):
        bot.reply_to(message, "Привет! Ты уже зарегистрирован.")
    else:
        start_balance = register_user(user_id, username)
        bot.reply_to(message, f"Привет! Ты получил стартовый бонус {start_balance} снежинок!")

def is_user_registered(user_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    else:
        return False

def register_user(user_id, username):
    conn = create_connection()
    if conn:
        start_balance = add_new_user(conn, user_id, username)
        conn.close()
        return start_balance
    else:
        return 0


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
                bot.reply_to(message, "Произошла ошибка при получении баланса.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")


@bot.message_handler(commands=['top'])
def top(message):
    conn = create_connection()
    if conn:
        top_users = get_top_users(conn)
        if top_users:
            text = "Топ игроков:\n"
            for i, user in enumerate(top_users):
                text += f"{i+1}. {user[1]} (ID: {user[0]}) - {user[2]} снежинок\n"
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "Нет данных о пользователях.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")


@bot.message_handler(commands=['roulette'])
def roulette(message):
    user_id = message.from_user.id
    conn = create_connection()
    if conn:
        if is_user_banned(conn, user_id):
            bot.reply_to(message, "Ты забанен.")
            conn.close()
            return

        try:
            bet_amount = int(message.text.split()[1])
            bet_number = int(message.text.split()[2])  # Get the bet number from the command

            if not (0 <= bet_number <= 36):
                bot.reply_to(message, "Пожалуйста, выберите число от 0 до 36.")
                conn.close()
                return

            balance = get_user_balance(conn, user_id)
            if balance is None:
                bot.reply_to(message, "Произошла ошибка при получении баланса.")
                conn.close()
                return

            if bet_amount <= 0:
                bot.reply_to(message, "Сумма ставки должна быть больше 0.")
                conn.close()
                return

            if bet_amount > balance:
                bot.reply_to(message, "У тебя недостаточно снежинок.")
                conn.close()
                return

        except (IndexError, ValueError):
            bot.reply_to(message, "Используй команду так: /roulette <ставка> <число>")
            conn.close()
            return

        winning_number = random.randint(0, ROULETTE_NUMBERS - 1)  # Generate winning number from 0 to 36

        if winning_number == bet_number:
            winnings = bet_amount * 35  # Payout is 35:1 if you win
            update_user_balance(conn, user_id, balance - bet_amount + winnings)  # Subtract bet, add winnings
            bot.reply_to(message, f"Выпало {winning_number}! Ты выиграл {winnings} снежинок!")
        else:
            update_user_balance(conn, user_id, balance - bet_amount)  # Subtract the bet amount
            bot.reply_to(message, f"Выпало {winning_number}. Ты проиграл {bet_amount} снежинок.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")


duel_states = {}  # {user_id: {'opponent_id': ..., 'stage': 'waiting'/'aiming'/'shooting'}}

@bot.message_handler(commands=['duel'])
def duel(message):
    user_id = message.from_user.id

    try:
        opponent_id = int(message.text.split()[1]) # Extract user ID from the command
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй команду: /duel <user_id>")
        return

    if user_id == opponent_id:
        bot.reply_to(message, "Нельзя вызвать на дуэль самого себя.")
        return

    if user_id in duel_states and duel_states[user_id]['stage'] != 'finished':
        bot.reply_to(message, "У тебя уже есть активный дуэль.")
        return

    # Check if the opponent is already in a duel
    for user, state in duel_states.items():
        if state['opponent_id'] == user_id and state['stage'] != 'finished':
            bot.reply_to(message, "Этот игрок уже участвует в дуэли.")
            return

    duel_states[user_id] = {'opponent_id': opponent_id, 'stage': 'waiting'}
    bot.send_message(opponent_id, f"{message.from_user.username} вызвал тебя на дуэль! Прими вызов командой /acceptduel {user_id}")
    bot.reply_to(message, f"Вызов на дуэль отправлен игроку с ID {opponent_id}.")

@bot.message_handler(commands=['acceptduel'])
def accept_duel(message):
    user_id = message.from_user.id

    try:
        challenger_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй команду: /acceptduel <user_id>")
        return

    if challenger_id not in duel_states or duel_states[challenger_id]['opponent_id'] != user_id or duel_states[challenger_id]['stage'] != 'waiting':
        bot.reply_to(message, "Этот вызов на дуэль недействителен.")
        return

    duel_states[challenger_id]['stage'] = 'aiming'
    duel_states[user_id] = {'opponent_id': challenger_id, 'stage': 'aiming'}

    conn = create_connection()
    if conn:
        # Reset health for both duelers
        update_user_health(conn, challenger_id, DUEL_MAX_HEALTH)
        update_user_health(conn, user_id, DUEL_MAX_HEALTH)
        conn.close()

    bot.send_message(challenger_id, "Дуэль принята! Прицелься командой /aim")
    bot.reply_to(message, "Ты принял вызов на дуэль! Прицелься командой /aim")

@bot.message_handler(commands=['aim'])
def aim(message):
    user_id = message.from_user.id

    if user_id not in duel_states or duel_states[user_id]['stage'] != 'aiming':
        bot.reply_to(message, "Ты не участвуешь в дуэли или не можешь прицелиться сейчас.")
        return

    duel_states[user_id]['stage'] = 'shooting'
    bot.reply_to(message, "Ты прицелился! Стреляй командой /shoot")

@bot.message_handler(commands=['shoot'])
def shoot(message):
    user_id = message.from_user.id

    if user_id not in duel_states or duel_states[user_id]['stage'] != 'shooting':
        bot.reply_to(message, "Ты не прицелился или не участвуешь в дуэли.")
        return

    opponent_id = duel_states[user_id]['opponent_id']

    conn = create_connection()
    if conn:
        user_health = get_user_health(conn, user_id)
        opponent_health = get_user_health(conn, opponent_id)

        # Calculate the damage to the opponent's health
        new_opponent_health = max(0, opponent_health - DUEL_DAMAGE)
        update_user_health(conn, opponent_id, new_opponent_health)

        bot.send_message(opponent_id, f"Тебя подстрелил {message.from_user.username}! У тебя осталось {new_opponent_health} здоровья.")
        bot.reply_to(message, f"Ты выстрелил в {get_user_name(opponent_id)}! У него осталось {new_opponent_health} здоровья.")

        if new_opponent_health <= 0:
            bot.send_message(opponent_id, f"Ты проиграл дуэль {message.from_user.username}!")
            bot.reply_to(message, f"Ты победил в дуэли {get_user_name(opponent_id)}!")
            duel_states[user_id]['stage'] = 'finished'
            # Reset the health for the next duel
            update_user_health(conn, user_id, DUEL_MAX_HEALTH)
            update_user_health(conn, opponent_id, DUEL_MAX_HEALTH)

            #End the duel for both players
            if opponent_id in duel_states:
                duel_states[opponent_id]['stage'] = 'finished'
        else:
            # Return the opponent to the aiming stage for the next turn
            duel_states[opponent_id]['stage'] = 'aiming'
            bot.send_message(opponent_id, "Прицелься командой /aim")

        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")

def get_user_name(user_id):
     try:
        user = bot.get_chat(user_id)
        return user.username
     except telebot.apihelper.ApiException as e:
         print(f"Error getting username for user {user_id}: {e}")
         return "Unknown User" # Handle cases where user is not found or has no username

# --------------- АДМИН КОМАНДЫ -----------------

@bot.message_handler(commands=['give'])
def give(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У тебя нет прав на эту команду.")
        return

    try:
        user_id = int(message.text.split()[1])
        amount = int(message.text.split()[2])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй команду так: /give <user_id> <количество>")
        return

    conn = create_connection()
    if conn:
        balance = get_user_balance(conn, user_id)
        if balance is None:
            bot.reply_to(message, "Пользователь не найден.")
            conn.close()
            return

        update_user_balance(conn, user_id, balance + amount)
        bot.reply_to(message, f"Выдано {amount} снежинок пользователю с ID {user_id}")
        bot.send_message(user_id, f"Тебе выдали {amount} снежинок.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")

@bot.message_handler(commands=['take'])
def take(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У тебя нет прав на эту команду.")
        return

    try:
        user_id = int(message.text.split()[1])
        amount = int(message.text.split()[2])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй команду так: /take <user_id> <количество>")
        return

    conn = create_connection()
    if conn:
        balance = get_user_balance(conn, user_id)
        if balance is None:
            bot.reply_to(message, "Пользователь не найден.")
            conn.close()
            return

        new_balance = max(0, balance - amount)
        update_user_balance(conn, user_id, new_balance)
        bot.reply_to(message, f"Забрано {amount} снежинок у пользователя с ID {user_id}")
        bot.send_message(user_id, f"У тебя забрали {amount} снежинок.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")

@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У тебя нет прав на эту команду.")
        return

    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй команду так: /ban <user_id>")
        return

    conn = create_connection()
    if conn:
        ban_user(conn, user_id)
        bot.reply_to(message, f"Пользователь с ID {user_id} забанен.")
        bot.send_message(user_id, "Ты забанен.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У тебя нет прав на эту команду.")
        return

    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Используй команду так: /unban <user_id>")
        return

    conn = create_connection()
    if conn:
        unban_user(conn, user_id)
        bot.reply_to(message, f"Пользователь с ID {user_id} разбанен.")
        bot.send_message(user_id, "Ты разбанен.")
        conn.close()
    else:
        bot.reply_to(message, "Произошла ошибка при подключении к базе данных.")

# --------------- ЗАПУСК БОТА -----------------
if __name__ == '__main__':
    bot.polling(none_stop=True)
