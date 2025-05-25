import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)
roulette_bets = {}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        icecream INTEGER DEFAULT 1000,
        banned BOOLEAN DEFAULT FALSE
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        amount INTEGER,
        uses_left INTEGER
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS roulette_log (
        user_id INTEGER,
        username TEXT,
        bet_amount INTEGER,
        bet_numbers TEXT,
        result INTEGER,
        win_amount INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.commit()
    conn.close()

# Проверка прав администратора
def is_admin(user_id):
    return user_id == ADMIN_ID

# Добавление пользователя
def add_user(user):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users 
              (user_id, username, first_name, icecream) 
              VALUES (?, ?, ?, 1000)""",
              (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()

# Получение баланса
def get_balance(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT icecream FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

# Обновление баланса
def update_balance(uid, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    c.execute("UPDATE users SET icecream = icecream + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    conn.close()

# Проверка бана
def check_ban(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else False

# Обработка ставок
def process_bet(p):
    p = p.lower()
    if p in ['чет', 'even', 'чёт', 'четное', 'ч']:
        return [n for n in range(1,37) if n%2 == 0]
    elif p in ['нечет', 'odd', 'нечёт', 'нечетное', 'н']:
        return [n for n in range(1,37) if n%2 != 0]
    elif p in ['красное', 'red', 'к']:
        return RED_NUMBERS
    elif p in ['черное', 'black', 'ч']:
        return BLACK_NUMBERS
    elif p.isdigit() and 0 <= int(p) <= 36:
        return [int(p)]
    return None

# Команды бота
@bot.message_handler(commands=["start"])
def start(msg):
    add_user(msg.from_user)
    bot.send_message(msg.chat.id, "❄️ Добро пожаловать в IceCream Casino!\n\n"
                     "Основные команды:\n"
                     "• Б - Проверить баланс\n"
                     "• П [сумма] - Перевод (ответом на сообщение)\n"
                     "• [ставка] [числа/типы] - Сделать ставку\n"
                     "• Го - Запустить рулетку\n\n"
                     "Пример ставки: 100 красное чет 12")

@bot.message_handler(func=lambda m: m.text.lower() == "б")
def balance(msg):
    if check_ban(msg.from_user.id):
        return
    add_user(msg.from_user)
    bal = get_balance(msg.from_user.id)
    bot.send_message(msg.chat.id, f"🍦 Ваш баланс: {bal}")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('П '))
def transfer(msg):
    if check_ban(msg.from_user.id):
        return bot.reply_to(msg, "⛔ Вы забанены!")
    
    if not msg.reply_to_message:
        return bot.reply_to(msg, "❌ Ответьте на сообщение получателя!")
    
    try:
        amount = int(msg.text.split()[1])
        if amount <= 0:
            raise ValueError
    except:
        return bot.reply_to(msg, "❌ Формат: П [сумма]")
    
    sender = msg.from_user
    recipient = msg.reply_to_message.from_user
    
    if get_balance(sender.id) < amount:
        return bot.reply_to(msg, "❌ Недостаточно средств!")
    
    update_balance(sender.id, -amount)
    update_balance(recipient.id, amount)
    bot.reply_to(msg, f"✅ Успешно переведено {amount}🍦\n"
                 f"Получатель: {recipient.first_name}")

@bot.message_handler(func=lambda m: m.text and any(c.isdigit() for c in m.text.split()[0]))
def parse_bets(msg):
    uid = msg.from_user.id
    if check_ban(uid):
        return
    
    try:
        parts = msg.text.split()
        amount = int(parts[0])
        numbers = []
        types = []
        
        for p in parts[1:]:
            nums = process_bet(p)
            if nums:
                numbers.extend(nums)
                types.append(p)
        
        numbers = list(set(numbers))
        if not numbers:
            return bot.reply_to(msg, "❌ Укажите числа или типы ставок!")
        
        if amount < 1:
            return bot.reply_to(msg, "❌ Минимальная ставка: 1🍦")
        
        balance = get_balance(uid)
        if balance < amount:
            return bot.reply_to(msg, f"❌ Недостаточно средств! Баланс: {balance}🍦")
        
        update_balance(uid, -amount)
        roulette_bets[uid] = {
            'amount': amount,
            'numbers': numbers,
            'types': types
        }
        
        bot.reply_to(msg, f"✅ Ставка принята!\n"
                     f"Сумма: {amount}🍦\n"
                     f"Количество чисел: {len(numbers)}\n"
                     f"Напишите 'Го' для запуска рулетки!")

    except Exception as e:
        print(f"Ошибка ставки: {e}")
        bot.reply_to(msg, "❌ Ошибка формата ставки!\nПример: 100 красное чет 12")

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def roulette_start(msg):
    uid = msg.from_user.id
    if check_ban(uid):
        return
    
    if uid not in roulette_bets:
        return bot.reply_to(msg, "❌ Сначала сделайте ставку!")
    
    try:
        bet = roulette_bets[uid]
        anim = bot.send_message(msg.chat.id, "🎡 Запуск рулетки...")
        
        # Анимация
        for i in range(3):
            time.sleep(0.7)
            bot.edit_message_text(f"🌀 Крутим... {random.randint(0,36)}",
                                msg.chat.id,
                                anim.message_id)
        
        # Результат
        result = random.randint(0, 36)
        color = 'красное' if result in RED_NUMBERS else 'черное' if result in BLACK_NUMBERS else ''
        parity = 'чет' if result%2 == 0 and result !=0 else 'нечет' if result !=0 else ''
        
        # Обновление сообщения
        bot.edit_message_text(f"🎯 Результат: {result} {color} {parity}",
                            msg.chat.id,
                            anim.message_id)
        
        # Расчет выигрыша
        win = 0
        coeff = 36 / len(bet['numbers']) if 0 < len(bet['numbers']) < 18 else 2
        
        if result in bet['numbers']:
            win = int(bet['amount'] * coeff)
            update_balance(uid, win)
        
        # Логирование
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("""INSERT INTO roulette_log 
                  (user_id, username, bet_amount, bet_numbers, result, win_amount)
                  VALUES (?, ?, ?, ?, ?, ?)""",
                  (uid, msg.from_user.username, bet['amount'], str(bet['numbers']), result, win))
        conn.commit()
        conn.close()
        
        # Результат
        result_text = (f"▫️ Ставка: {bet['amount']}🍦\n"
                      f"▫️ Коэффициент: x{coeff:.1f}\n"
                      f"▫️ Выигрыш: {'+' + str(win) if win else '0'}\n"
                      f"▫️ Новый баланс: {get_balance(uid)}🍦")
        
        del roulette_bets[uid]
        bot.send_message(msg.chat.id, result_text)

    except Exception as e:
        print(f"Ошибка рулетки: {e}")
        bot.reply_to(msg, "❌ Ошибка, попробуйте снова")

# Админ-команды
@bot.message_handler(commands=["give"])
def give_icecream(msg):
    if not is_admin(msg.from_user.id):
        return
    
    try:
        args = msg.text.split()[1:]
        if msg.reply_to_message:
            amount = int(args[0])
            user = msg.reply_to_message.from_user
        else:
            amount = int(args[0])
            user_id = int(args[1])
            user = bot.get_chat_member(user_id, user_id).user
    except:
        return bot.reply_to(msg, "❌ Формат:\n/give [сумма] [user_id]\nили ответом /give [сумма]")
    
    update_balance(user.id, amount)
    bot.reply_to(msg, f"✅ Выдано {amount}🍦 пользователю {user.first_name}")

@bot.message_handler(commands=["stats"])
def stats(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(icecream) FROM users")
    total_icecream = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM roulette_log")
    total_bets = c.fetchone()[0]
    
    conn.close()
    
    stats_text = (f"📊 Статистика бота:\n"
                 f"👥 Пользователей: {total_users}\n"
                 f"🍦 Всего мороженого: {total_icecream}\n"
                 f"🎰 Сыграно ставок: {total_bets}")
    bot.reply_to(msg, stats_text)

@bot.message_handler(commands=["top"])
def top_balance(msg):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, icecream FROM users ORDER BY icecream DESC LIMIT 10")
    top = c.fetchall()
    conn.close()
    
    top_text = "🏆 Топ игроков:\n"
    for i, (name, balance) in enumerate(top, 1):
        top_text += f"{i}. {name} - {balance}🍦\n"
    
    bot.send_message(msg.chat.id, top_text)

@bot.message_handler(commands=["take"])
def take_icecream(msg):
    if not is_admin(msg.from_user.id):
        return
    
    try:
        args = msg.text.split()[1:]
        user_id = int(args[1])
        amount = int(args[0])
    except:
        return bot.reply_to(msg, "❌ Формат: /take [сумма] [user_id]")
    
    current = get_balance(user_id)
    take = min(amount, current)
    update_balance(user_id, -take)
    bot.reply_to(msg, f"✅ Изъято {take}🍦 у пользователя {user_id}")

@bot.message_handler(commands=["ban"])
def ban_user(msg):
    if not is_admin(msg.from_user.id):
        return
    
    try:
        user_id = int(msg.text.split()[1])
    except:
        return bot.reply_to(msg, "❌ Формат: /ban [user_id]")
    
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET banned = TRUE WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(msg, f"⛔ Пользователь {user_id} забанен")

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()