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
from sqlalchemy import BigInteger, String, select, update
from sqlalchemy.exc import IntegrityError

TOKEN = "7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U"
ADMIN_ID = [6359584002, 5419078908]

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
                    await session.execute(update(User).where(User.user_id == event.from_user.id).values(username=event.from_user.username, first_name=event.from_user.first_name))
                
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
    text = "🏆 Топ игроков по мороженому 🍧:\n\n"
    for i, user in enumerate(top_users, start=1):
        username = f"@{user.username}" if user.username else f"t.me/openmessage?user_id={user.user_id}"
        text += f"{i}. [{user.first_name}]({username}) — {user.icecream}🍨\n"
    await msg.answer(text, parse_mode="markdown")

@dp.message(F.text.lower() == "б")
async def balance(msg: Message):
    bal = await get_balance(msg.from_user.id)
    await msg.answer(
        f"👤 Игрок: {msg.from_user.first_name}\n"
        f"📦 Баланс: {bal}🍧\n"
        f"🆔 ID: {msg.from_user.id}"
    )

@dp.message(Command(commands=["выдать", "забрать", "бан"]))
async def admin_cmd(msg: Message, command: CommandObject):
    if msg.from_user.id not in ADMIN_ID or not msg.reply_to_message:
        return
    uid = msg.reply_to_message.from_user.id
    try:
        amount = int(msg.text.split()[1])
    except:
        await msg.reply("❌ Ошибка формата. Пример: /выдать 1000")
        return

    if command.command == "выдать":
        await update_balance(uid, amount)
        await msg.reply(f"✅ Выдано {amount}🍧")
    elif command.command == "забрать":
        current = await get_balance(uid)
        amount = min(amount, current)
        if amount <= 0:
            await msg.reply("❌ Нечего забирать")
            return
        await update_balance(uid, -amount)
        await msg.reply(f"✅ Забрано {amount}🍧")
    elif command.command == "бан":
        banned_users.add(uid)
        await msg.reply("⛔ Пользователь забанен")

@dp.message(F.text.lower().startswith("мины"))
async def mines(msg: Message):
    uid = msg.from_user.id
    
    if msg.from_user.id in banned_users:
        return
    try:
        amount = int(msg.text.split()[1])
        if amount < 10:
            raise ValueError
    except:
        await msg.reply("⚠️ Пример: мины 100 (мин. ставка 10🍧)")
        return

    balance = await get_balance(msg.from_user.id)
    if balance < amount:
        await msg.answer("❌ Недостаточно мороженого! 🍨")
        return

    await update_balance(msg.from_user.id, -amount)
    games[uid] = {
        "mines": random.sample(range(25), 3),
        "opened": [],
        "bet": amount,
        "step": 0
    }
    
    markup = build_mine_keyboard(uid)
    sent = await msg.answer("💣 Игра началась! Выбери клетку:", reply_markup=markup)

def build_mine_keyboard(uid: int) -> InlineKeyboardMarkup:
    game = games.get(uid)
    if not game:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    keyboard: list[list[InlineKeyboardButton]] = []
    for i in range(5):
        row: list[InlineKeyboardButton] = []
        for j in range(5):
            idx = i * 5 + j
            label = "❔" if idx not in game["opened"] else "🟢"
            row.append(
                InlineKeyboardButton(text=label, callback_data=f"open_{idx}")
            )
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(text="🏁 Забрать выигрыш 🍧", callback_data="take")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.callback_query(F.data.startswith("open_"))
async def open_cell(call: CallbackQuery):
    uid = call.from_user.id
    game = games.get(uid)
    if not game:
        return

    idx = int(call.data.split("_")[1])
    if idx in game["mines"]:
        await call.message.edit_text("💥 Ты подорвался на мине! 🚫")
        games.pop(uid, None)
        return
    
    game["opened"].append(idx)
    game["step"] += 1
    
    if game["step"] >= len(COEFFS):
        win = int(game["bet"] * COEFFS[-1])
        await update_balance(uid, win)
        await call.message.edit_text(f"🎉 Полный проход! +{win}🍧")
        games.pop(uid, None)
        return
    
    text = f"🔍 Открыто клеток: {game['step']} | Коэф: x{COEFFS[game['step']-1]}"
    await call.message.edit_text(
        text,
        reply_markup=build_mine_keyboard(uid)
    )

