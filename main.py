from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import sqlite3, random, time

API_TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"
CREATOR_ID =6359584002  # Ваш Telegram ID

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

# Команды создателя
@dp.message_handler(commands=['add'])
async def add_snowflakes(message: Message):
    if message.from_user.id != CREATOR_ID:
        return
    try:
        _, user_id, amount = message.text.split()
        update_balance(int(user_id), int(amount))
        await message.answer(f"✅ Добавлено {amount} снежинок пользователю {user_id}")
    except:
        await message.answer("Формат: /add [user_id] [amount]")

@dp.message_handler(commands=['remove'])
async def remove_snowflakes(message: Message):
    if message.from_user.id != CREATOR_ID:
        return
    try:
        _, user_id, amount = message.text.split()
        update_balance(int(user_id), -int(amount))
        await message.answer(f"✅ Изъято {amount} снежинок у пользователя {user_id}")
    except:
        await message.answer("Формат: /remove [user_id] [amount]")

@dp.message_handler(commands=['balance'])
async def check_balance(message: Message):
    if message.from_user.id != CREATOR_ID:
        return
    try:
        _, user_id = message.text.split()
        balance = get_balance(int(user_id))
        await message.answer(f"Баланс пользователя {user_id}: {balance}❄️")
    except:
        await message.answer("Формат: /balance [user_id]")

@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    update_balance(message.from_user.id, 5000)
    text = (
        "❄️ Добро пожаловать в SnowCasino! ❄️\n"
        "Доступные команды:\n"
        "▶️ го - начать игру в рулетку\n"
        "💣 мины - игра в мины\n"
        "💰 б - проверить баланс\n"
        "🎁 /bonus - получить бонус (раз в 5 часов)"
    )
    await message.answer(text)

@dp.message_handler(commands=['bonus'])
async def cmd_bonus(message: Message):
    bonus = try_give_bonus(message.from_user.id)
    balance = get_balance(message.from_user.id)
    if bonus:
        await message.answer(f"🎁 Вы получили бонус: +{bonus}❄️\nТекущий баланс: {balance}❄️")
    else:
        await message.answer("⏳ Бонус можно получить раз в 5 часов!")

@dp.message_handler(lambda m: m.text.lower() == 'б')
async def show_balance(message: Message):
    balance = get_balance(message.from_user.id)
    await message.answer(f"❄️ Ваш баланс: {balance} снежинок")

# Улучшенная рулетка
ROULETTE_PAYOUTS = {
    'number': 35,
    'even_odd': 1,
    'color': 1,
    'dozen': 2
}

@dp.message_handler(lambda m: m.text.lower() == "го")
async def go_command(message: Message):
    await GameState.roulette_waiting.set()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Красное'), KeyboardButton('Чёрное'))
    markup.add(KeyboardButton('Чётное'), KeyboardButton('Нечётное'))
    await message.answer(
        "🎰 Режим рулетки\n"
        "Введите ставку и тип (примеры):\n"
        "• 100 красное\n"
        "• 50 12 (конкретное число)\n"
        "• 200 1-12 (первый десяток)",
        reply_markup=markup
    )

@dp.message_handler(state=GameState.roulette_waiting)
async def handle_roulette_bet(message: Message, state: FSMContext):
    try:
        parts = message.text.lower().split()
        if len(parts) < 2:
            raise ValueError
        
        amount = int(parts[0])
        bet_type = ' '.join(parts[1:])
        balance = get_balance(message.from_user.id)
        
        if amount < 10:
            await message.reply("Минимальная ставка: 10❄️")
            return
        if balance < amount:
            await message.reply("Недостаточно снежинок❄️")
            return
        
        # Генерация результата
        result = random.randint(0, 36)
        is_red = result in {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        
        # Проверка выигрыша
        win = False
        multiplier = 1
        
        try: # Проверка на число
            number_bet = int(bet_type)
            win = (number_bet == result)
            multiplier = ROULETTE_PAYOUTS['number']
        except:
            if bet_type in ['красное', 'red']:
                win = is_red and result != 0
                multiplier = ROULETTE_PAYOUTS['color']
            elif bet_type in ['чёрное', 'black']:
                win = not is_red and result != 0
                multiplier = ROULETTE_PAYOUTS['color']
            elif bet_type in ['чётное', 'even']:
                win = result % 2 == 0 and result != 0
                multiplier = ROULETTE_PAYOUTS['even_odd']
            elif bet_type in ['нечётное', 'odd']:
                win = result % 2 == 1
                multiplier = ROULETTE_PAYOUTS['even_odd']
            elif '-' in bet_type:
                start, end = map(int, bet_type.split('-'))
                win = start <= result <= end
                multiplier = ROULETTE_PAYOUTS['dozen']
        
        # Определение цвета для вывода
        color = '🔴' if is_red else ('🟢' if result == 0 else '⚫')
        
        if win:
            win_amount = amount * multiplier
            update_balance(message.from_user.id, win_amount)
            await message.answer(
                f"{color} Выпало {result}\n"
                f"🎉 Вы выиграли {win_amount}❄️ (x{multiplier})"
            )
        else:
            update_balance(message.from_user.id, -amount)
            await message.answer(
                f"{color} Выпало {result}\n"
                f"💸 Вы проиграли {amount}❄️"
            )
        await state.finish()
    except:
        await message.reply("❌ Ошибка в ставке. Используйте примеры из инструкции")
        await state.finish()

# Улучшенные мины
@dp.message_handler(lambda m: m.text.lower() == "мины")
async def mines_game(message: Message):
    await GameState.mines_settings.set()
    await message.answer(
        "💣 Настройки игры Мины\n"
        "Введите через пробел:\n"
        "• Ставку\n• Размер поля (3-25)\n• Количество мин (1-10)\n"
        "Пример: 1000 15 3"
    )

@dp.message_handler(state=GameState.mines_settings)
async def setup_mines_game(message: Message, state: FSMContext):
    try:
        bet, size, mines = map(int, message.text.split())
        if not (10 <= bet <= 100000):
            await message.reply("🚫 Ставка должна быть от 10 до 100000❄️")
            return
        if not (3 <= size <= 25):
            await message.reply("🚫 Размер поля от 3 до 25 клеток")
            return
        if not (1 <= mines <= min(10, size-1)):
            await message.reply("🚫 Некорректное количество мин")
            return
        
        if get_balance(message.from_user.id) < bet:
            await message.reply("❌ Недостаточно средств для ставки")
            return
        
        await state.update_data(
            bet=bet,
            size=size,
            mines=mines,
            opened=[],
            mines_positions=[],
            multiplier=1.0
        )
        await GameState.mines_playing.set()
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton('Забрать 🏆'))
        
        await message.answer(
            f"Игра началась!\n"
            f"🏁 Ставка: {bet}❄️\n"
            f"🔢 Поле: {size} клеток\n"
            f"💣 Мины: {mines}\n"
            f"Текущий множитель: x1.0",
            reply_markup=markup
        )
        await show_mines_field(message, state)
    except:
        await message.reply("❌ Ошибка ввода. Используйте формат: 1000 15 3")

