import random
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = '7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc'  # <-- вставь сюда свой токен
ADMINS = [123456789]          # <-- сюда свой user_id

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 10000
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bet_text TEXT,
    amount INTEGER,
    result INTEGER,
    win INTEGER,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

# ========== ХЕЛПЕРЫ ==========
async def get_user_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

async def update_user_balance(user_id, balance):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id))
    conn.commit()

async def get_top_users(limit=10):
    cursor.execute("SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
    return cursor.fetchall()

# ========== РУЛЕТКА ==========
RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

def match_special(bet, result):
    if bet == 'red': return result in RED
    if bet == 'black': return result in BLACK
    if bet == 'odd': return result != 0 and result % 2 == 1
    if bet == 'even': return result != 0 and result % 2 == 0
    return False

async def process_bet(user_id, amount, bet_inputs):
    numbers, specials = [], []
    for part in bet_inputs:
        if part in ['red', 'black', 'odd', 'even']:
            specials.append(part)
        elif '-' in part:
            try:
                start, end = map(int, part.split('-'))
                numbers += list(range(start, end + 1))
            except:
                continue
        else:
            try:
                numbers.append(int(part))
            except:
                continue

    total_bets = len(numbers) + len(specials)
    if total_bets == 0:
        return False, "Некорректная ставка"

    total_amount = amount * total_bets
    balance = await get_user_balance(user_id)
    if total_amount > balance:
        return False, "Недостаточно снежинок"

    await update_user_balance(user_id, balance - total_amount)

    result = random.randint(0, 36)
    win = 0

    for num in numbers:
        if num == result:
            win += amount * 36

    for spec in specials:
        if match_special(spec, result):
            win += amount * 2

    if win > 0:
        new_bal = await get_user_balance(user_id)
        await update_user_balance(user_id, new_bal + win)

    cursor.execute("INSERT INTO bets (user_id, bet_text, amount, result, win) VALUES (?, ?, ?, ?, ?)",
                   (user_id, " ".join(bet_inputs), amount, result, win))
    conn.commit()

    return True, result, win

# ========== ХЭНДЛЕРЫ ==========
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    await message.reply("Добро пожаловать! Напиши 'Б' чтобы узнать баланс или сделай ставку: например `50 red 10-15`")

@dp.message_handler(lambda msg: msg.text.lower() == "б")
async def show_balance(message: types.Message):
    balance = await get_user_balance(message.from_user.id)
    await message.reply(f"Ваш баланс: {balance} снежинок")

@dp.message_handler(lambda msg: msg.text.lower() == "топ")
async def show_top(message: types.Message):
    top = await get_top_users()
    text = "Топ игроков:\n"
    for i, user in enumerate(top, 1):
        uid, uname, bal = user
        name = uname or f"id{uid}"
        text += f"{i}. {name} — {bal} снежинок\n"
    await message.reply(text)

@dp.message_handler(lambda msg: msg.text.lower() == "панель")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Просмотр ставок", callback_data="view_bets"),
        InlineKeyboardButton("Выдать снежинки", callback_data="give_snow")
    )
    await message.reply("Админ-панель:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "view_bets")
async def handle_view_bets(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    cursor.execute("SELECT * FROM bets ORDER BY time DESC LIMIT 5")
    bets = cursor.fetchall()
    text = "Последние ставки:\n\n"
    for bet in bets:
        _, uid, bet_text, amount, result, win, time = bet
        text += f"{time}: ID {uid} — {bet_text}, выпало {result}, выигрыш: {win}\n"
    await call.message.edit_text(text)

@dp.callback_query_handler(lambda c: c.data == "give_snow")
async def handle_give_snow(call: types.CallbackQuery):
    await call.message.edit_text("Напиши в формате:\nвыдать <user_id> <сумма>")

@dp.message_handler(lambda msg: msg.text.lower().startswith("выдать"))
async def give_snow(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Формат: выдать <user_id> <сумма>")
    user_id, amount = int(parts[1]), int(parts[2])
    balance = await get_user_balance(user_id)
    await update_user_balance(user_id, balance + amount)
    await message.reply(f"Выдано {amount} снежинок пользователю {user_id}")

@dp.message_handler()
async def handle_bet(message: types.Message):
    try:
        parts = message.text.lower().split()
        if len(parts) < 2:
            return
        amount = int(parts[0])
        bets = parts[1:]
        success, *result = await process_bet(message.from_user.id, amount, bets)
        if not success:
            await message.reply(result[0])
            return
        result_num, win = result
        text = f"Выпало число: {result_num}\n"
        text += f"Вы {'выиграли ' + str(win) if win > 0 else 'проиграли'} снежинок."
        await message.reply(text)
    except Exception:
        pass

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)