@dp.callback_query(F.data == "take")
async def take_win(call: CallbackQuery):
    uid = call.from_user.id
    if uid not in games:
        return
    g = games[uid]
    if g["step"] == 0:
        await update_balance(uid, g["bet"])
        del games[uid]
        await call.message.edit_text("🔄 Ставка возвращена 🍨")
        return
    win = int(g["bet"] * COEFFS[g["step"]-1])
    await update_balance(uid, win)
    del games[uid]
    await call.message.edit_text(f"💰 Выигрыш: {win}🍧")

@dp.message(F.text.lower() == "го")
async def go_roulette(msg: Message):
    chat_id = msg.chat.id
    bets = roulette_bets.get(chat_id)
    if not bets:
        return await msg.answer("❌ Сначала сделайте ставки! 🎰")
    
    sent = await msg.answer_animation(
        "CgACAgIAAxkBAAICVGgyo8fx8r0-BW034uQ30js0atY1AAICWQAC96p5SC81RvIZJygENgQ"
    )
    await asyncio.sleep(5)
    await sent.delete()
    
    result = random.randint(0, 36)
    color = "🔴" if result in RED_NUMS else "⚫" if result != 0 else "🟣"
    header = f"Рулетка: {result}{color}\n\n"

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
        if isinstance(target, int):
            if result == target:
                prize = amount * 36
        elif (target == "odd" or target == "одд") and result % 2 == 1 and result != 0:
            prize = amount * 2
        elif (target == "even" or target == "евен") and result % 2 == 0 and result != 0:
            prize = amount * 2
        elif (target == "red" or target == "к") and result in RED_NUMS:
            prize = amount * 2
        elif (target == "black" or target == "ч") and result in BLACK_NUMS and result != 0:
            prize = amount * 2
        
        switch = {
            "одд": "odd",
            "евен": "even",
            "к": "🔴",
            "ч": "⚫"
        }
        
        if prize:
            winners_exist = True
            await update_balance(uid, prize)
            lines.append(f"{name} ставка {amount}🍧 выиграл {prize}🍧 на {switch.get(target, target)}")
        else:
            lines.append(f"{name} {amount}🍧 на {switch.get(target, target)}")

    roulette_bets.pop(chat_id, None)

    if not winners_exist:
        lines.append("Никто не выиграл")
    
    text = header + "\n".join(lines)
    try:
        await msg.answer(text)
    except TelegramForbiddenError:
        pass

@dp.message(F.text.lower().split()[0] == "п")
async def transfer(msg: Message):
    if not msg.reply_to_message:
        return
    try:
        amount = int(msg.text.split()[1]) if msg.text.split()[1].isdigit() else parse_amount(msg.text.split()[1])
        if not amount:
            return
        
        if amount < 1:
            raise ValueError
    except:
        await msg.reply("⚠️ Пример: П 100 (ответом на сообщение)")
        return

    from_uid = msg.from_user.id
    to_user = msg.reply_to_message.from_user
    if from_uid == to_user.id:
        await msg.reply("❌ Нельзя передать самому себе 🚫")
        return

    if (await get_balance(from_uid)) < amount:
        await msg.reply("❌ Недостаточно мороженого 🍨")
        return

    await update_balance(from_uid, -amount)
    await update_balance(to_user.id, amount)
    await msg.reply(f"✅ Передано {amount}🍧 игроку {to_user.first_name}")

@dp.message(Command("рассылка"))
async def broadcast(msg: Message):
    if msg.from_user.id not in ADMIN_ID:
        return
    text = msg.text.split(" ", 1)[1] if " " in msg.text else ""
    if not text:
        await msg.reply("❌ Укажите текст рассылки")
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    success = 0
    for user in users:
        try:
            await bot.send_message(user.user_id, f"📢 Рассылка от администратора ❄️🍧\n\n{text}")
            success += 1
        except:
            continue
    await msg.reply(f"✅ Рассылка отправлена {success} пользователям 🍦")

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
        valid: list[str|int] = []
        for t in targets:
            if t.isdigit() and 0 <= int(t) <= 36:
                valid.append(int(t))
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

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())