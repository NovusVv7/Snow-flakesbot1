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

TOKEN = "Р’РђРЁ_РўРћРљР•Рќ_Р—Р”Р•РЎР¬"
ADMIN_ID = [123456789, 987654321]  # Р—Р°РјРµРЅРёС‚Рµ РЅР° СЃРІРѕРё ID

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
    if s.endswith("РєРє") or s.endswith("Рј"):
        num_part = s[:-2] if s.endswith("РєРє") else s[:-1]
        try:
            return int(float(num_part) * 1_000_000)
        except ValueError:
            return None
    if s.endswith("Рє"):
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
        "вќ„пёЏрџЌЁ Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ IceCream Casino! рџЌ§

"
        "РћСЃРЅРѕРІРЅС‹Рµ РєРѕРјР°РЅРґС‹:
"
        "рџЌ§ Р‘ - РїСЂРѕРІРµСЂРёС‚СЊ Р±Р°Р»Р°РЅСЃ
"
        "рџ’Ј РњРёРЅС‹ 100 - РёРіСЂР° РІ РјРёРЅС‹
"
        "рџЋ° 100 1 2 3 - СЃС‚Р°РІРєРё РЅР° СЂСѓР»РµС‚РєСѓ
"
        "рџ”„ Рџ 1000 (РѕС‚РІРµС‚РѕРј) - РїРµСЂРµРґР°С‚СЊ РјРѕСЂРѕР¶РµРЅРѕРµ
"
        "рџЏ† /С‚РѕРї - С‚РѕРї РёРіСЂРѕРєРѕРІ
"
        "в„№пёЏ /info - РёРЅС„РѕСЂРјР°С†РёСЏ Рѕ Р±РѕС‚Рµ"
    )

@dp.message(F.text.lower() == "Р±")
async def balance(msg: Message):
    bal = await get_balance(msg.from_user.id)
    await msg.answer(
        f"рџ‘¤ РРіСЂРѕРє: {msg.from_user.first_name}
"
        f"рџ“¦ Р‘Р°Р»Р°РЅСЃ: {bal}рџЌ§
"
        f"рџ†” ID: {msg.from_user.id}"
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
            return await msg.reply("вљ пёЏ РњРёРЅ. СЃС‚Р°РІРєР°: 10рџЌ§")

        targets = parts[1:]
        valid: list[str | int] = []
        for t in targets:
            t = t.replace("вЂ“", "-")
            if t.isdigit() and 0 <= int(t) <= 36:
                valid.append(int(t))
            elif "-" in t:
                try:
                    start, end = map(int, t.split("-"))
                    if 0 <= start <= end <= 36:
                        valid.append(f"{start}-{end}")
                except:
                    pass
            elif t in ["red", "black", "even", "odd", "Рє", "С‡", "РµРІРµРЅ", "РѕРґРґ"]:
                valid.append(t)

        if not valid:
            return await msg.reply("вќЊ РќРµС‚ РІР°Р»РёРґРЅС‹С… СЃС‚Р°РІРѕРє")

        total = amount * len(valid)
        bal = await get_balance(msg.from_user.id)
        if bal < total:
            return await msg.reply(f"вќЊ РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РјРѕСЂРѕР¶РµРЅРѕРіРѕ РґР»СЏ {len(valid)} СЃС‚Р°РІРѕРє рџЌЁ")

        await update_balance(msg.from_user.id, -total)

        bets = roulette_bets.setdefault(chat_id, [])
        for t in valid:
            bets.append({
                "user_id": msg.from_user.id,
                "amount": amount,
                "target": t
            })

        await msg.reply(f"вњ… РџСЂРёРЅСЏС‚Рѕ {len(valid)} СЃС‚Р°РІРѕРє РїРѕ {amount}рџЌ§. РџРёС€Рё 'РіРѕ' РґР»СЏ Р·Р°РїСѓСЃРєР°! рџЋ°")

    except Exception:
        logging.exception("РћС€РёР±РєР° РІ parse_bets")

@dp.message(F.text.lower() == "РіРѕ")
async def go_roulette(msg: Message):
    chat_id = msg.chat.id
    bets = roulette_bets.get(chat_id)
    if not bets:
        return await msg.answer("вќЊ РЎРЅР°С‡Р°Р»Р° СЃРґРµР»Р°Р№С‚Рµ СЃС‚Р°РІРєРё! рџЋ°")

    await msg.answer("Р—Р°РїСѓСЃРєР°СЋ СЂСѓР»РµС‚РєСѓ...")
    await asyncio.sleep(3)

    result = random.randint(0, 36)
    color = "рџ”ґ" if result in RED_NUMS else "вљ«" if result != 0 else "рџџЈ"
    header = f"Р СѓР»РµС‚РєР°: {result}{color}

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
            "РѕРґРґ": "odd",
            "РµРІРµРЅ": "even",
            "Рє": "рџ”ґ",
            "С‡": "вљ«"
        }

        if isinstance(target, int):
            if result == target:
                prize = amount * 36
        elif isinstance(target, str):
            target_lc = target.lower()
            if target_lc in ["odd", "РѕРґРґ"] and result % 2 == 1 and result != 0:
                prize = amount * 2
            elif target_lc in ["even", "РµРІРµРЅ"] and result % 2 == 0 and result != 0:
                prize = amount * 2
            elif target_lc in ["red", "Рє"] and result in RED_NUMS:
                prize = amount * 2
            elif target_lc in ["black", "С‡"] and result in BLACK_NUMS and result != 0:
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
            lines.append(f"{name} СЃС‚Р°РІРєР° {amount}рџЌ§ РІС‹РёРіСЂР°Р» {prize}рџЌ§ РЅР° {switch.get(target, target)}")
        else:
            lines.append(f"{name} {amount}рџЌ§ РЅР° {switch.get(target, target)}")

    roulette_bets.pop(chat_id, None)

    if not winners_exist:
        lines.append("РќРёРєС‚Рѕ РЅРµ РІС‹РёРіСЂР°Р»")

    text = header + "
".join(lines)
    try:
        await msg.answer(text)
    except TelegramForbiddenError:
        pass