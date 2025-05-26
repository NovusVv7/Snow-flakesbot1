import asyncio
import random
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, BaseMiddleware, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base, mapped_column, Mapped
from sqlalchemy import BigInteger, String, select, update, Column, Integer
from sqlalchemy.exc import IntegrityError

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"
ADMIN_ID = [6359584002]  # Ваши ID админов

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

engine = create_async_engine("sqlite+aiosqlite:///bot.db", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=True)
Base = declarative_base()

# Модели данных
class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)
    icecream: Mapped[int] = mapped_column(BigInteger, default=1000)

class Promo(Base):
    __tablename__ = "promo"
    id = Column(Integer, primary_key=True)
    owner_id = Column(BigInteger)
    promo_name = Column(String)
    amount = Column(Integer)
    max_activations = Column(Integer)
    activations = Column(Integer, default=0)

# Игровые переменные
games = {}
roulette_bets: dict[int, list[dict]] = {}
banned_users = set()
COEFFS = [1.7, 2.5, 3, 4.67, 25]
RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMS = set(range(1, 37)) - RED_NUMS

# Мидлварь для автоматического добавления пользователей
class AddUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        if event.from_user:
            await add_user(event.from_user)
            
            async with async_session() as session:
                user = await session.get(User, event.from_user.id)
                
                if user:
                    await session.execute(update(User).where(User.user_id == event.from_user.id).values(
                        username=event.from_user.username, 
                        first_name=event.from_user.first_name
                    ))
                
        return await handler(event, data)

dp.message.middleware(AddUserMiddleware())

# Утилиты
async def add_user(user):
    async with async_session() as session:
        try:
            session.add(User(
                user_id=user.id, 
                username=user.username, 
                first_name=user.first_name
            ))
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

async def get_top_users():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .order_by(User.icecream.desc())
            .limit(10)
        )
        return result.scalars().all()

# Команды
@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer(
        "❄️🍨 Добро пожаловать в IceCream World! 🍧\n\n"
        "Основные команды:\n"
        "🍧 /б - проверить баланс\n"
        "💣 /мины 100 - игра в мины\n"
        "🎰 /рулетка 100 1 2 3 - ставки на рулетку\n"
        "🔄 /п 1000 (ответом) - передать мороженое\n"
        "🏆 /топ - топ игроков\n"
        "💝 /промо [код] - активировать промокод\n"
        "ℹ️ /info - информация о боте"
    )

@dp.message(Command("info"))
async def info(msg: Message):
    await msg.answer(
        "🍦 IceCream World Бот\n"
        "👑 Владелец: @admin\n"
        "🎮 Игры:\n"
        "• 💣 Мины (коэффициенты до x25)\n"
        "• 🎰 Рулетка (европейская)\n"
        "💎 Валюта: Мороженое 🍧"
    )

@dp.message(Command("топ"))
async def top(msg: Message):
    top_users = await get_top_users()
    text = "🏆 Топ игроков по мороженому 🍧:\n\n"
    for i, user in enumerate(top_users, start=1):
        username = f"@{user.username}" if user.username else f"ID {user.user_id}"
        text += f"{i}. {user.first_name} ({username}) — {user.icecream}🍨\n"
    await msg.answer(text)

@dp.message(Command("б"))
async def balance(msg: Message):
    bal = await get_balance(msg.from_user.id)
    await msg.answer(
        f"👤 Игрок: {msg.from_user.first_name}\n"
        f"📦 Баланс: {bal}🍧\n"
        f"🆔 ID: {msg.from_user.id}"
    )

# RP-команды
@dp.message(lambda message: message.text.lower().startswith('кусь'))
async def kuss(message: Message):
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение!")
    user1 = message.from_user.first_name
    user2 = message.reply_to_message.from_user.first_name
    await message.answer(f"🐶😻 | {user1} укусил {user2}")

@dp.message(lambda message: message.text.lower().startswith('поцеловать'))
async def kisslovs(message: Message):
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение!")
    user1 = message.from_user.first_name
    user2 = message.reply_to_message.from_user.first_name
    await message.answer(f"😘💋| {user1} поцеловал {user2}")

@dp.message(lambda message: message.text.lower().startswith('рп'))
async def rp_list(message: Message):
    response = (
        "Список RP-команд:\n\n"
        "Поцеловать 💋\nУбить 💀\nРаб ⛓\nКусь 🐶\nПогладить 🥰\nИзбить 🤬"
    )
    await message.answer(response)

# Промокоды
@dp.message(Command("промо_создать"))
async def create_promo(msg: Message, command: CommandObject):
    if msg.from_user.id not in ADMIN_ID:
        return
    
    try:
        _, name, amount, activations = command.args.split()
        amount = int(amount)
        activations = int(activations)
    except:
        return await msg.answer("Использование: /промо_создать [имя] [сумма] [активации]")

    async with async_session() as session:
        promo = Promo(
            owner_id=msg.from_user.id,
            promo_name=name,
            amount=amount,
            max_activations=activations
        )
        session.add(promo)
        await session.commit()
    
    await msg.answer(f"🍦 Промокод создан!\nИмя: {name}\nНаграда: {amount}🍧\nАктиваций: {activations}")

@dp.message(Command("промо"))
async def use_promo(msg: Message, command: CommandObject):
    if not command.args:
        return await msg.answer("Укажите промокод")
    
    promo_name = command.args.strip()
    
    async with async_session() as session:
        promo = await session.execute(select(Promo).where(Promo.promo_name == promo_name))
        promo = promo.scalar()
        
        if not promo:
            return await msg.answer("❌ Неверный промокод!")
        
        if promo.activations >= promo.max_activations:
            return await msg.answer("❌ Промокод закончился!")
        
        # Проверка на повторную активацию
        activated = await session.execute(select(UserPromo).where(
            UserPromo.user_id == msg.from_user.id,
            UserPromo.promo_name == promo_name
        ))
        if activated.scalar():
            return await msg.answer("❌ Вы уже активировали этот промокод!")
        
        # Начисление награды
        await update_balance(msg.from_user.id, promo.amount)
        promo.activations += 1
        session.add(UserPromo(user_id=msg.from_user.id, promo_name=promo_name))
        await session.commit()
    
    await msg.answer(f"🎉 Промокод активирован! Получено {promo.amount}🍧")

# Игры (мины, рулетка, перевод) остаются без изменений из второго кода
# ... (вставить код игр из предыдущего ответа)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())