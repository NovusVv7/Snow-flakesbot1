
import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, mapped_column, Mapped
from sqlalchemy import BigInteger, String, select, update
from sqlalchemy.exc import IntegrityError

TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
ADMIN_ID = [123456789, 987654321]  # Замените на свои ID

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
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)
    icecream: Mapped[int] = mapped_column(BigInteger, default=1000)

games = {}
roulette_bets: dict[int, list[dict]] = {}
banned_users = set()
COEFFS = [1.7, 2.5, 3, 4.67, 25]

RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
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
    async def __call__(self, handler, event: Message, data):
        if event.from_user:
            await add_user(event.from_user)
            async with async_session() as session:
                user = await session.get(User, event.from_user.id)
                if user:
                    await session.execute(update(User).where(User.user_id == event.from_user.id).values(
                        username=event.from_user.username, first_name=event.from_user.first_name))
        return await handler(event, data)

dp.message.middleware(AddUserMiddleware())

async def add_user(user):
    async with async_session() as session:
        try:
            session.add(User(user_id=user.id, username=user.username, first_name=user.first_name))
            await session.commit()
        except IntegrityError:
            await session.rollback()

async def get_balance(uid: int):
    async with async_session() as session:
        user = await session.get(User, uid)
        return user.icecream if user else 0

async def update_balance(uid: int, amount: int):
    async with async_session() as session:
        user = await session.get(User, uid)
        if user:
            user.icecream += amount
            await session.commit()

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer(
        "❄️🍨 Добро пожаловать в IceCream Casino! 🍧

"
        "Основные команды:
"
        "🍧 Б - проверить баланс
"
        "💣 Мины 100 - игра в мины
"
        "🎰 100 1 2 3 - ставки на рулетку
"
        "🔄 П 1000 (ответом) - передать мороженое
"
        "🏆 /топ - топ игроков
"
        "ℹ️ /info - информация о боте"
    )

@dp.message(F.text.lower() == "б")
async def balance(msg: Message):
    bal = await get_balance(msg.from_user.id)
    await msg.answer(
        f"👤 Игрок: {msg.from_user.first_name}
"
        f"📦 Баланс: {bal}🍧
"
        f"🆔 ID: {msg.from_user.id}"
    )

@dp.message()
async def parse_bets(msg: Message):
    chat_id = msg.chat.id
    if msg.from_user.id in banned_users:
        return

    parts = msg.text.lower().split()
    if not parts:
        return
    if not parts[0].isdigit():
        parts[0] = parse_amount(parts[0])
        if not parts[0]:
            return

    try:
        amount = int(parts[0])
        if amount < 10:
            return await msg.reply("⚠️ Мин. ставка: 10🍧")

        targets = parts[1:]
        valid: list[str | int] = []
        for t in targets:
            t = t.replace("–", "-")
            if t.isdigit() and 0 <= int(t) <= 36:
                valid.append(int(t))
            elif "-" in t:
                try:
                    start, end = map(int, t.split("-"))
                    if 0 <= start <= end <= 36:
                        valid.append(f"{start}-{end}")
                except:
                    pass
            elif t in ["red", "black", "even", "odd", "к", "ч", "евен", "одд"]:
                valid.append(t)

        if not valid:
            return await msg.reply("❌ Нет валидных ставок")

        total = amount * len(valid)
        bal = await get_balance(msg.from_user.id)
        if bal < total:
            return await msg.reply(f"❌ Недостаточно мороженого для {len(valid)} ставок 🍨")

        await update_balance(msg.from_user.id, -total)

        bets = roulette_bets.setdefault(chat_id, [])
        for t in valid:
            bets.append({
                "user_id": msg.from_user.id,
                "amount": amount,
                "target": t
            })

        await msg.reply(f"✅ Принято {len(valid)} ставок по {amount}🍧. Пиши 'го' для запуска! 🎰")

    except Exception:
        logging.exception("Ошибка в parse_bets")

@dp.message(F.text.lower() == "го")
async def go_roulette(msg: Message):
    chat_id = msg.chat.id
    bets = roulette_bets.get(chat_id)
    if not bets:
        return await msg.answer("❌ Сначала сделайте ставки! 🎰")

    await msg.answer("Запускаю рулетку...")
    await asyncio.sleep(3)

    result = random.randint(0, 36)
    color = "🔴" if result in RED_NUMS else "⚫" if result != 0 else "🟣"
    header = f"Рулетка: {result}{color}

"

    lines: list[str] = []
    winners_exist = False

    user_ids = {bet["user_id"] for bet in bets}
    async with async_session() as session:
        q = await session.execute(select(User).where(User.user_id.in_(user_ids)))
        users = {u.user_id: u for u in q.scalars().all()}

    for bet in bets:
        uid = bet["user_id"]
        user = users.get(uid)
        name = user.first_name if user else f"ID {uid}"
        amount = bet["amount"]
        target = bet["target"]

        prize = 0
        switch = {
            "одд": "odd",
            "евен": "even",
            "к": "🔴",
            "ч": "⚫"
        }

        if isinstance(target, int):
            if result == target:
                prize = amount * 36
        elif isinstance(target, str):
            target_lc = target.lower()
            if target_lc in ["odd", "одд"] and result % 2 == 1 and result != 0:
                prize = amount * 2
            elif target_lc in ["even", "евен"] and result % 2 == 0 and result != 0:
                prize = amount * 2
            elif target_lc in ["red", "к"] and result in RED_NUMS:
                prize = amount * 2
            elif target_lc in ["black", "ч"] and result in BLACK_NUMS and result != 0:
                prize = amount * 2
            elif "-" in target:
                try:
                    start, end = map(int, target.split("-"))
                    if start <= result <= end:
                        prize = amount * 3
                except:
                    pass

        if prize:
            winners_exist = True
            await update_balance(uid, prize)
            lines.append(f"{name} ставка {amount}🍧 выиграл {prize}🍧 на {switch.get(target, target)}")
        else:
            lines.append(f"{name} {amount}🍧 на {switch.get(target, target)}")

    roulette_bets.pop(chat_id, None)

    if not winners_exist:
        lines.append("Никто не выиграл")

    text = header + "
".join(lines)
    try:
        await msg.answer(text)
    except TelegramForbiddenError:
        pass
