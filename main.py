import os
import logging
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import ChatNotFound

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get the API token from the environment variable
TOKEN = os.getenv("API_TOKEN")
if not TOKEN:
    logging.error("API_TOKEN environment variable not set!")
    exit(1)  # Exit if the token is missing

# Initialize the bot with the token from the environment
bot = Bot(TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"
ADMIN_ID = 6359584002  # Ваш ID

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except FileNotFoundError:
        logging.warning("Database file not found. Creating a new one.")
        return {"users": {}, "banned": [], "history": {}, "promo_codes": {}}
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from database file. Using default database.")
        return {"users": {}, "banned": [], "history": {}, "promo_codes": {}}
    return {"users": {}, "banned": [], "history": {}, "promo_codes": {}}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving database: {e}")

db = load_db()

def get_user_id_from_username(username):
    for user_id, data in db["users"].items():
        if "username" in data and data["username"] == username:
            return user_id
    return None

# Обработка команды /start
@dp.message_handler(lambda message: message.text.lower() == "старт")
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username

    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return

    if user_id not in db["users"]:
        db["users"][user_id] = {"snowflakes": 1000, "username": username}
        save_db(db)
    else:
        db["users"][user_id]["username"] = username
        save_db(db)
    await message.answer(f"Добро пожаловать, у вас {db['users'][user_id]['snowflakes']} снежинок.")

# Обработка команды рулетка или го
@dp.message_handler(lambda message: message.text.lower().startswith("го") or message.text.lower().startswith("рулетка"))
async def roulette(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return

    if user_id not in db["users"]:
        await message.answer("Сначала используйте команду старт")
        return

    text = message.text.lower().split()
    if len(text) < 2:
        await message.reply("Пример: го [ставка] или го [диапазон от-до] (ставка - число от 50 и выше, например: го 50-10 или го 100)")
        return

    bet_str = text[1]
    bet_parts = bet_str.split("-")
    
    if len(bet_parts) == 1 and bet_parts[0].isdigit():
        bet = int(bet_parts[0])
        if bet < 50:
            await message.reply("Минимальная ставка 50 снежинок.")
            return
    elif len(bet_parts) == 2 and all(part.isdigit() for part in bet_parts):
        bet = int(bet_parts[0])
        if bet < 50:
            await message.reply("Минимальная ставка 50 снежинок.")
            return
        start_range = int(bet_parts[0])
        end_range = int(bet_parts[1])
        if start_range > end_range or start_range < 0 or end_range > 36:
            await message.reply("Некорректный диапазон, он должен быть от 0 до 36.")
            return
    else:
        await message.reply("Некорректная ставка или диапазон.")
        return

    if db["users"][user_id]["snowflakes"] < bet:
        await message.reply("Недостаточно снежинок.")
        return

    await message.reply("Рулетка запускается через 7 секунд...")
    await asyncio.sleep(7)

    result = random.randint(0, 36)
    winnings = 0
    if len(bet_parts) == 1:
        if result == bet:
            winnings = bet * 36  # Ставка на конкретное число (36x)
    else:
        # Ставки на диапазоны
        if start_range <= result <= end_range:
            winnings = bet * 2  # Ставка на диапазон дает 2x выигрыш

    # Логирование результата
    logging.info(f"Рулетка: Вышло число {result}. Ставка: {bet}, Выигрыш: {winnings}.")

    if winnings > 0:
        db["users"][user_id]["snowflakes"] += winnings
        await message.reply(f"Выпало {result}! Победа! +{winnings} снежинок.")
    else:
        db["users"][user_id]["snowflakes"] -= bet
        await message.reply(f"Выпало {result}. Проигрыш. -{bet} снежинок.")

    save_db(db)

# === Команды администратора ===

@dp.message_handler(lambda message: message.text.lower() == "админ" or message.text.lower() == "панель администратора")
async def admin_panel(message: types.Message):
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await message.reply("Добро пожаловать, админ!")
    else:
        await message.reply("У вас нет прав доступа.")

@dp.message_handler(lambda message: message.text.lower().startswith("создать промокод"))
async def create_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("У вас нет прав для создания промокодов.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Используйте команду так: создать промокод [количество снежинок] [количество промокодов]")
        return

    try:
        snowflakes = int(parts[2])
        promo_count = int(parts[3])
    except ValueError:
        await message.reply("Введите корректные значения для снежинок и количества промокодов.")
        return

    promo_codes = []
    for _ in range(promo_count):
        promo_code = str(random.randint(100000, 999999))
        db["promo_codes"][promo_code] = snowflakes
        promo_codes.append(promo_code)

    save_db(db)
    await message.reply(f"Созданы следующие промокоды: {', '.join(promo_codes)}.\nКаждый дает {snowflakes} снежинок.")

@dp.message_handler(lambda message: message.text.lower().startswith("промокод"))
async def use_promo(message: types.Message):
    promo_code = message.text.split()[1].strip()
    if promo_code in db["promo_codes"]:
        snowflakes = db["promo_codes"][promo_code]
        user_id = str(message.from_user.id)
        if user_id not in db["users"]:
            db["users"][user_id] = {"snowflakes": 0, "username": message.from_user.username}
        db["users"][user_id]["snowflakes"] += snowflakes
        del db["promo_codes"][promo_code]  # Удаляем использованный промокод
        save_db(db)
        await message.reply(f"Вы использовали промокод! Вам начислено {snowflakes} снежинок.")
    else:
        await message.reply("Неверный или уже использованный промокод.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
