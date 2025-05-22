import logging
import json
import os
import random
from aiogram import Bot, Dispatcher, executor, types

TOKEN = os.getenv("API_TOKEN") or "your_token_here"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "banned": [], "history": {}}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

db = load_db()

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return
    if user_id not in db["users"]:
        db["users"][user_id] = {"snowflakes": 1000}
        save_db(db)
    await message.answer(f"Добро пожаловать, у вас {db['users'][user_id]['snowflakes']} снежинок.")

@dp.message_handler(lambda m: m.text.lower().startswith("го"))
async def roulette(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return
    text = message.text.lower().split()
    if len(text) != 3:
        await message.reply("Пример: го odd 100")
        return
    choice, bet = text[1], int(text[2])
    if db["users"][user_id]["snowflakes"] < bet:
        await message.reply("Недостаточно снежинок.")
        return
    result = random.randint(0, 36)
    win = False
    if choice == "odd" and result % 2 == 1:
        win = True
    elif choice == "even" and result % 2 == 0:
        win = True
    elif choice.isdigit() and int(choice) == result:
        win = True
    if win:
        coef = 36 if choice.isdigit() else 2
        winnings = bet * coef
        db["users"][user_id]["snowflakes"] += winnings
        await message.reply(f"Выпало {result}. Победа! +{winnings} снежинок.")
    else:
        db["users"][user_id]["snowflakes"] -= bet
        await message.reply(f"Выпало {result}. Проигрыш. -{bet} снежинок.")
    save_db(db)

@dp.message_handler(lambda m: m.text.lower().startswith("п "))
async def pay(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()
    if len(parts) != 3 or not parts[2].isdigit():
        await message.reply("Используй: П [ID] [сумма]")
        return
    target, amount = parts[1], int(parts[2])
    if user_id not in db["users"] or db["users"][user_id]["snowflakes"] < amount:
        await message.reply("Недостаточно снежинок.")
        return
    db["users"][user_id]["snowflakes"] -= amount
    if target not in db["users"]:
        db["users"][target] = {"snowflakes": 1000}
    db["users"][target]["snowflakes"] += amount
    await message.reply(f"Вы передали {amount} снежинок пользователю {target}.")
    save_db(db)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)