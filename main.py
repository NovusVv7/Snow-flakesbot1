import json, random, os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

OWNER_ID = 123456789  # <-- замени на свой user_id
TOKEN = os.getenv("API_TOKEN") or "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def load_db():
    return json.load(open("db.json")) if os.path.exists("db.json") else {"banned": [], "history": {}}

def save_db(db):
    json.dump(db, open("db.json", "w"))

def get_balance(uid):
    db = load_db()
    if str(uid) not in db:
        db[str(uid)] = 1000
        save_db(db)
    return db[str(uid)]

def update_balance(uid, val):
    db = load_db()
    db[str(uid)] = db.get(str(uid), 1000) + val
    save_db(db)

def add_history(uid, entry):
    db = load_db()
    uid = str(uid)
    if uid not in db["history"]:
        db["history"][uid] = []
    db["history"][uid].append(entry)
    save_db(db)

@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    if str(m.from_user.id) in load_db().get("banned", []):
        return
    get_balance(m.from_user.id)
    await m.answer("Добро пожаловать! У тебя снежинки — валюта. Напиши 'Го red 100', 'мины 100' или 'П @юзер 100'.")

@dp.message_handler(commands=["снег"])
async def snow(m: types.Message):
    if str(m.from_user.id) in load_db().get("banned", []):
        return
    await m.answer(f"У тебя {get_balance(m.from_user.id)} снежинок.")

@dp.message_handler(lambda m: m.text.lower().startswith("го"))
async def roulette(m: types.Message):
    if str(m.from_user.id) in load_db().get("banned", []):
        return
    args = m.text.lower().split()
    if len(args) != 3:
        return await m.answer("Пример: Го red 100")
    choice, bet = args[1], int(args[2])
    if bet > get_balance(m.from_user.id):
        return await m.answer("Недостаточно снежинок.")
    num = random.randint(0, 36)
    color = "green" if num == 0 else "black" if num % 2 == 0 else "red"
    parity = "even" if num % 2 == 0 else "odd"
    win = choice == color or choice == parity
    update_balance(m.from_user.id, bet if win else -bet)
    await m.answer(f"Выпало {num} ({color}), {'четное' if parity=='even' else 'нечетное'} — {'Победа!' if win else 'Проигрыш!'}")

@dp.message_handler(lambda m: m.text.lower().startswith("мины"))
async def mines(m: types.Message):
    if str(m.from_user.id) in load_db().get("banned", []):
        return
    args = m.text.lower().split()
    if len(args) != 2:
        return await m.answer("Пример: мины 100")
    bet = int(args[1])
    if bet > get_balance(m.from_user.id):
        return await m.answer("Недостаточно снежинок.")
    win = random.randint(1, 10) == 1
    if win:
        prize = int(bet * 1042)
        update_balance(m.from_user.id, prize)
        return await m.answer(f"БУМ! Ты победил и получил {prize} снежинок!")
    else:
        update_balance(m.from_user.id, -bet)
        return await m.answer("Мина взорвалась! Снежинки потеряны.")

@dp.message_handler(lambda m: m.text.lower().startswith("п "))
async def pay(m: types.Message):
    if str(m.from_user.id) in load_db().get("banned", []):
        return
    args = m.text.split()
    if len(args) != 3 or not m.entities or m.entities[1].type != "mention":
        return await m.answer("Пример: П @юзер 100")
    target_name = args[1].replace("@", "")
    amount = int(args[2])
    if amount > get_balance(m.from_user.id):
        return await m.answer("Недостаточно снежинок.")
    users = await bot.get_chat_administrators(m.chat.id) if m.chat else []
    target_id = None
    for user in users:
        if user.user.username and user.user.username.lower() == target_name.lower():
            target_id = user.user.id
            break
    if not target_id:
        return await m.answer("Пользователь не найден.")
    update_balance(m.from_user.id, -amount)
    update_balance(target_id, amount)
    add_history(m.from_user.id, f"Отправил {amount} -> {target_id}")
    add_history(target_id, f"Получил {amount} <- {m.from_user.id}")
    await m.answer(f"Перевод {amount} снежинок отправлен @{target_name}.")

@dp.message_handler(lambda m: m.from_user.id == OWNER_ID)
async def admin(m: types.Message):
    args = m.text.lower().split()
    if "выдать" in args and len(args) == 3:
        target = m.entities[1].user.id if m.entities and len(m.entities) > 1 else None
        if not target:
            return await m.answer("Укажи пользователя.")
        update_balance(target, int(args[2]))
        return await m.answer("Снежинки выданы.")
    elif "отнять" in args and len(args) == 3:
        target = m.entities[1].user.id if m.entities and len(m.entities) > 1 else None
        if not target:
            return await m.answer("Укажи пользователя.")
        update_balance(target, -int(args[2]))
        return await m.answer("Снежинки отняты.")
    elif "бан" in args:
        target = m.entities[1].user.id if m.entities and len(m.entities) > 1 else None
        db = load_db()
        db["banned"].append(str(target))
        save_db(db)
        return await m.answer("Забанен.")
    elif "разбан" in args:
        target = m.entities[1].user.id if m.entities and len(m.entities) > 1 else None
        db = load_db()
        db["banned"] = [u for u in db["banned"] if u != str(target)]
        save_db(db)
        return await m.answer("Разбанен.")
    elif "история" in args:
        target = m.entities[1].user.id if m.entities and len(m.entities) > 1 else None
        h = load_db().get("history", {}).get(str(target), ["История пуста."])
        return await m.answer("\n".join(h[-10:]))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)