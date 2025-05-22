import os
import logging
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, executor, types

# Логирование
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменной среды
TOKEN = os.getenv("API_TOKEN")
if not TOKEN:
    logging.error("API_TOKEN environment variable not set!")
    exit(1)

# Инициализация бота
bot = Bot(TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"
ADMIN_ID = 6359584002

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("Ошибка загрузки БД. Создается новая.")
    return {"users": {}, "banned": [], "promo_codes": {}}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения БД: {e}")

db = load_db()

# Обновляем username каждый раз
@dp.message_handler()
async def update_user(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Без ника"
    if user_id in db.get("banned", []):
        return
    if user_id not in db["users"]:
        db["users"][user_id] = {"snowflakes": 1000, "username": username}
        await message.answer(f"Добро пожаловать, {username}! У вас 1000 снежинок. ❄️")
    else:
        db["users"][user_id]["username"] = username
    save_db(db)

# Рулетка
@dp.message_handler(lambda m: m.text.lower().startswith(("го", "рулетка")))
async def roulette(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return
    if user_id not in db["users"]:
        await message.answer("Сначала напишите 'старт'")
        return

    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.answer("Пример: го 17 или го 5-20 (минимум 50 снежинок)")
        return

    bet_input = parts[1]
    bet_parts = bet_input.split("-")

    try:
        if len(bet_parts) == 1:
            bet = int(bet_parts[0])
            if bet < 50:
                raise ValueError
            bet_type = "single"
        elif len(bet_parts) == 2:
            bet = int(bet_parts[0])
            start, end = int(bet_parts[0]), int(bet_parts[1])
            if bet < 50 or not (0 <= start <= end <= 36):
                raise ValueError
            bet_type = "range"
        else:
            raise ValueError
    except ValueError:
        await message.answer("Некорректная ставка или диапазон. Пример: го 17 или го 10-20")
        return

    if db["users"][user_id]["snowflakes"] < bet:
        await message.answer("Недостаточно снежинок ❄️")
        return

    await message.answer("Рулетка запускается через 5 секунд...")
    await asyncio.sleep(5)

    result = random.randint(0, 36)
    color = "🟣" if result == 0 else ("⚫" if result % 2 == 0 else "🔴")
    winnings = 0

    if bet_type == "single" and result == bet:
        winnings = bet * 36
    elif bet_type == "range" and start <= result <= end:
        winnings = bet * 2

    if winnings > 0:
        db["users"][user_id]["snowflakes"] += winnings
        msg = f"{color} Выпало: {result}\nВы выиграли {winnings} снежинок! ❄️"
    else:
        db["users"][user_id]["snowflakes"] -= bet
        msg = f"{color} Выпало: {result}\nВы проиграли {bet} снежинок."

    save_db(db)
    await message.answer(msg)

# Панель администратора
@dp.message_handler(lambda m: m.text.lower() in ["админ", "панель администратора"])
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Добро пожаловать, админ! ⚙️")
    else:
        await message.answer("У вас нет прав доступа.")

# Создание промокодов
@dp.message_handler(lambda m: m.text.lower().startswith("создать промокод"))
async def create_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("Нет прав.")
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.reply("Формат: создать промокод [снежинки] [кол-во]")
        return

    try:
        snowflakes = int(parts[2])