async def show_mines_field(message: Message, state: FSMContext):
    data = await state.get_data()
    size = data['size']
    opened = data['opened']
    mines = data['mines_positions']
    
    field = ""
    for i in range(size):
        if i in opened:
            if i in mines:
                field += "💥 "
            else:
                field += "🟩 "
        else:
            field += "⬜ "
        if (i + 1) % 5 == 0:
            field += "\n"
    
    await message.answer(f"Поле ({size} клеток):\n{field}\nВыберите клетку (1-{size}):")

@dp.message_handler(state=GameState.mines_playing, text='Забрать 🏆')
async def take_mines_win(message: Message, state: FSMContext):
    data = await state.get_data()
    win_amount = int(data['bet'] * data['multiplier'])
    update_balance(message.from_user.id, win_amount)
    await message.answer(
        f"🏆 Вы забрали выигрыш!\n"
        f"💰 Получено: {win_amount}❄️\n"
        f"🎯 Множитель: x{data['multiplier']:.2f}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.finish()

@dp.message_handler(state=GameState.mines_playing)
async def process_mines_move(message: Message, state: FSMContext):
    try:
        cell = int(message.text) - 1
        data = await state.get_data()
        
        if cell < 0 or cell >= data['size']:
            await message.reply("🚫 Неверный номер клетки!")
            return
            
        if cell in data['opened']:
            await message.reply("ℹ️ Эта клетка уже открыта!")
            return
        
        # Генерация мин после первого хода
        if not data['mines_positions']:
            available = [i for i in range(data['size']) if i != cell]
            mines = random.sample(available, data['mines'])
            await state.update_data(mines_positions=mines)
        
        opened = data['opened'] + [cell]
        mines = data['mines_positions']
        
        if cell in mines:
            update_balance(message.from_user.id, -data['bet'])
            await message.answer(
                "💥 Вы подорвались на мине!\n"
                f"💸 Потеряно: {data['bet']}❄️",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.finish()
            return
        
        # Обновление множителя
        multiplier = data['multiplier'] * 1.5
        await state.update_data(opened=opened, multiplier=multiplier)
        
        # Проверка победы
        if len(opened) == data['size'] - data['mines']:
            win_amount = int(data['bet'] * multiplier)
            update_balance(message.from_user.id, win_amount)
            await message.answer(
                f"🎉 Вы открыли все клетки!\n"
                f"💰 Выигрыш: {win_amount}❄️\n"
                f"🎯 Множитель: x{multiplier:.2f}",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.finish()
        else:
            await state.update_data(multiplier=multiplier)
            await message.answer(f"Текущий множитель: x{multiplier:.2f}")
            await show_mines_field(message, state)
    except:
        await message.reply("❌ Ошибка ввода. Введите номер клетки или 'Забрать'")

@dp.message_handler(lambda m: m.text.lower().startswith("передать "))
async def transfer_currency(message: Message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            raise ValueError
        
        recipient_id = int(parts[1])
        amount = int(parts[2])
        
        if amount <= 0:
            await message.reply("🚫 Сумма должна быть положительной!")
            return
            
        sender_id = message.from_user.id
        if sender_id == recipient_id:
            await message.reply("🚫 Нельзя передавать себе!")
            return
            
        if get_balance(sender_id) < amount:
            await message.reply("❌ Недостаточно средств для перевода!")
            return
            
        update_balance(sender_id, -amount)
        update_balance(recipient_id, amount)
        await message.reply(f"✅ Успешно передано {amount}❄️ пользователю {recipient_id}")
    except:
        await message.reply("❌ Формат: Передать [ID] [Сумма]")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)