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

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"
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
        "вќ„пёЏрџЌЁ Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ IceCream Casino! рџЌ§\n\n"
        "РћСЃРЅРѕРІРЅС‹Рµ РєРѕРјР°РЅРґС‹:\n"
        "рџЌ§ Р‘ - РїСЂРѕРІРµСЂРёС‚СЊ Р±Р°Р»Р°РЅСЃ\n"
        "рџ’Ј РњРёРЅС‹ 100 - РёРіСЂР° РІ РјРёРЅС‹\n"
        "рџЋ° 100 1 2 3 - СЃС‚Р°РІРєРё РЅР° СЂСѓР»РµС‚РєСѓ\n"
        "рџ”„ Рџ 1000 (РѕС‚РІРµС‚РѕРј) - РїРµСЂРµРґР°С‚СЊ РјРѕСЂРѕР¶РµРЅРѕРµ\n"
        "рџЏ† /С‚РѕРї - С‚РѕРї РёРіСЂРѕРєРѕРІ\n"
        "в„№пёЏ /info - РёРЅС„РѕСЂРјР°С†РёСЏ Рѕ Р±РѕС‚Рµ"
    )

@dp.message(Command("info"))
async def info(msg: Message):
    await msg.answer(
        "рџЌ¦ IceCream Casino Р‘РѕС‚\n"
        "рџ‘‘ Р’Р»Р°РґРµР»РµС†: @admin\n"
        "рџЋ® РРіСЂС‹:\n"
        "вЂў рџ’Ј РњРёРЅС‹ (РєРѕСЌС„С„РёС†РёРµРЅС‚С‹ РґРѕ x25)\n"
        "вЂў рџЋ° Р СѓР»РµС‚РєР° (РµРІСЂРѕРїРµР№СЃРєР°СЏ)\n"
        "рџ’Ћ Р’Р°Р»СЋС‚Р°: РњРѕСЂРѕР¶РµРЅРѕРµ рџЌ§"
    )

@dp.message(Command("С‚РѕРї"))
async def top(msg: Message):
    top_users = await get_top_users()
    text = "рџЏ† РўРѕРї РёРіСЂРѕРєРѕРІ РїРѕ РјРѕСЂРѕР¶РµРЅРѕРјСѓ рџЌ§:\n\n"
    for i, user in enumerate(top_users, start=1):
        username = f"@{user.username}" if user.username else f"t.me/openmessage?user_id={user.user_id}"
        text += f"{i}. [{user.first_name}]({username}) вЂ” {user.icecream}рџЌЁ\n"
    await msg.answer(text, parse_mode="markdown")

@dp.message(F.text.lower() == "Р±")
async def balance(msg: Message):
    bal = await get_balance(msg.from_user.id)
    await msg.answer(
        f"рџ‘¤ РРіСЂРѕРє: {msg.from_user.first_name}\n"
        f"рџ“¦ Р‘Р°Р»Р°РЅСЃ: {bal}рџЌ§\n"
        f"рџ†” ID: {msg.from_user.id}"
    )

@dp.message(Command(commands=["РІС‹РґР°С‚СЊ", "Р·Р°Р±СЂР°С‚СЊ", "Р±Р°РЅ"]))
async def admin_cmd(msg: Message, command: CommandObject):
    if msg.from_user.id not in ADMIN_ID or not msg.reply_to_message:
        return
    uid = msg.reply_to_message.from_user.id
    try:
        amount = int(msg.text.split()[1])
    except:
        await msg.reply("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°. РџСЂРёРјРµСЂ: /РІС‹РґР°С‚СЊ 1000")
        return

    if command.command == "РІС‹РґР°С‚СЊ":
        await update_balance(uid, amount)
        await msg.reply(f"вњ… Р’С‹РґР°РЅРѕ {amount}рџЌ§")
    elif command.command == "Р·Р°Р±СЂР°С‚СЊ":
        current = await get_balance(uid)
        amount = min(amount, current)
        if amount <= 0:
            await msg.reply("вќЊ РќРµС‡РµРіРѕ Р·Р°Р±РёСЂР°С‚СЊ")
            return
        await update_balance(uid, -amount)
        await msg.reply(f"вњ… Р—Р°Р±СЂР°РЅРѕ {amount}рџЌ§")
    elif command.command == "Р±Р°РЅ":
        banned_users.add(uid)
        await msg.reply("в›” РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ Р·Р°Р±Р°РЅРµРЅ")

@dp.message(F.text.lower().startswith("РјРёРЅС‹"))
async def mines(msg: Message):
    uid = msg.from_user.id
    
    if msg.from_user.id in banned_users:
        return
    try:
        amount = int(msg.text.split()[1])
        if amount < 10:
            raise ValueError
    except:
        await msg.reply("вљ пёЏ РџСЂРёРјРµСЂ: РјРёРЅС‹ 100 (РјРёРЅ. СЃС‚Р°РІРєР° 10рџЌ§)")
        return

    balance = await get_balance(msg.from_user.id)
    if balance < amount:
        await msg.answer("вќЊ РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РјРѕСЂРѕР¶РµРЅРѕРіРѕ! рџЌЁ")
        return

    await update_balance(msg.from_user.id, -amount)
    games[uid] = {
        "mines": random.sample(range(25), 3),
        "opened": [],
        "bet": amount,
        "step": 0
    }
    
    markup = build_mine_keyboard(uid)
    sent = await msg.answer("рџ’Ј РРіСЂР° РЅР°С‡Р°Р»Р°СЃСЊ! Р’С‹Р±РµСЂРё РєР»РµС‚РєСѓ:", reply_markup=markup)

