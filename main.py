import asyncio
import datetime
import functools
import logging
import random
from aiogram.utils.exceptions import ChatAdminRequired
import re
from aiogram.utils.exceptions import UserIsAnAdministratorOfTheChat
import sqlite3
import time
from asyncio import sleep
from collections import defaultdict
import pyqiwip2p
from app import create_inline_keyboard, check_payment, add_donate_coins
from datetime import datetime, timedelta
from functools import wraps
from random import randint
import requests
import json
import aioschedule
import aiogram
import pytz
from aiogram import executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.callback_data import CallbackData
from aiogram.types import (ContentType, InlineKeyboardButton,
                           InlineKeyboardMarkup, ParseMode)
from aiogram.types.chat_member import ChatMemberStatus
from aiogram.utils.exceptions import Throttled
from aiogram.utils.markdown import text, escape_md
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

import chats
import config
import users



class ChRass(StatesGroup):
    msg = State()


class Rass(StatesGroup):
    msg = State()


class Quest(StatesGroup):
    msg = State()


class DonateState(StatesGroup):
    EnteringAmount = State()
    EnteringAmountCrypto = State()
    ChoosingCurrency = State()

class BankStates(StatesGroup):
    PUT_BANK = State()
    WITHDRAW_BANK = State()
    PUT_DEPOSIT = State()
    WITHDRAW_DEPOSIT = State()


class Answer(StatesGroup):
    text = State()


bot = aiogram.Bot(config.bot_token, parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.ERROR)

casino_results = []
async def update_users():
    query1 = "UPDATE users SET deposit = deposit + (deposit * user_percent * 0.01);"
    query2 = "UPDATE users SET limit_spent = 0;"
    
    execute_sql(query1)
    await asyncio.sleep(1)
    execute_sql(query2)
async def scheduler():
    aioschedule.every(6).hours.do(update_users)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)
def start_bot(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        message = None
        for arg in args:
            if isinstance(arg, types.Message):
                message = arg
                break

        if not message:
            raise ValueError("Message object not found in arguments")

        users.cursor.execute("SELECT id FROM users WHERE id = ?", (message.from_user.id,))
        if not users.cursor.fetchone():
            now = datetime.now()
            users_cursor = users.cursor.execute(f"SELECT * FROM users ORDER BY user_id DESC")
            uid = 1000
            for user in users_cursor:
                uid += 1
            time_dice = current_date = datetime.now() - timedelta(seconds=18000)
            current = current_date.time()
            regdata = now.strftime("%d.%m.%Y")
            ttime = current.strftime('%H:%M:%S')
            bio = "Не установлено..."

            users.cursor.execute(
                "INSERT INTO users VALUES("
                "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (
                    uid, message.from_user.id, message.from_user.first_name, message.from_user.username,
                    "Пользователь", 300000, 600000000000000, 0, 0, 0, 0, 0, 0, 0, 0, 0, regdata, ttime, 0, bio, 0, 1,
                    "00:00:00", 0, "1970-01-01 00:00:00", 0, 150000000000000, 0, 8, 0, 0, "1970-01-01 00:00:00",
                    0, 0, 0, 0, False, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, "1970-01-01 00:00:00", 0, 0, 0, 0, 15, 0
                )
            )
            users.connect.commit()

        return await func(*args, **kwargs)

    return wrapper


def rate_limit(limit, key=None):
    def decorator(func):
        setattr(func, 'throttling_rate_limit', limit)
        if key:
            setattr(func, 'throttling_key', key)
        return func

    return decorator


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit=0, key_prefix='antiflood_'):
        self.rate_limit = limit
        self.prefix = key_prefix
        super(ThrottlingMiddleware, self).__init__()

    async def on_process_message(self, message, data):
        handler = current_handler.get()
        dispatcher = Dispatcher.get_current()

        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_message"

        if limit <= 0:
            return

        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            await self.message_throttled(message, t)
            raise CancelHandler()

    async def message_throttled(self, message, throttled):
        handler = current_handler.get()

        if handler:
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            key = f"{self.prefix}_message"

        if throttled.exceeded_count <= 2:
            await message.reply('❎ | Не спамь!')


