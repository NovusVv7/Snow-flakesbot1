import asyncio
import random
import time
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart

TOKEN = "ТВОЙ_ТОКЕН"
ADMINS = [123456789]  # замени на свой Telegram ID

dp = Dispatcher()
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)

SPAM_DELAY = 5
last_bet = {}

# Цвета рулетки
RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                balance INTEGER,
                banned INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(uid):
    async with aiosqlite.connect("users.db") as db:
        cur = await db.execute("SELECT balance, banned FROM users WHERE id = ?", (uid,))
        row = await cur.fetchone()
        if row:
            return {"balance": row[0], "banned": row[1]}
        else:
            bonus = random.randint(5000, 100000)
            await db.execute("INSERT INTO users (id, balance) VALUES (?, ?)", (uid, bonus))
            await db.commit()
            return {"balance": bonus, "banned": 0}

async def update_balance(uid, amount):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = ? WHERE id = ?", (amount, uid))
        await db.commit()

async def add_balance(uid, amount):
    user = await get_user(uid)
    await update_balance(uid, user['balance'] + amount)

async def sub_balance(uid, amount):
    user = await get_user(uid)
    await update_balance(uid, max(0, user['balance'] - amount))

async def is_banned(uid):
    user = await get_user(uid)
    return user['banned'] == 1

@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    user = await get_user(uid)
    if await is_banned(uid):
        return
    await message.answer(f"Добро пожаловать, {message.from_user.full_name}!\nВаши снежинки: {user['balance']}")

@dp.message(F.text.lower().in_({"профиль", "баланс"}))
async def show_profile(message: Message):
    uid = message.from_user.id
    if await is_banned(uid):
        return
    user = await get_user(uid)
    await message.answer(f"Ваш баланс: {user['balance']} снежинок")

@dp.message(F.text.lower().startswith("топ"))
async def top_players(message: Message):
    async with aiosqlite.connect("users.db") as db:
        cur = await db.execute("SELECT id, balance FROM users ORDER BY balance DESC LIMIT 10")
        rows = await cur.fetchall()
        text = "<b>Топ игроков:</b>\n"
        for i, row in enumerate(rows, 1):
            text += f"{i}. <code>{row[0]}</code> — {row[1]} снежинок\n"
        await message.answer(text)

@dp.message(F.text.lower() == "админ" and F.from_user.id.in_(ADMINS))
async def admin_panel(message: Message):
    buttons = [
        [InlineKeyboardButton(text="Выдать", callback_data="admin_give"),
         InlineKeyboardButton(text="Забрать", callback_data="admin_take")],
        [InlineKeyboardButton(text="Забанить", callback_data="admin_ban")]
    ]
    await message.answer("Админ-панель:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("admin_"))
async def admin_action(call: types.CallbackQuery):
    await call.message.answer(f"Введи команду:\nПример: <code>{call.data[6:]} 123456789 1000</code>")
    await call.answer()

@dp.message(lambda msg: msg.from_user.id in ADMINS and any(msg.text.startswith(cmd) for cmd in ["выдать", "забрать", "забанить"]))
async def admin_commands(message: Message):
    parts = message.text.split()
    if len(parts) < 3 and not message.text.startswith("забанить"):
        return await message.answer("Неверный формат.")
    cmd = parts[0].lower()
    uid = int(parts[1])

    if cmd == "выдать":
        amount = int(parts[2])
        await add_balance(uid, amount)
        await message.answer(f"Выдано {amount} снежинок пользователю {uid}")
    elif cmd == "забрать":
        amount = int(parts[2])
        await sub_balance(uid, amount)
        await message.answer(f"Забрано {amount} снежинок у пользователя {uid}")
    elif cmd == "забанить":
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET banned = 1 WHERE id = ?", (uid,))
            await db.commit()
        await message.answer(f"Пользователь {uid} забанен.")

@dp.message()
async def roulette(message: Message):
    uid = message.from_user.id
    if await is_banned(uid):
        return

    # Антиспам
    now = time.time()
    if uid in last_bet and now - last_bet[uid] < SPAM_DELAY:
        return await message.answer("Подожди пару секунд перед следующей ставкой.")
    last_bet[uid] = now

    text = message.text.lower().replace("ч", "чет").replace("н", "нечет")
    try:
        parts = text.split()
        if len(parts) < 2:
            return

        bet = int(parts[0])
        target = parts[1]

        user = await get_user(uid)
        if user['balance'] < bet:
            return await message.answer("Недостаточно снежинок.")

        win_number = random.randint(0, 36)
        result = f"Выпало: <b>{win_number}</b>\n"

        win = False
        win_amount = 0

        if "-" in target:
            start, end = map(int, target.split("-"))
            numbers = set(range(start, end + 1))
            if win_number in numbers:
                win = True
                win_amount = bet * (36 // len(numbers))
        elif target in {"чет", "нечет"}:
            if win_number == 0:
                win = False
            elif target == "чет" and win_number % 2 == 0:
                win = True
                win_amount = bet * 2
            elif target == "нечет" and win_number % 2 == 1:
                win = True
                win_amount = bet * 2
        elif target in {"красное", "черное"}:
            if target == "красное" and win_number in RED_NUMBERS:
                win = True
                win_amount = bet * 2
            elif target == "черное" and win_number in BLACK_NUMBERS:
                win = True
                win_amount = bet * 2
        else:
            numbers = set(map(int, target.split(",")))
            if win_number in numbers:
                win = True
                win_amount = bet * (36 // len(numbers))

        await sub_balance(uid, bet)
        if win:
            await add_balance(uid, win_amount)
            result += f"Вы выиграли <b>{win_amount}</b> снежинок!"
        else:
            result += f"Вы проиграли {bet} снежинок."
        await message.answer(result)
    except:
        await message.answer("Формат: <code>100 10-20</code> или <code>200 красное</code>")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())