def build_mine_keyboard(uid: int) -> InlineKeyboardMarkup:
    game = games.get(uid)
    if not game:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    keyboard: list[list[InlineKeyboardButton]] = []
    for i in range(5):
        row: list[InlineKeyboardButton] = []
        for j in range(5):
            idx = i * 5 + j
            label = "вќ”" if idx not in game["opened"] else "рџџў"
            row.append(
                InlineKeyboardButton(text=label, callback_data=f"open_{idx}")
            )
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(text="рџЏЃ Р—Р°Р±СЂР°С‚СЊ РІС‹РёРіСЂС‹С€ рџЌ§", callback_data="take")
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
        await call.message.edit_text("рџ’Ґ РўС‹ РїРѕРґРѕСЂРІР°Р»СЃСЏ РЅР° РјРёРЅРµ! рџљ«")
        games.pop(uid, None)
        return
    
    game["opened"].append(idx)
    game["step"] += 1
    
    if game["step"] >= len(COEFFS):
        win = int(game["bet"] * COEFFS[-1])
        await update_balance(uid, win)
        await call.message.edit_text(f"рџЋ‰ РџРѕР»РЅС‹Р№ РїСЂРѕС…РѕРґ! +{win}рџЌ§")
        games.pop(uid, None)
        return
    
    text = f"рџ”Ќ РћС‚РєСЂС‹С‚Рѕ РєР»РµС‚РѕРє: {game['step']} | РљРѕСЌС„: x{COEFFS[game['step']-1]}"
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
        await call.message.edit_text("рџ”„ РЎС‚Р°РІРєР° РІРѕР·РІСЂР°С‰РµРЅР° рџЌЁ")
        return
    win = int(g["bet"] * COEFFS[g["step"]-1])
    await update_balance(uid, win)
    del games[uid]
    await call.message.edit_text(f"рџ’° Р’С‹РёРіСЂС‹С€: {win}рџЌ§")

@dp.message(F.text.lower() == "РіРѕ")
async def go_roulette(msg: Message):
    chat_id = msg.chat.id
    bets = roulette_bets.get(chat_id)
    if not bets:
        return await msg.answer("вќЊ РЎРЅР°С‡Р°Р»Р° СЃРґРµР»Р°Р№С‚Рµ СЃС‚Р°РІРєРё! рџЋ°")

    sent = await msg.answer_animation(
        "CgACAgIAAxkBAAICVGgyo8fx8r0-BW034uQ30js0atY1AAICWQAC96p5SC81RvIZJygENgQ"
    )
    await asyncio.sleep(5)
    await sent.delete()

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

    if not winners_exist:
        lines.append("РќРёРєС‚Рѕ РЅРµ РІС‹РёРіСЂР°Р»")
    
    text = header + "\n".join(lines)
    try:
        await msg.answer(text)
    except TelegramForbiddenError:
        pass

@dp.message(F.text.lower().split()[0] == "Рї")
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
        await msg.reply("вљ пёЏ РџСЂРёРјРµСЂ: Рџ 100 (РѕС‚РІРµС‚РѕРј РЅР° СЃРѕРѕР±С‰РµРЅРёРµ)")
        return

    from_uid = msg.from_user.id
    to_user = msg.reply_to_message.from_user
    if from_uid == to_user.id:
        await msg.reply("вќЊ РќРµР»СЊР·СЏ РїРµСЂРµРґР°С‚СЊ СЃР°РјРѕРјСѓ СЃРµР±Рµ рџљ«")
        return

    if (await get_balance(from_uid)) < amount:
        await msg.reply("вќЊ РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РјРѕСЂРѕР¶РµРЅРѕРіРѕ рџЌЁ")
        return

    await update_balance(from_uid, -amount)
    await update_balance(to_user.id, amount)
    await msg.reply(f"вњ… РџРµСЂРµРґР°РЅРѕ {amount}рџЌ§ РёРіСЂРѕРєСѓ {to_user.first_name}")

@dp.message(Command("СЂР°СЃСЃС‹Р»РєР°"))
async def broadcast(msg: Message):
    if msg.from_user.id not in ADMIN_ID:
        return
    text = msg.text.split(" ", 1)[1] if " " in msg.text else ""
    if not text:
        await msg.reply("вќЊ РЈРєР°Р¶РёС‚Рµ С‚РµРєСЃС‚ СЂР°СЃСЃС‹Р»РєРё")
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    success = 0
    for user in users:
        try:
            await bot.send_message(user.user_id, f"рџ“ў Р Р°СЃСЃС‹Р»РєР° РѕС‚ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° вќ„пёЏрџЌ§\n\n{text}")
            success += 1
        except:
            continue
    await msg.reply(f"вњ… Р Р°СЃСЃС‹Р»РєР° РѕС‚РїСЂР°РІР»РµРЅР° {success} РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРј рџЌ¦")

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
            t = t.replace("вЂ“", "-")  # РЅР° СЃР»СѓС‡Р°Р№ РґР»РёРЅРЅРѕРіРѕ С‚РёСЂРµ
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

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())