import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties  # ВАЖНО

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

roulette_history = []
user_balances = {}

START_BALANCE = 1000

def get_balance(user_id: int) -> int:
    if user_id not in user_balances:
        user_balances[user_id] = START_BALANCE
    return user_balances[user_id]

def update_balance(user_id: int, amount: int):
    get_balance(user_id)
    user_balances[user_id] += amount

@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()
    user_id = message.from_user.id

    # Баланс
    if text.lower() == "баланс":
        balance = get_balance(user_id)
        await message.answer(f"Ваш баланс: {balance}")
        return

    # Монета
    if text.lower().startswith("монета"):
        parts = text.split()
        if len(parts) != 3:
            await message.answer("Формат: Монета Орёл 100")
            return
        _, choice, amount = parts
        try:
            amount = int(amount)
        except ValueError:
            await message.answer("Ставка должна быть числом.")
            return

        balance = get_balance(user_id)
        if amount > balance:
            await message.answer("Недостаточно средств.")
            return

        result = random.choice(["Орёл", "Решка"])
        if choice.lower() == result.lower():
            winnings = amount * 2
            update_balance(user_id, winnings)
            await message.answer(f"Выпало: {result}! Вы выиграли {winnings}!")
        else:
            update_balance(user_id, -amount)
            await message.answer(f"Выпало: {result}. Вы проиграли {amount}.")
        return

    # Лог
    if text.lower() == "лог":
        if not roulette_history:
            await message.answer("Лог пуст.")
        else:
            await message.answer("Последние результаты:\n" + "\n".join(roulette_history))
        return

    # Рулетка
    parts = text.split()
    if len(parts) < 2:
        await message.answer("Формат: <ставка> <число|цвет|диапазон> ...")
        return

    try:
        bet = int(parts[0])
        choices = parts[1:]
    except ValueError:
        await message.answer("Первая часть должна быть числом — это ставка.")
        return

    balance = get_balance(user_id)
    if bet > balance:
        await message.answer("Недостаточно средств для ставки.")
        return

    number = random.randint(0, 36)
    color = "красное" if number != 0 and number % 2 == 0 else "чёрное"
    roulette_history.append(f"{number} ({color})")
    if len(roulette_history) > 10:
        roulette_history.pop(0)

    win = False
    total_multiplier = 0

    for choice in choices:
        c = choice.lower()
        if c.isdigit() and int(c) == number:
            total_multiplier += 35
            win = True
        elif c in ["красное", "чёрное"] and c == color:
            total_multiplier += 2
            win = True
        elif c == "1-18" and 1 <= number <= 18:
            total_multiplier += 2
            win = True
        elif c == "19-36" and 19 <= number <= 36:
            total_multiplier += 2
            win = True

    if win:
        winnings = bet * total_multiplier
        update_balance(user_id, winnings)
        await message.answer(f"Выпало {number} ({color})! Вы выиграли {winnings}!")
    else:
        update_balance(user_id, -bet)
        await message.answer(f"Выпало {number} ({color})! Вы проиграли {bet}.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())