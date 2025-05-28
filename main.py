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
menu.add(KeyboardButton("рџ’« РЎРїРёРЅ"), KeyboardButton("рџЋІ РљСѓР±РёРє"))
menu.add(KeyboardButton("рџ‘¤ РџСЂРѕС„РёР»СЊ"), KeyboardButton("рџЋЃ Р РµС„РµСЂР°Р»"))
menu.add(KeyboardButton("рџ“ў Р РµРєР»Р°РјР°"), KeyboardButton("рџЏ† РўРѕРї"))

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
    await msg.answer("Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ! Р’РѕС‚ РјРµРЅСЋ:", reply_markup=menu)

@dp.message_handler(lambda m: m.text == "рџ’« РЎРїРёРЅ")
async def spin_game(msg: types.Message):
    user_id = msg.from_user.id
    win = random.randint(1, 100) == 1
    stars = 100 if win else 0
    cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (stars, user_id))
    conn.commit()
    await msg.answer("рџЋ‰ Р’С‹ РІС‹РёРіСЂР°Р»Рё 100 в­ђ!" if win else "рџў РќРµ РїРѕРІРµР·Р»Рѕ!")

@dp.message_handler(lambda m: m.text.startswith(("Р§С‘С‚", "РќРµС‡РµС‚", "0", "1", "2", "3", "4", "5", "6")))
async def cube_game(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.answer("РџСЂРёРјРµСЂ: Р§С‘С‚ 100 РёР»Рё 4 100")
    user_id = msg.from_user.id
    bet_type, amount = parts[0], int(parts[1])
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < amount:
        return await msg.answer("РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ Р·РІС‘Р·Рґ.")
    roll = random.randint(1, 6)
    win = False
    if bet_type.lower() == "С‡С‘С‚" and roll % 2 == 0:
        win = True
    elif bet_type.lower() == "РЅРµС‡РµС‚" and roll % 2 != 0:
        win = True
    elif bet_type.isdigit() and int(bet_type) == roll:
        win = True
        amount *= 5
    cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount if win else -amount, user_id))
    conn.commit()
    await msg.answer(f"рџЋІ Р’С‹РїР°Р»Рѕ {roll}. " + ("Р’С‹ РІС‹РёРіСЂР°Р»Рё в­ђ!" if win else "Р’С‹ РїСЂРѕРёРіСЂР°Р»Рё."))

@dp.message_handler(lambda m: m.text == "рџ‘¤ РџСЂРѕС„РёР»СЊ")
async def profile(msg: types.Message):
    user_id = msg.from_user.id
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    stars = cursor.fetchone()[0]
    await msg.answer(f"Р’Р°С€ Р±Р°Р»Р°РЅСЃ: {stars} в­ђ")

@dp.message_handler(lambda m: m.text == "рџЋЃ Р РµС„РµСЂР°Р»")
async def referral(msg: types.Message):
    user_id = msg.from_user.id
    bot_username = (await bot.get_me()).username
    await msg.answer(
        f"РџСЂРёРіР»Р°С€Р°Р№ РґСЂСѓР·РµР№!
"
        f"РўРІРѕСЏ СЃСЃС‹Р»РєР°:
"
        f"https://t.me/{bot_username}?start={user_id}"
    )

@dp.message_handler(lambda m: m.text == "рџ“ў Р РµРєР»Р°РјР°")
async def ads(msg: types.Message):
    await msg.answer("Р РµРєР»Р°РјР° СЃС‚РѕРёС‚ 200 в­ђ. РќР°РїРёС€Рё Р°РґРјРёРЅСѓ РґР»СЏ СЂР°Р·РјРµС‰РµРЅРёСЏ.")

@dp.message_handler(lambda m: m.text == "рџЏ† РўРѕРї")
async def top(msg: types.Message):
    cursor.execute("SELECT user_id, stars FROM users ORDER BY stars DESC LIMIT 5")
    top_users = cursor.fetchall()
    text = "рџЏ† РўРѕРї РїРѕ Р·РІС‘Р·РґР°Рј:
"
    for i, (uid, stars) in enumerate(top_users, 1):
        text += f"{i}. {uid} вЂ” {stars} в­ђ
"
    await msg.answer(text)

if __name__ == "__main__":
    from aiogram import executor
    from database import conn
    executor.start_polling(dp, skip_updates=True)