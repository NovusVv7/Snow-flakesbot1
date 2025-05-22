from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import sqlite3, random, time

API_TOKEN = '7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc'
CREATOR_ID =6359584002  # Замените на ваш Telegram ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Состояния FSM
class GameState(StatesGroup):
    roulette_waiting = State()
    mines_settings = State()
    mines_playing = State()

# Инициализация базы данных
conn = sqlite3.connect("data.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    snowflakes INTEGER DEFAULT 0,
    last_bonus INTEGER DEFAULT 0
)
""")
conn.commit()

# Работа с балансом
BONUS_INTERVAL = 5 * 60 * 60  # 5 часов

def get_balance(user_id):
    cursor.execute("SELECT snowflakes FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE user_id = ?", (amount, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, snowflakes) VALUES (?, ?)", (user_id, amount))
    conn.commit()

def try_give_bonus(user_id):
    now = int(time.time())
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    last = result[0] if result else 0
    
    if now - last >= BONUS_INTERVAL:
        bonus = random.randint(5000, 20000)
        update_balance(user_id, bonus)
        cursor.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (now, user_id))
        conn.commit()
        return bonus
    return None

@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    update_balance(message.from_user.id, 5000)
    await message.answer("Добро пожаловать! Напишите 'го' для начала или 'мины' для игры.")

@dp.message_handler(lambda m: m.text.lower() == 'б')
async def show_balance(message: Message):
    bonus = try_give_bonus(message.from_user.id)
    balance = get_balance(message.from_user.id)
    if bonus:
        await message.answer(f"Баланс: {balance} снежинок\nВы получили бонус: +{bonus}!")
    else:
        await message.answer(f"Баланс: {balance} снежинок\nБонус доступен раз в 5 часов.")

@dp.message_handler(lambda m: m.text.lower() == "го")
async def go_command(message: Message):
    await GameState.roulette_waiting.set()
    await message.answer("Режим рулетки активирован. Введите ставку (пример: 100 red)")

@dp.message_handler(state=GameState.roulette_waiting)
async def handle_roulette_bet(message: Message, state: FSMContext):
    parts = message.text.lower().split()
    if len(parts) < 2:
        await message.reply("Пример ставки: 100 red")
        return
    
    try:
        amount = int(parts[0])
        choice = parts[1]
        
        if get_balance(message.from_user.id) < amount:
            await message.reply("Недостаточно снежинок.")
            return

        win = False
        result = random.choice(["red", "black"])
        if choice == result:
            win = True

        if win:
            update_balance(message.from_user.id, amount)
            await message.reply(f"Выпало {result}. Вы выиграли! +{amount}")
        else:
            update_balance(message.from_user.id, -amount)
            await message.reply(f"Выпало {result}. Вы проиграли. -{amount}")
        await state.finish()
    except:
        await message.reply("Ошибка в ставке.")

@dp.message_handler(lambda m: m.text.lower().startswith("передать "))
async def transfer_currency(message: Message):
    try:
        parts = message.text.lower().split()
        if len(parts) < 3:
            await message.reply("Формат: передать [ID] [сумма]")
            return
        
        recipient_id = int(parts[1])
        amount = int(parts[2])
        
        if amount <= 0:
            await message.reply("Сумма должна быть положительной!")
            return
            
        sender_id = message.from_user.id
        if sender_id == recipient_id:
            await message.reply("Нельзя передавать себе!")
            return
            
        if get_balance(sender_id) < amount:
            await message.reply("Недостаточно снежинок для перевода.")
            return
            
        update_balance(sender_id, -amount)
        update_balance(recipient_id, amount)
        await message.reply(f"Вы успешно передали {amount} снежинок пользователю {recipient_id}")
    except Exception as e:
        await message.reply(f"Ошибка перевода: {str(e)}")

# Игра "Мины"
@dp.message_handler(lambda m: m.text.lower() == "мины")
async def mines_game(message: Message):
    await GameState.mines_settings.set()
    await message.answer("Настройки игры 'Мины':\n"
                        "Введите ставку, количество клеток и мин через пробел\n"
                        "Пример: 1000 25 5 (ставка 1000, поле 5x5, 5 мин)")

@dp.message_handler(state=GameState.mines_settings)
async def setup_mines_game(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.reply("Нужно 3 числа: ставка, клетки, мины")
            return
            
        bet, cells, mines = map(int, parts)
        if bet <= 0 or cells <= 0 or mines <= 0:
            await message.reply("Все числа должны быть положительными!")
            return
            
        if mines >= cells:
            await message.reply("Количество мин должно быть меньше количества клеток!")
            return
            
        if get_balance(message.from_user.id) < bet:
            await message.reply("Недостаточно снежинок для ставки!")
            return
            
        await state.update_data(bet=bet, cells=cells, mines=mines, opened=[])
        await GameState.mines_playing.set()
        await show_mines_field(message, state)
    except:
        await message.reply("Ошибка ввода. Используйте числа!")

async def show_mines_field(message: Message, state: FSMContext):
    data = await state.get_data()
    cells = data['cells']
    opened = data.get('opened', [])
    
    field = ""
    for i in range(cells):
        if i in opened:
            field += "🟩 "
        else:
            field += "⬜ "
        if (i + 1) % 5 == 0:
            field += "\n"
    
    await message.answer(f"Поле ({cells} клеток, {data['mines']} мин):\n{field}\n"
                        f"Выберите клетку (1-{cells})")

@dp.message_handler(state=GameState.mines_playing)
async def process_mines_move(message: Message, state: FSMContext):
    try:
        cell = int(message.text) - 1
        data = await state.get_data()
        
        if cell < 0 or cell >= data['cells']:
            await message.reply("Неверный номер клетки!")
            return
            
        if cell in data.get('opened', []):
            await message.reply("Эта клетка уже открыта!")
            return
            
        # Генерация мин при первом ходе
        if 'mines_positions' not in data:
            mines_positions = random.sample(range(data['cells']), data['mines'])
            await state.update_data(mines_positions=mines_positions)
        else:
            mines_positions = data['mines_positions']
        
        opened = data.get('opened', [])
        opened.append(cell)
        await state.update_data(opened=opened)
        
        if cell in mines_positions:
            update_balance(message.from_user.id, -data['bet'])
            await message.answer("💥 Вы наткнулись на мину и проиграли!")
            await state.finish()
        else:
            if len(opened) == data['cells'] - data['mines']:
                win_amount = data['bet'] * 2
                update_balance(message.from_user.id, win_amount)
                await message.answer(f"🎉 Вы открыли все безопасные клетки и выиграли {win_amount}!")
                await state.finish()
            else:
                await show_mines_field(message, state)
    except:
        await message.reply("Ошибка ввода. Введите номер клетки!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)