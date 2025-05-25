
import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base, mapped_column, Mapped
from sqlalchemy import BigInteger, String, select, update, Integer
from sqlalchemy.exc import IntegrityError

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"  # Replace with your actual bot token
ADMIN_ID = [6359584002]  # Replace with your actual admin IDs

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

engine = create_async_engine("sqlite+aiosqlite:///bot.db", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"  # Explicitly set table name

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    username: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)

    icecream: Mapped[int] = mapped_column(BigInteger, default=1000)


# Define type hints for your game data for clarity and type safety
MineGameData = dict[str, int | set[int] | int | None]
RouletteBet = dict[str, int | int | str]

games: dict[int, MineGameData] = {}
roulette_bets: dict[int, list[RouletteBet]] = {}
banned_users = set()
COEFFS = [1.7, 2.5, 3, 4.67, 25]

RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMS = set(range(1, 37)) - RED_NUMS


def parse_amount(s: str) -> int | None:
    s = s.lower().strip()

    if s.endswith("кк") or s.endswith("м"):
        num_part = s[:-2] if s.endswith("кк") else s[:-1]
        try:
            return int(float(num_part) * 1_000_000)
        except ValueError:
            return None

    if s.endswith("к"):
        num_part = s[:-1]
        try:
            return int(float(num_part) * 1_000)
        except ValueError:
            return None

    if s.isdigit():
        return int(s)
    return None


class AddUserMiddleware(BaseMiddleware):
    async def call(self, handler, event: Message, data):
        if event.from_user:
            await add_user(event.from_user)

            async with async_session() as session:
                user = await session.get(User, event.from_user.id)

                if user:
                    await session.execute(
                        update(User)
                        .where(User.user_id == event.from_user.id)
                        .values(username=event.from_user.username, first_name=event.from_user.first_name)
                    )
                    await session.commit()  # Commit the changes after updating
        return await handler(event, data)


dp.message.middleware(AddUserMiddleware())


async def add_user(user):
    async with async_session() as session:
        try:
            session.add(User(user_id=user.id, username=user.username, first_name=user.first_name))
            await session.commit()
        except IntegrityError:
            await session.rollback()


async def get_balance(uid: int) -> int:
    async with async_session() as session:
        user = await session.get(User, uid)
        return user.icecream if user else 0


async def update_balance(uid: int, amount: int):
    async with async_session() as session:
        user = await session.get(User, uid)
        if user:
            user.icecream += amount
            await session.commit()


async def get_top_users():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .order_by(User.icecream.desc())
            .limit(10)
        )
        return result.scalars().all()


@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer(
        "❄️🍨 Добро пожаловать в IceCream Casino! 🍧\n\n"
        "Основные команды:\n"
        "🍧 Б - проверить баланс\n"
        "💣 Мины 100 - игра в мины\n"
        "🎰 100 1 2 3 - ставки на рулетку\n"
        "🔄 П 1000 (ответом) - передать мороженое\n"
        "🏆 /топ - топ игроков\n"
        "ℹ️ /info - информация о боте"
    )


@dp.message(Command("info"))
async def info(msg: Message):
    await msg.answer(
        "🍦 IceCream Casino Бот\n"
        "👑 Владелец: @admin\n"
        "🎮 Игры:\n"
        "• 💣 Мины (коэффициенты до x25)\n"
        "• 🎰 Рулетка (европейская)\n"
        "💎 Валюта: Мороженое 🍧"
    )


@dp.message(Command("топ"))
async def top(msg: Message):
    top_users = await get_top_users()
    txt = "🏆 Топ игроков по мороженому 🍧:\n\n"
    for i, user in enumerate(top_users, 1):
        txt += f"{i}. {user.first_name} (@{user.username}) — {user.icecream}🍧\n"
    await msg.answer(txt)


