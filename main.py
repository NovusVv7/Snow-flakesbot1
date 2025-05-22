import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import sqlite3

API_TOKEN = '7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc'
CREATOR_ID = 6359584002

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# FSM состояния
class GameState(StatesGroup):
    waiting_for_go = State()

class MinesState(StatesGroup):
    choosing_settings = State()
    playing = State()

# SQLite
conn = sqlite3.connect("data.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    snowflakes INTEGER DEFAULT 0
)
""")
conn.commit()

# Баланс
def get_balance(user_id):
    cursor.execute("SELECT snowflakes FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    if cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
        cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE user_id = ?", (amount, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, snowflakes) VALUES (?, ?)", (user_id, amount))
    conn.commit()

# /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: Message):
    update_balance(message.from_user.id, 5000)
    await message.answer("Добро пожаловать! Напишите 'го' чтобы начать игру.")
    await GameState.waiting_for_go.set()

@dp.message_handler(lambda m: m.text.lower() == "го", state=GameState.waiting_for_go)
async def start_game(message: Message, state: FSMContext):
    await state.finish()
    await message.answer("Выберите игру: \n1. Рулетка (в разработке)\n2. Снежные мины — напишите 'мины'")
    
# Снежные мины
@dp.message_handler(lambda m: m.text.lower() == "мины")
async def mines_start(message: Message):
    await message.answer("Введите ставку и количество мин (например: `100 5`):")
    await MinesState.choosing_settings.set()

@dp.message_handler(state=MinesState.choosing_settings)
async def set_mines_game(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        bet, mines = int(parts[0]), int(parts[1])
        balance = get_balance(message.from_user.id)

        if bet <= 0 or mines <= 0 or mines >= 25:
            return await message.answer("Неверные данные. Мин должно быть от 1 до 24.")

        if balance < bet:
            return await message.answer("Недостаточно снежинок.")

        # Генерация мин
        mine_positions = random.sample(range(25), mines)
        opened = []

        await state.update_data(bet=bet, mines=mine_positions, opened=opened)
        update_balance(message.from_user.id, -bet)
        await message.answer("Поле 5x5 готово. Введите клетку (например: A1, B3):")
        await MinesState.playing.set()

    except Exception:
        await message.answer("Ошибка ввода. Формат: ставка количество_мин")

@dp.message_handler(state=MinesState.playing)
async def mines_play(message: Message, state: FSMContext):
    cell_map = {
        "A": 0, "B": 1, "C": 2, "D": 3, "E": 4
    }

    data = await state.get_data()
    bet = data['bet']
    mines = data['mines']
    opened = data['opened']

    cell = message.text.upper()
    if len(cell) < 2 or cell[0] not in cell_map or not cell[1:].isdigit():
        return await message.answer("Неверная клетка. Пример: B3")

    row = cell_map[cell[0]]
    col = int(cell[1:]) - 1
    if not (0 <= col < 5):
        return await message.answer("Номер должен быть от 1 до 5.")

    index = row * 5 + col
    if index in opened:
        return await message.answer("Эта клетка уже открыта!")

    if index in mines:
        await message.answer("Бум! Вы попали на мину. Игра окончена.")
        await state.finish()
    else:
        opened.append(index)
        await state.update_data(opened=opened)
        reward = bet // 5
        update_balance(message.from_user.id, reward)
        await message.answer(f"Безопасно! Вы получили {reward} снежинок. Введите следующую клетку:")

        if len(opened) == 25 - len(mines):
            await message.answer("Вы выиграли! Все безопасные клетки открыты.")
            await state.finish()

# Создатель: передача снежинок
@dp.message_handler(lambda msg: msg.text.startswith("П "))
async def give_currency(msg: Message):
    if msg.from_user.id != CREATOR_ID:
        return await msg.reply("Недостаточно прав.")
    try:
        amount = int(msg.text.split()[1])
        receiver_id = msg.reply_to_message.from_user.id if msg.reply_to_message else None
        if not receiver_id:
            return await msg.reply("Ответьте на сообщение пользователя.")
        update_balance(receiver_id, amount)
        await msg.answer(f"Передано {amount} снежинок.")
    except Exception as e:
        await msg.reply(f"Ошибка: {e}")

# Выдать / забрать снежинки
@dp.message_handler(lambda msg: msg.text.startswith("выдать") or msg.text.startswith("забрать"))
async def manage_balance(msg: Message):
    if msg.from_user.id != CREATOR_ID:
        return await msg.reply("Недостаточно прав.")
    try:
        parts = msg.text.split()
        cmd, amount = parts[0], int(parts[1])
        target_id = msg.reply_to_message.from_user.id if msg.reply_to_message else msg.from_user.id
        update_balance(target_id, amount if cmd == "выдать" else -amount)
        await msg.answer(f"{cmd.capitalize()} {abs(amount)} снежинок.")
    except Exception as e:
        await msg.reply(f"Ошибка: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)