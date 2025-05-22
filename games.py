from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def handle_games(message: types.Message):
    game = message.text.strip().lower()

    if game == "мины":
        await message.answer(
            "Мини-игра 'Мины':\n\nТебе предстоит выбрать клетки на поле 5x5. В некоторых клетках спрятаны мины.\n"
            "Если ты попадешь на мину — проиграешь всю ставку.\n\nСтавка от 100 круннов."
        )
    elif game == "крипта":
        await message.answer(
            "Мини-игра 'Крипта':\n\nТвоя задача — следить за множителем, который увеличивается с каждым секундом.\n"
            "Ты можешь забрать выигрыш в любой момент до краша. Если не успеешь, ставка сгорает.\n\nСтавка от 10 круннов."
        )
    elif game == "ракета":
        await message.answer(
            "Мини-игра 'Ракета':\n\nРакета начинает взлетать, множитель растет, и ты можешь забрать выигрыш в любой момент.\n"
            "Если ракета взорвется — ты потеряешь свою ставку.\n\nСтавка от 100 круннов."
        )
    else:
        await message.answer("Неизвестная игра. Доступные игры: Мины, Крипта, Ракета.")
        
def register_games(dp):
    dp.register_message_handler(handle_games, commands=["Игры, игры"], state="*")