@dp.message(F.text.lower() == "б")
async def balance(msg: Message):
    bal = await get_balance(msg.from_user.id)
    await msg.answer(
        f"👤 Игрок: {msg.from_user.first_name}\n"
        f"📦 Баланс: {bal}🍧\n"
        f"🆔 ID: {msg.from_user.id}"
    )


@dp.message(Command(commands=["выдать", "забрать", "бан", "разбан"]))
async def admin_cmd(msg: Message):
    if msg.from_user.id not in ADMIN_ID or not msg.reply_to_message:
        return

    user_id_to_modify = msg.reply_to_message.from_user.id

    try:
        amount = int(msg.text.split()[1])
    except (IndexError, ValueError):
        await msg.reply("❌ Ошибка формата. Пример: /выдать 1000")
        return

    if "/выдать" in msg.text:
        await update_balance(user_id_to_modify, amount)
        await msg.reply(f"✅ Выдано {amount}🍧")
    elif "/забрать" in msg.text:
        current_balance = await get_balance(user_id_to_modify)
        amount_to_take = min(amount, current_balance)
        if amount_to_take <= 0:
            await msg.reply("❌ Нечего забирать")
            return
        await update_balance(user_id_to_modify, -amount_to_take)
        await msg.reply(f"✅ Забрано {amount_to_take}🍧")
    elif "/бан" in msg.text:
        banned_users.add(user_id_to_modify)
        await msg.reply("⛔ Пользователь забанен")
    elif "/разбан" in msg.text:
        if user_id_to_modify in banned_users:
            banned_users.remove(user_id_to_modify)
            await msg.reply("✅ Пользователь разбанен")
        else:
            await msg.reply("❌ Пользователь не забанен")


# ---- Mines Game ----
@dp.message(F.text.lower().startswith("мины"))
async def mines(msg: Message):
    uid = msg.from_user.id
    if uid in banned_users:
        await msg.answer("Вы забанены и не можете играть.")
        return

    try:
        parts = msg.text.split()
        if len(parts) != 2:
            await msg.answer("Используйте: мины <ставка>")
            return
        bet_str = parts[1]
        bet = parse_amount(bet_str)  # Use parse_amount function
        if bet is None or bet <= 0:
            await msg.answer("Ставка должна быть положительным числом.")
            return

    except (IndexError, ValueError):
        await msg.answer("Используйте: мины <ставка>")
        return

    bal = await get_balance(uid)
    if bal < bet:
        await msg.answer("Недостаточно средств на балансе.")
        return

    # Initialize the game state
    games[uid] = {
        "bet": bet,
        "step": 0,
        "opened": set(),
        "mines": set(random.sample(range(1, 10), 3)),
        "chat_id": msg.chat.id,
        "message_id": None,
    }

    # Deduct the bet amount immediately before starting the game
    await update_balance(uid, -bet)

    # Create the initial minefield layout
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(1, 10):
        btn = InlineKeyboardButton(text=str(i), callback_data=f"mine_open_{i}")
        buttons.append(btn)
        if i % 3 == 0:
            markup.row(*buttons[i - 3:i])  # Use slicing for correct row creation
    markup.add(InlineKeyboardButton(text="🚩 Забрать", callback_data="mine_take"))

    # Send the initial minefield message
    sent_message = await msg.answer(
        text=f"Игра в мины началась!\nСтавка: {bet}🍧\nВыберите ячейку.",
        reply_markup=markup
    )

    # Store the message ID in the game state
    games[uid]["message_id"] = sent_message.message_id