def not_in_black_list(func):
    @wraps(func)
    async def wrapper(update, *args, **kwargs):
        if isinstance(update, types.Message):
            user_id = update.from_user.id
        elif isinstance(update, types.CallbackQuery):
            user_id = update.from_user.id
        else:
            return await func(update, *args, **kwargs)

        users.cursor.execute("SELECT black_list FROM users WHERE id=?", (user_id,))
        result = users.cursor.fetchone()
        if result:
            user_in_black_list = result[0]
            if user_in_black_list:
                return
        return await func(update, *args, **kwargs)

    return wrapper


payment_amounts = defaultdict(int)


async def execute_sql_command(message: types.Message, command: str):
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute(command)
        conn.commit()
        conn.close()
        await message.reply("Выполнено ✅", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.reply(f"Не выполнено ⛔\nОшибка: {e}", parse_mode=ParseMode.MARKDOWN)


async def on_command_sql(message: types.Message):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        status = cursor.execute("SELECT status from users where id = ?", (message.from_user.id,)).fetchone()

    user_id = message.from_user.id

    if str(status) == "Создатель бота" or user_id == config.owner:
        if len(message.text.split()) > 1:
            sql_command = message.text.split(" ", 1)[1]
            await execute_sql_command(message, sql_command)
        else:
            await message.reply("Пожалуйста, укажите SQL-команду после /sql.")
    else:
        await message.reply("У вас нет доступа к этой команде, ваш статус должен быть Создатель бота")
async def on_startup(_):
    asyncio.create_task(scheduler())

dp.register_message_handler(on_command_sql, Command("sql"))



@dp.message_handler(lambda message: message.text.lower().startswith('кусь'))
async def kuss(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"🐶😻 | {name1} укусил {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nИ добавил: {additional_text}"
    
    await message.answer(response)
    

@dp.message_handler(lambda message: message.text.lower().startswith('поцеловать'))
async def kisslovs(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"😘💋| {name1} поцеловал {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nПрошептав: {additional_text}"
    
    await message.answer(response)
    
   
@dp.message_handler(lambda message: message.text.lower().startswith('отдаться'))
async def kisss(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"🥵🔞| {name1} страстно отдался {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nОн кричал: {additional_text}"
    
    await message.answer(response)
    
    
@dp.message_handler(lambda message: message.text.lower().startswith('раб'))
async def rab(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"⛓| {name1} забрал в рабство {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nПоследнее что он слышал: {additional_text}"
    
    await message.answer(response)    
   
@dp.message_handler(lambda message: message.text.lower().startswith('убить'))
async def smert(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"💀| {name1} убил {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nПоследнее что он слышал: {additional_text}"
    
    await message.answer(response)       
    
@dp.message_handler(lambda message: message.text.lower().startswith('избить'))
async def izbet(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"🤕💀 | {name1} избил {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nДо отключки последним {name2} слышал: {additional_text}"
    
    await message.answer(response)           
    
@dp.message_handler(lambda message: message.text.lower().startswith('отлизать'))
async def otlis(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"👅 | {name1} отлизал у {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nВ процессе он кричал: {additional_text}"
    
    await message.answer(response)   
    
            
@dp.message_handler(lambda message: message.text.lower().startswith('отсосать'))
async def otis(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"🍆🥵 | {name1} отсосал у {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nВ процессе он кричал: {additional_text}"
    
    await message.answer(response)           
    
                        
@dp.message_handler(lambda message: message.text.lower().startswith('пиво'))
async def otipivos(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"🍻 | {name1} бухнул с {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nА так-же, вставил свои три копейки: {additional_text}"
    
    await message.answer(response)            
    

@dp.message_handler(lambda message: message.text.lower().startswith('погладить'))
async def wllsb(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"💓 | {name1} погладил {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\nСказав: {additional_text}"
    
    await message.answer(response)   
    
@dp.message_handler(lambda message: message.text.lower().startswith('послать'))
async def wllsb(message: types.Message):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, ответьте на сообщение, чтобы использовать эту команду.")
        return

    user1 = message.from_user
    user2 = message.reply_to_message.from_user
    
    name1 = user1.first_name
    name2 = user2.first_name
    
    response = f"🤬 | {name1} далеко послал {name2}"

    if len(message.text.split()) > 1:
        additional_text = ' '.join(message.text.split()[1:])
        response += f"\n#$!@: {additional_text}"
    
    await message.answer(response)                  

@dp.message_handler(lambda message: message.text.lower().startswith('рп'))
async def handle_rp_command(message: types.Message):
    respoonse = "Список рп команд:\n\n" \
               "Поцеловать 💋\n" \
               "Убить 💀\n" \
               "Пиво 🍻\n" \
               "Раб ⛓\n" \
               "Кусь 🐶\n" \
               "Отдаться 💘\n" \
               "Отсосать 🔞\n" \
               "Отлизать 🔞\n" \
               "Погладить 🥰\n" \
               "Избить 🤬\n" \
               "Послать 🤬"

    await message.reply(respoonse)

@dp.message_handler(
    lambda t: t.text.startswith("промо создать") or t.text.startswith("Промо создать") or t.text.startswith(
        "создать промо") or t.text.startswith("Создать промо"))
@not_in_black_list
@start_bot
async def startswith(message):
    user_status = users.cursor.execute(f"SELECT status FROM users WHERE id = {message.from_user.id}").fetchone()
    user_status = user_status[0]
    user_name = users.cursor.execute(f"SELECT name from users where id = {message.from_user.id}").fetchone()
    balance = users.cursor.execute(f"SELECT balance from users where id = {message.from_user.id}").fetchone()
    balance = round(int(balance[0]))
    balance2 = '{:,}'.format(balance).replace(',', '.')
    user_name = user_name[0]
    try:
        name = message.text.split()[2]
        akt = int(message.text.split()[3])
        dengi5 = message.text.split()[4]
    except:
        if user_status != "Создатель бота":
            return
        else:
            await message.answer(f'❗️Использовать: промо создать [имя] [количество акт.] [сумма (на одного)]')
    users.cursor.execute(f"SELECT promo_name FROM promiki WHERE promo_name = '{name}'")
    akt2 = '{:,}'.format(akt).replace(',', '.')
    dengi4 = (dengi5).replace(' ', '').replace('k', '000').replace('е', 'e').replace('к', '000').replace(',',
                                                                                                         '').replace(
        '.', '').replace("₽", "").replace('м', '000000').replace('m', '000000')
    dengi3 = float(dengi4)
    dengi = int(dengi3)
    denfi = int(dengi * akt)
    denfi2 = '{:,}'.format(denfi).replace(',', '.')
    dengi2 = '{:,}'.format(dengi).replace(',', '.')
    if users.cursor.fetchone() != None:
        return await message.answer(f'Имя промокода "{name}" занято.')
    if akt < 2:
        return await message.answer(f'❌ Извини, но нельзя создавать промокоды, где количество активаций 1')
    if dengi < 100:
        return await message.answer(
            f'❌ Извини, но нельзя создавать промокоды, где на одного пользователя дают: <code>100</code>₽')
    if user_status == "Создатель бота" or user_status == "Особый Администратор":
        users.cursor.execute(f"INSERT INTO promiki VALUES ({message.from_user.id}, '{name}', {dengi}, {akt}, 0)")
        users.connect.commit()
        return await message.answer(
            f'✔️ Вы успешно создали промокод: «<code>{name}</code>»\n✅ Количество активаций: <code>{akt2}</code>\n👥 На одного пользователя: <code>{dengi2}</code>$\n🧾 С баланса было снято: <code>{denfi2}</code>₽')


@dp.message_handler(lambda t: t.text.startswith("Промо") or t.text.startswith("промо"))
@not_in_black_list
@start_bot
async def startswith(message):
    channel_id = -1001600332618

    try:
        chat_member = await bot.get_chat_member(channel_id, message.from_user.id)
    except:
        return await message.answer(
            "❌ Не удалось проверить вашу подписку на канал. Пожалуйста, попробуйте еще раз позже.")

    if chat_member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
        return await message.answer(
            "❌ 😔 Ошибка! Для использования промокода необходима подписка на канал @mgldev 🎮💡 Подписывайтесь, чтобы получить доступ к эксклюзивным предложениям!")

    try:
        vvod = message.text.split()[1]
    except:
        return await message.answer(f'❌ Вы не ввели имя промокода')

    user_exists = users.cursor.execute("SELECT * FROM users WHERE id = ?", (message.from_user.id,)).fetchone()

    if not user_exists:
        return await message.answer("❌ Вы не зарегистрированы. Пожалуйста, напишите команду /start для регистрации.")

    promo_exists = users.cursor.execute("SELECT promo_name FROM promiki WHERE promo_name = ?", (vvod,)).fetchone()

    if not promo_exists:
        return await message.answer('❌ Данного промокода не существует.')

    promo_activated = users.cursor.execute("SELECT activation FROM promo WHERE user_id = ? AND promo_name = ?",
                                           (message.from_user.id, vvod)