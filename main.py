import random from aiogram import Bot, Dispatcher, executor, types from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton import asyncio import sqlite3

API_TOKEN = 'YOUR_BOT_TOKEN' ADMINS = [123456789]  # Замените на свой user_id

bot = Bot(token=API_TOKEN) dp = Dispatcher(bot)

========== БАЗА ДАННЫХ ==========

conn = sqlite3.connect('bot.db') cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 10000 )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS bets ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bet_text TEXT, amount INTEGER, result INTEGER, win INTEGER, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP )''')

conn.commit()

========== ХЕЛПЕРЫ ==========

async def get_user_balance(user_id): cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) row = cursor.fetchone() return row[0] if row else 0

async def update_user_balance(user_id, balance): cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)) cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id)) conn.commit()

async def get_top_users(limit=10): cursor.execute("SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,)) return cursor.fetchall()

========== РУЛЕТКА ==========

RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36} BLACK_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

def match_special_bet(bet, result): if bet == 'red': return result in RED_NUMBERS if bet == 'black': return result in BLACK_NUMBERS if bet == 'odd': return result != 0 and result % 2 == 1 if bet == 'even': return result != 0 and result % 2 == 0 return False

async def process_bet(user_id, amount, bet_inputs): numbers, special_bets = [], [] for part in bet_inputs: if part in ['red', 'black', 'odd', 'even']: special_bets.append(part) elif '-' in part: try: start, end = map(int, part.split('-')) numbers += list(range(start, end + 1)) except: continue else: try: numbers.append(int(part)) except: continue

total_bets = len(numbers) + len(special_bets)
if total_bets == 0:
    return False, "Ставка некорректна"

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

for spec in special_bets:
    if match_special_bet(spec, result):
        win += amount * 2

if win > 0:
    new_balance = await get_user_balance(user_id)
    await update_user_balance(user_id, new_balance + win)

cursor.execute("INSERT INTO bets (user_id, bet_text

@dp.callback_query_handler(lambda c: c.data == "give_snow")
async def handle_give_snow(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Напиши в формате:\n`выдать <user_id> <сумма>`")

@dp.message_handler(lambda msg: msg.text.lower().startswith("выдать"))
async def give_snow(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Формат: выдать <user_id> <сумма>")

    user_id, amount = int(parts[1]), int(parts[2])
    balance = await get_user_balance(user_id)
    await update_user_balance(user_id, balance + amount)
    await message.reply(f"Выдано {amount} снежинок пользователю {user_id}")
ADMINS = [123456789]  # user_id админа

def is_admin(user_id):
    return user_id in ADMINS