@dp.callback_query(F.data.startswith("mine_open_"))
async def mine_open(call: CallbackQuery):
    uid = call.from_user.id

    if uid not in games:
        await call.answer("Игра не найдена. Начните новую игру.")
        return

    game: MineGameData = games[uid]
    index = int(call.data[len("mine_open_"):])

    if index in game["opened"]:
        await call.answer("Ячейка уже открыта.")
        return

    game["opened"].add(index)  # Mark cell as opened

    if index in game["mines"]:
        await update_balance(uid, -game["bet"])  # Deduct bet
        del games[uid]
        await bot.edit_message_text(
            text="💥 Вы подорвались на мине! 💣",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        await call.answer("Вы проиграли!")  # Notify the user
        return

    game["step"] += 1

    if game["step"] >= len(COEFFS):
        win = int(game["bet"] * COEFFS[-1])
        await update_balance(uid, win)
        del games[uid]
        await bot.edit_message_text(
            text=f"🎉 Вы выиграли! Коэффициент x{COEFFS[-1]}, выигрыш {win}🍧!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        await call.answer("Вы выиграли!")
        return

    win_coeff = COEFFS[game["step"] - 1]

    # Create the updated minefield layout
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(1, 10):
        if i in game["opened"]:
            button_text = "✅"
        else:
            button_text = str(i)
        btn = InlineKeyboardButton(text=button_text, callback_data=f"mine_open_{i}")
        buttons.append(btn)
        if i % 3 == 0:
            markup.row(*buttons[i - 3:i])  # Use slicing for correct row creation
    markup.add(InlineKeyboardButton(text="🚩 Забрать", callback_data="mine_take"))

    await bot.edit_message_text(
        text=f"Игра в мины!\nСтавка: {game['bet']}🍧\nКоэффициент: x{win_coeff:.2f}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )
    await call.answer("Ячейка открыта!")


@dp.callback_query(F.data == "mine_take")
async def mine_take(call: CallbackQuery):
    uid = call.from_user.id

    if uid not in games:
        await call.answer("Игра не найдена. Начните новую игру.")
        return

    game: MineGameData = games[uid]

    if game["step"] == 0:
        win = game["bet"]  # Return the initial bet
    else:
        win = int(game["bet"] * COEFFS[game["step"] - 1])  # Correct calculation

    await update_balance(uid, win)
    del games[uid]

    await bot.edit_message_text(
        text=f"🎉 Вы забрали выигрыш {win}🍧!",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    await call.answer("Выигрыш получен!")


# ---- Roulette Game ----
@dp.message(F.text.lower().startswith("🎰"))
async def roulette(msg: Message):
    uid = msg.from_user.id
    if uid in banned_users:
        await msg.answer("Вы забанены и не можете играть.")
        return

    try:
        parts = msg.text.split()
        if len(parts) < 3:
            await msg.answer("Используйте: 🎰 <ставка> <число1> <число2> ...")
            return

        bet_str = parts[1]
        bet = parse_amount(bet_str)  # Use parse_amount function
        if bet is None or bet <= 0:
            await msg.answer("Ставка должна быть положительным числом.")
            return

        numbers = []
        for part in parts[2:]:
            num = parse_amount(part)
            if num is None:
                await msg.answer("Неверный формат числа в ставке.")
                return
            numbers.append(num)

        for num in numbers:
            if not 0 <= num <= 36:
                await msg.answer("Числа должны быть от 0 до 36.")
                return

    except (IndexError, ValueError):
        await msg.answer("Используйте: 🎰 <ставка> <число1> <число2> ...")
        return

    bal = await get_balance(uid)
    if bal < bet:
        await msg.answer("Недостаточно средств на балансе.")
        return

    await update_balance(uid, -bet)  # Deduct bet upfront

    result = random.randint(0, 36)
    win = 0

    if result in numbers:
        win = bet * 35  # Payout for a direct hit (35 to 1 payout)
        await update_balance(uid, win)
        await msg.answer(f"🎉 Выпало число {result}! Вы выиграли {win}🍧!")
    else:
        await msg.answer(f"🎲 Выпало число {result}. Вы проиграли.")

# ---- Initialize Database ----
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---- Run Bot ----
async def main():
    await on_startup()
    dp.startup.register(on_startup)  # Register startup function

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
if __name__ == "__main__":
    import asyncio

    async def main():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await dp.start_polling(bot)

    asyncio.run(main())