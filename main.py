import os
import logging
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from datetime import datetime, timedelta

# Конфигурируем логирование
logging.basicConfig(level=logging.INFO)

# Получаем API токен из переменной окружения
TOKEN = os.getenv("API_TOKEN")
if not TOKEN:
    logging.error("API_TOKEN environment variable not set!")
    exit(1)  # Выход, если токен отсутствует

# Инициализация бота с токеном
bot = Bot(TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"
ADMIN_ID = 6359584002  # Ваш ID

# Словарь для хранения ставок
roulette_bets = {}  # user_id: {"amount": int, "numbers": list, "time": datetime}

# Лог-файл для записей рулетки
LOG_FILE = "roulette_log.txt"

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except FileNotFoundError:
        logging.warning("Database file not found. Creating a new one.")
        return {"users": {}, "banned": [], "history": {}}
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from database file. Using default database.")
        return {"users": {}, "banned": [], "history": {}}
    return {"users": {}, "banned": [], "history": {}}

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

@dp.message_handler(commands=["start"])
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

@dp.message_handler(commands=["balance"])
async def balance(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return
    if user_id not in db["users"]:
        await message.answer("Сначала используйте команду /start")
        return
    await message.answer(f"Ваш баланс: {db['users'][user_id]['snowflakes']} снежинок.")

@dp.message_handler(lambda m: m.text and m.text.split()[0].isdigit() and not m.text.lower().startswith("го"))
async def place_roulette_bet(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in db["users"]:
        await message.answer("Сначала используйте команду /start")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Формат: [ставка] [числа от 0 до 36]")
        return

    if not parts[0].isdigit():
        return

    amount = int(parts[0])
    numbers = parts[1:]

    if len(numbers) > 19:
        await message.reply("Максимум 19 чисел.")
        return

    try:
        numbers = [int(n) for n in numbers]
    except ValueError:
        await message.reply("Все числа должны быть от 0 до 36.")
        return

    if any(n < 0 or n > 36 for n in numbers):
        await message.reply("Числа должны быть от 0 до 36.")
        return

    if amount < 50:
        await message.reply("Минимальная ставка 50 снежинок.")
        return

    if db["users"][user_id]["snowflakes"] < amount:
        await message.reply("Недостаточно снежинок.")
        return

    roulette_bets[user_id] = {"amount": amount, "numbers": numbers, "time": datetime.now()}
    await message.reply(f"Ставка принята: {amount} снежинок на {len(numbers)} чисел.\nНапиши 'го' чтобы крутить рулетку.")

@dp.message_handler(lambda m: m.text.lower().strip() == "го")
async def launch_roulette(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in roulette_bets:
        await message.reply("Сначала сделайте ставку, указав сумму и числа.")
        return

    bet = roulette_bets.pop(user_id)
    amount = bet["amount"]
    numbers = bet["numbers"]

    if db["users"][user_id]["snowflakes"] < amount:
        await message.reply("Недостаточно снежинок для запуска ставки.")
        return

    bet_per_number = amount // len(numbers)
    if bet_per_number == 0:
        await message.reply("Ставка слишком мала для такого количества чисел.")
        return

    await message.reply("Рулетка запускается через 7 секунд...")
    await asyncio.sleep(7)

    result = random.randint(0, 36)
    outcome = ""
    result_type = ""

    # Классификация числа
    if result == 0:
        result_type = "фиолетовый"
        outcome = f"Выпало {result} (фиолетовый 0). Вы проиграли {amount} снежинок."
    elif result % 2 == 0:
        result_type = "черный"
        outcome = f"Выпало {result} (черный). Вы проиграли {amount} снежинок."
    else:
        result_type = "красный"
        outcome = f"Выпало {result} (красный). Вы проиграли {amount} снежинок."

    # Проверка на выигрыш
    if result in numbers:
        winnings = bet_per_number * 36
        db["users"][user_id]["snowflakes"] += winnings
        outcome = f"Выпало {result} ({result_type}). Победа! +{winnings} снежинок."

    # Логирование результата
    log_message = f"{datetime.now()} - Выпало число {result} ({result_type}).\n"
    with open(LOG_FILE, "a") as log_file:
        log_file.write(log_message)

    db["users"][user_id]["snowflakes"] -= amount
    save_db(db)
    await message.answer(outcome)

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await message.reply("Добро пожаловать, админ!")
    else:
        await message.reply("У вас нет прав доступа.")

@dp.message_handler(commands=["ban"])
async def admin_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.reply_to_message:
        user_id = str(message.reply_to_message.from_user.id)
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("Используй: /ban [username/id]")
            return

        target = parts[1]
        if target.isdigit():
            user_id = target
        else:
            user_id = get_user_id_from_username(target)
            if not user_id:
                await message.reply("Пользователь не найден.")
                return

    db["banned"].append(user_id)
    save_db(db)
    await message.reply(f"Пользователь {user_id} забанен.")

@dp.message_handler(commands=["give"])
async def admin_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Используй: /give [username/id] [количество]")
        return

    target = parts[1]
    amount_str = parts[2]

    if not amount_str.isdigit():
        await message.reply("Количество должно быть числом.")
        return

    amount = int(amount_str)

    if target.isdigit():
        user_id = target
    else:
        user_id = get_user_id_from_username(target)
        if not user_id:
            await message.reply("Пользователь не найден.")
            return

    if user_id not in db["users"]:
        db["users"][user_id] = {"snowflakes": 0, "username": None}

    db["users"][user_id]["snowflakes"] += amount
    save_db(db)
    await message.reply(f"Выдано {amount} снежинок пользователю {target}.")

@dp.message_handler(commands=["top"])
async def top_balance(message: types.Message):
    users = db["users"]
    sorted_users = sorted(users.items(), key=lambda item: item[1]["snowflakes"], reverse=True)

    top_users = sorted_users[:10]  # Топ 10

    response = "Топ 10 богатейших игроков:\n"
    for i, (user_id, data) in enumerate(top_users):
        username = data.get("username", "Неизвестный")  # Получаем юзернейм
        response += f"{i+1}. {username} ({user_id}): {data['snowflakes']} снежинок\n"

    await message.reply(response)

async def check_bet_expiry():
    while True:
        now = datetime.now()
        for user_id, bet in list(roulette_bets.items()):
            if now - bet["time"] > timedelta(minutes=5):
                del roulette_bets[user_id]
                logging.info(f"Ставка пользователя {user_id} удалена из-за истечения времени.")
        await asyncio.sleep(60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(check_bet_expiry())  # Запуск проверки на истечение времени
    executor.start_polling(dp, skip_updates=True)
