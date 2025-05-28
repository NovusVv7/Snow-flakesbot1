from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import random
import sqlite3
from config import TOKEN, ADMIN_IDS

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("stars_bot.db")
cursor = conn.cursor()

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("💫 Спин"), KeyboardButton("🎲 Кубик"))
menu.add(KeyboardButton("👤 Профиль"), KeyboardButton("🎁 Реферал"))
menu.add(KeyboardButton("📢 Реклама"), KeyboardButton("🏆 Топ"))

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    ref = msg.get_args()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, stars, referrer_id) VALUES (?, ?, ?)",
                       (user_id, 0, int(ref) if ref.isdigit() else None))
        if ref.isdigit():
            cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (int(ref), user_id))
            cursor.execute("UPDATE users SET stars = stars + 10 WHERE user_id = ?", (int(ref),))
        conn.commit()
    await msg.answer("Добро пожаловать! Вот меню:", reply_markup=menu)

@dp.message_handler(lambda m: m.text == "💫 Спин")
async def spin_game(msg: types.Message):
    user_id = msg.from_user.id
    win = random.randint(1, 100) == 1
    stars = 100 if win else 0
    cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (stars, user_id))
    conn.commit()
    await msg.answer("🎉 Вы выиграли 100 ⭐!" if win else "😢 Не повезло!")

@dp.message_handler(lambda m: m.text.startswith(("Чёт", "Нечет", "0", "1", "2", "3", "4", "5", "6")))
async def cube_game(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.answer("Пример: Чёт 100 или 4 100")
    user_id = msg.from_user.id
    bet_type, amount = parts[0], int(parts[1])
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < amount:
        return await msg.answer("Недостаточно звёзд.")
    roll = random.randint(1, 6)
    win = False
    if bet_type.lower() == "чёт" and roll % 2 == 0:
        win = True
    elif bet_type.lower() == "нечет" and roll % 2 != 0:
        win = True
    elif bet_type.isdigit() and int(bet_type) == roll:
        win = True
        amount *= 5
    cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount if win else -amount, user_id))
    conn.commit()
    await msg.answer(f"🎲 Выпало {roll}. " + ("Вы выиграли ⭐!" if win else "Вы проиграли."))

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    user_id = msg.from_user.id
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    stars = cursor.fetchone()[0]
    await msg.answer(f"Ваш баланс: {stars} ⭐")

@dp.message_handler(lambda m: m.text == "🎁 Реферал")
async def referral(msg: types.Message):
    user_id = msg.from_user.id
    bot_username = (await bot.get_me()).username
    await msg.answer(f"Приглашай друзей!
Твоя ссылка:
https://t.me/{bot_username}?start={user_id}")

@dp.message_handler(lambda m: m.text == "📢 Реклама")
async def ads(msg: types.Message):
    await msg.answer("Реклама стоит 200 ⭐. Напиши админу для размещения.")

@dp.message_handler(lambda m: m.text == "🏆 Топ")
async def top(msg: types.Message):
    cursor.execute("SELECT user_id, stars FROM users ORDER BY stars DESC LIMIT 5")
    top_users = cursor.fetchall()
    text = "🏆 Топ по звёздам:
"
    for i, (uid, stars) in enumerate(top_users, 1):
        text += f"{i}. {uid} — {stars} ⭐
"
    await msg.answer(text)

if __name__ == "__main__":
    from aiogram import executor
    from database import conn
    executor.start_polling(dp, skip_updates=True)