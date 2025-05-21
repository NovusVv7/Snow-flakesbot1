import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"
ADMINS = [123456789]  # ЗАМЕНИ на свой Telegram user ID

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def get_user(user_id):
    db = load_db()
    return db.get(str(user_id), {"balance": 1000, "banned": False, "history": []})

def update_user(user_id, user_data):
    db = load_db()
    db[str(user_id)] = user_data
    save_db(db)

def change_balance(user_id, amount, action=""):
    user = get_user(user_id)
    user["balance"] += amount
    user["history"].append(f"{'+' if amount >= 0 else ''}{amount} ({action})")
    update_user(user_id, user)

def is_banned(user_id):
    return get_user(user_id).get("banned", False)

@dp.message_handler(lambda m: m.text.lower() == "б")
async def check_balance(message: Message):
    if is_banned(message.from_user.id):
        await message.reply("Вы забанены.")
        return
    bal = get_user(message.from_user.id)["balance"]
    await message.reply(f"У вас {bal} снежинок.")

# Админ-команды
@dp.message_handler(commands=["выдать", "отнять", "забанить", "история", "перевод"])
async def admin_commands(message: Message):
    if message.from_user.id not in ADMINS:
        return

    parts = message.text.split()
    if message.text.startswith("/выдать") and len(parts) == 3:
        uid, amount = int(parts[1]), int(parts[2])
        change_balance(uid, amount, "выдача")
        await message.reply("Выдано.")
    elif message.text.startswith("/отнять") and len(parts) == 3:
        uid, amount = int(parts[1]), int(parts[2])
        change_balance(uid, -amount, "отнятие")
        await message.reply("Отнято.")
    elif message.text.startswith("/забанить") and len(parts) == 2:
        uid = int(parts[1])
        user = get_user(uid)
        user["banned"] = True
        update_user(uid, user)
        await message.reply("Забанен.")
    elif message.text.startswith("/история") and len(parts) == 2:
        uid = int(parts[1])
        history = get_user(uid).get("history", [])
        await message.reply("\n".join(history[-10:]) or "История пуста.")
    elif message.text.startswith("/перевод") and len(parts) == 3:
        to_id, amount = int(parts[1]), int(parts[2])
        from_id = message.from_user.id
        if get_user(from_id)["balance"] < amount:
            await message.reply("Недостаточно снежинок.")
            return
        change_balance(from_id, -amount, "перевод")
        change_balance(to_id, amount, "получено")
        await message.reply("Перевод выполнен.")

# Рулетка
pending_bets = {}

@dp.message_handler()
async def all_text_handler(message: Message):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.reply("Вы забанены.")
        return

    text = message.text.lower().strip()
    parts = text.split()

    # Ставка на рулетку
    if len(parts) == 2 and parts[0].isdigit() and (parts[1].isdigit() or parts[1] in ["odd", "even"]):
        amount = int(parts[0])
        bet = parts[1]
        bal = get_user(user_id)["balance"]
        if amount > bal:
            await message.reply("Недостаточно снежинок.")
            return
        pending_bets[user_id] = {"amount": amount, "bet": bet}
        await message.reply(f"Ставка {amount} на {bet} принята. Запуск через 5 секунд...")
        await asyncio.sleep(5)
        await roulette_spin(user_id, message)
        return

    # Команды для мин
    if text.startswith("м "):
        await mines_click(message)
    elif text == "забрать":
        await mines_cashout(message)

# Рулетка обработка
async def roulette_spin(user_id, message):
    data = pending_bets.pop(user_id, None)
    if not data:
        return
    number = random.randint(0, 36)
    amount = data["amount"]
    bet = data["bet"]
    win = False
    if bet == "odd" and number % 2 == 1:
        win = True
        payout = amount * 2
    elif bet == "even" and number % 2 == 0 and number != 0:
        win = True
        payout = amount * 2
    elif bet.isdigit() and int(bet) == number:
        win = True
        payout = amount * 36
    else:
        payout = 0

    if win:
        change_balance(user_id, payout, "рулетка +")
        result = f"Выпало {number}. Победа! +{payout} снежинок."
    else:
        change_balance(user_id, -amount, "рулетка -")
        result = f"Выпало {number}. Проигрыш. -{amount} снежинок."
    await message.reply(result)

# Мины
active_mines = {}  # user_id: {"grid": [...], "revealed": set(), "amount": int}

def generate_mines_grid(size=5, mines=5):
    grid = [["⬜" for _ in range(size)] for _ in range(size)]
    positions = random.sample(range(size*size), mines)
    for pos in positions:
        x, y = divmod(pos, size)
        grid[x][y] = "💣"
    return grid

def render_grid(grid, revealed):
    text = ""
    for i, row in enumerate(grid):
        for j, cell in enumerate(row):
            text += cell if (i, j) in revealed or cell == "💣" else "▪️"
        text += "\n"
    return text

@dp.message_handler(commands=["мины"])
async def start_mines(message: Message):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.reply("Вы забанены.")
        return
    bal = get_user(user_id)["balance"]
    if bal < 100:
        await message.reply("Нужно минимум 100 снежинок.")
        return
    grid = generate_mines_grid()
    active_mines[user_id] = {"grid": grid, "revealed": set(), "amount": 100}
    change_balance(user_id, -100, "ставка в мины")
    await message.reply("Игра началась! Введите `м 1 2` чтобы открыть клетку.\n" + render_grid(grid, set()))

async def mines_click(message: Message):
    user_id = message.from_user.id
    if user_id not in active_mines:
        await message.reply("Игра не начата. Напишите /мины.")
        return
    try:
        _, x, y = message.text.split()
        x, y = int(x), int(y)
    except:
        await message.reply("Формат: м x y")
        return

    data = active_mines[user_id]
    grid = data["grid"]
    revealed = data["revealed"]
    if (x, y) in revealed:
        await message.reply("Клетка уже открыта.")
        return

    revealed.add((x, y))
    if grid[x][y] == "💣":
        await message.reply("Бум! Вы подорвались.\n" + render_grid(grid, revealed))
        del active_mines[user_id]
    else:
        await message.reply("Успешно!\n" + render_grid(grid, revealed))

async def mines_cashout(message: Message):
    user_id = message.from_user.id
    if user_id not in active_mines:
        await message.reply("У вас нет активной игры.")
        return
    data = active_mines.pop(user_id)
    safe_cells = len(data["revealed"])
    winnings = int(data["amount"] * (1 + safe_cells * 0.42))
    change_balance(user_id, winnings, "выигрыш мины")
    await message.reply(f"Вы забрали {winnings} снежинок за {safe_cells} безопасных клеток.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
