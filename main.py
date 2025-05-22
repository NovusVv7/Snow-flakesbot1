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
    exit(1) # Exit if the token is missing

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

@dp.message_handler(lambda m: m.text.lower().startswith("п "))
async def pay(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) != 3:
        await message.reply("Используй: П [сумма] [username/id]")
        return

    amount_str, target = parts[1], parts[2]

    if not amount_str.isdigit():
        await message.reply("Сумма должна быть числом.")
        return

    amount = int(amount_str)

    if user_id not in db["users"]:
        await message.reply("Сначала используйте команду /start")
        return

    if db["users"][user_id]["snowflakes"] < amount:
        await message.reply("Недостаточно снежинок.")
        return

    # Определяем ID цели:
    if target.isdigit():
        target_id = target  # Это ID
    else:
        target_id = get_user_id_from_username(target)  # Это username

        if target_id is None:
            await message.reply("Пользователь не найден.")
            return

    if target_id not in db["users"]:
        db["users"][target_id] = {"snowflakes": 1000, "username": None}  # Инициализируем пользователя
    db["users"][user_id]["snowflakes"] -= amount
    db["users"][target_id]["snowflakes"] += amount
    await message.reply(f"Вы передали {amount} снежинок пользователю {target}.")
    save_db(db)

@dp.message_handler(lambda m: m.text.lower().startswith("го"))
async def roulette(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return

    if user_id not in db["users"]:
        await message.answer("Сначала используйте команду /start")
        return

    text = message.text.lower().split()
    if len(text) != 2 or not text[1].isdigit():
        await message.reply("Пример: го [ставка] (ставка - число от 1)")
        return

    bet = int(text[1])
    if db["users"][user_id]["snowflakes"] < bet:
        await message.reply("Недостаточно снежинок.")
        return

    await message.reply("Рулетка запускается через 7 секунд...")
    await asyncio.sleep(7)

    result = random.randint(0, 36)
    if result == 0:
        winnings = bet * 36
    else:
        winnings = 0 # Нет выигрыша

    if winnings > 0:
        db["users"][user_id]["snowflakes"] += winnings
        await message.reply(f"Выпало {result}! Победа! +{winnings} снежинок.")
    else:
        db["users"][user_id]["snowflakes"] -= bet
        await message.reply(f"Выпало {result}. Проигрыш. -{bet} снежинок.")

    save_db(db)

mines_games = {} # Словарь для хранения игр с минами

@dp.message_handler(lambda m: m.text.lower().startswith("мины"))
async def start_mines(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in db["banned"]:
        await message.answer("Вы забанены.")
        return

    if user_id not in db["users"]:
        await message.answer("Сначала используйте команду /start")
        return

    text = message.text.lower().split()

    if len(text) != 2 or not text[1].isdigit():
        await message.reply("Пример: мины [ставка]")
        return

    bet = int(text[1])

    if db["users"][user_id]["snowflakes"] < bet:
        await message.reply("Недостаточно снежинок.")
        return

    mines_games[user_id] = {
        "bet": bet,
        "coef": 1.0, # Начальный коэффициент
        "clicks": 0, # Кол-во кликов
        "board": create_mines_board()
    }
    db["users"][user_id]["snowflakes"] -= bet
    save_db(db)
    await send_mines_board(message.chat.id, user_id)


def create_mines_board():
    board = []
    mines_positions = random.sample(range(25), 5) # 5 мин на поле 5x5
    for i in range(25):
        if i in mines_positions:
            board.append("💣")
        else:
            board.append("⬜️")
    return board

async def send_mines_board(chat_id, user_id):
    game = mines_games[user_id]
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    for i in range(25):
        callback_data = f"mines_click_{user_id}_{i}"
        keyboard.add(types.InlineKeyboardButton(game["board"][i], callback_data=callback_data))
    keyboard.add(types.InlineKeyboardButton(f"Забрать x{game['coef']:.2f}", callback_data=f"mines_take_{user_id}"))
    await bot.send_message(chat_id, f"Ставка: {game['bet']} снежинок\nКоэффициент: x{game['coef']:.2f}", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('mines_click_'))
async def process_mines_click(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split("_")
    index = int(data[3]) # Индекс клетки

    game = mines_games[str(user_id)]

    if game["board"][index] == "💣": # Взорвались
        del mines_games[str(user_id)]
        await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=f"Взрыв! Вы проиграли {game['bet']} снежинок.")
    else: # Успешный клик
      game["board"][index] = "✅" # Помечаем клетку
      game["clicks"] += 1
      game["coef"] = calculate_mines_coef(game["clicks"])
      await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text="Успешный клик!")
      await send_mines_board(callback_query.message.chat.id, str(user_id))

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('mines_take_'))
async def process_mines_take(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    game = mines_games[str(user_id)]
    winnings = int(game["bet"] * game["coef"])
    db["users"][str(user_id)]["snowflakes"] += winnings
    save_db(db)
    del mines_games[str(user_id)] # Удаляем игру
    await bot.send_message(callback_query.message.chat.id, f"Вы забрали {winnings} снежинок!")

def calculate_mines_coef(clicks):
    # Упрощенная формула увеличения коэффициента (нужно настроить)
    coefficient = 1.0
    for i in range(clicks):
        coefficient += (85 - coefficient) * 0.05 # Коэффициент увеличивается, стремясь к 86
    return coefficient

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
  user_id = message.from_user.id

  if user_id == ADMIN_ID:
      await message.reply("Добро пожаловать, админ!")
  else:
      await message.reply("У вас нет прав доступа.")

# === Команды администратора ===

@dp.message_handler(commands=["take"])
async def admin_take(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.reply_to_message: # Забираем у отвеченного пользователя
        user_id = str(message.reply_to_message.from_user.id)
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("Используй: /take [username/id]")
            return

        target = parts[1]
        if target.isdigit():
            user_id = target
        else:
            user_id = get_user_id_from_username(target)
            if not user_id:
                await message.reply("Пользователь не найден.")
                return

    if user_id not in db["users"]:
        await message.reply("Пользователь не найден в базе данных.")
        return

    amount = db["users"][user_id]["snowflakes"]
    db["users"][user_id]["snowflakes"] = 0  # Забираем всё
    save_db(db)
    await message.reply(f"Забрано {amount} снежинок у пользователя {user_id}.")

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

    top_users = sorted_users[:10] # Топ 10

    response = "Топ 10 богатейших игроков:\n"
    for i, (user_id, data) in enumerate(top_users):
        username = data.get("username", "Неизвестный") # Получаем юзернейм
        response += f"{i+1}. {username} ({user_id}): {data['snowflakes']} снежинок\n"

    await message.reply(response)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
