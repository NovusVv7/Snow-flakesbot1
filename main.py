import logging
from aiogram import Bot, Dispatcher, executor, types
import asyncio
import random
import os

API_TOKEN = os.getenv("API_TOKEN")
ADMINS = [6359584002]
BONUS_AMOUNT = 5000

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

users = {}
banned_users = set()
roulette_bets = {}

roulette_gif_url = "https://media.tenor.com/TuY5z2GbPOgAAAAC/roulette-casino.gif"

def is_admin(user_id):
    return user_id in ADMINS

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        return await message.answer("Вы забанены.")
    if user_id not in users:
        users[user_id] = {
            'balance': BONUS_AMOUNT,
            'name': message.from_user.first_name,
            'id': user_id
        }
        await message.answer(f"Добро пожаловать, {message.from_user.first_name}! Вам начислено {BONUS_AMOUNT} снежинок!")
    else:
        await message.answer("Вы уже зарегистрированы.")

@dp.message_handler(lambda message: message.text.lower().startswith("профиль"))
async def profile(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        return await message.answer("Сначала напишите /start")
    user = users[user_id]
    await message.answer(f"Профиль:
Имя: {user['name']}
ID: {user['id']}
Баланс: {user['balance']} снежинок")

@dp.message_handler(lambda message: message.text.lower() == "б")
async def balance(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        return await message.answer("Сначала напишите /start")
    await message.answer(f"Ваш баланс: {users[user_id]['balance']} снежинок")

@dp.message_handler(lambda message: message.text.lower().startswith("п "))
async def transfer(message: types.Message):
    try:
        _, target_id, amount = message.text.split()
        user_id = message.from_user.id
        target_id = int(target_id)
        amount = int(amount)
        if user_id not in users or target_id not in users:
            return await message.answer("Один из пользователей не найден.")
        if users[user_id]['balance'] < amount:
            return await message.answer("Недостаточно средств.")
        users[user_id]['balance'] -= amount
        users[target_id]['balance'] += amount
        await message.answer(f"Вы перевели {amount} снежинок пользователю {target_id}.")
    except:
        await message.answer("Используй формат: п [id] [сумма]")

@dp.message_handler(commands=['выдать'])
async def give_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, target_id, amount = message.text.split()
        users[int(target_id)]['balance'] += int(amount)
        await message.answer("Снежинки выданы.")
    except:
        await message.answer("Ошибка выдачи.")

@dp.message_handler(commands=['забрать'])
async def take_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, target_id, amount = message.text.split()
        users[int(target_id)]['balance'] -= int(amount)
        await message.answer("Снежинки забраны.")
    except:
        await message.answer("Ошибка изъятия.")

@dp.message_handler(commands=['забанить'])
async def ban_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, target_id = message.text.split()
        banned_users.add(int(target_id))
        await message.answer("Пользователь забанен.")
    except:
        await message.answer("Ошибка блокировки.")

@dp.message_handler(lambda message: message.text.lower().startswith("мины "))
async def mines_start(message: types.Message):
    try:
        _, bet = message.text.split()
        bet = int(bet)
        user_id = message.from_user.id
        if users[user_id]['balance'] < bet:
            return await message.answer("Недостаточно средств.")
        users[user_id]['balance'] -= bet
        await message.answer("Игра «Мины» началась! Напиши: м x y (например: м 1 2)")
    except:
        await message.answer("Формат: мины [ставка]")

@dp.message_handler(lambda message: message.text.lower().startswith("м "))
async def mines_click(message: types.Message):
    await message.answer("Вы кликнули по мине! (Функция в разработке: будет поле, коэффициент до 60 и кнопка 'забрать')")

@dp.message_handler(lambda message: message.text.lower().startswith("го"))
async def go_roulette(message: types.Message):
    user_id = message.from_user.id
    if user_id not in roulette_bets or not roulette_bets[user_id]:
        return await message.answer("Ставок нет.")
    await message.answer_animation(roulette_gif_url, caption="Запуск рулетки...")
    await asyncio.sleep(5)
    number = random.randint(0, 36)
    color = 'red' if number % 2 == 0 else 'black'
    result_text = f"Выпало число {number} ({color})"
    total_win = 0
    for bet in roulette_bets[user_id]:
        amount, bets = bet
        if str(number) in bets:
            total_win += amount * 36 // len(bets)
    if total_win > 0:
        users[user_id]['balance'] += total_win
        result_text += f"
Вы выиграли: {total_win} снежинок!"
    else:
        result_text += "
Вы проиграли."
    roulette_bets[user_id] = []
    await message.answer(result_text)

@dp.message_handler()
async def handle_bets(message: types.Message):
    try:
        parts = message.text.split()
        amount = int(parts[0])
        numbers = parts[1:]
        user_id = message.from_user.id
        if user_id not in users or users[user_id]['balance'] < amount:
            return await message.answer("Недостаточно баланса или вы не зарегистрированы.")
        users[user_id]['balance'] -= amount
        if user_id not in roulette_bets:
            roulette_bets[user_id] = []
        roulette_bets[user_id].append((amount, numbers))
        await message.answer(f"Ставка принята: {amount} на {', '.join(numbers)}. Напиши 'Го' для запуска.")
    except:
        await message.answer("Формат ставки: [сумма] [числа через пробел]")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
