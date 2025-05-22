from aiogram import executor
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from config import TOKEN
import logging
import asyncio 
from handlers import start, profile, promo, roulette, cancel, games, rocket, bonus, p_transfer, referral, mines, crypto, treasury
from level import level
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database import create_tables
from aiogram.utils.exceptions import RetryAfter

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

start.register_start(dp)
referral.register_handlers_referral(dp, bot)
treasury.register_handlers_treasury(dp, bot)
crypto.register_crypto(dp)
profile.register_profile(dp)
promo.register_promo(dp)
level.register_level_handler(dp)
roulette.register_roulette(dp)
cancel.register_cancel(dp)
mines.register_mines(dp)
games.register_games(dp)
rocket.register_rocket(dp)
bonus.register_bonus(dp)
p_transfer.register_transfer(dp)


print("="*90)
print(" " * 10 + "KRUIN INFINITY ЗАПУЩЕН")
print("="*90)

async def on_startup(dispatcher: Dispatcher):
    create_tables()
    logging.info("Бот запущен")

async def process_new_member(message: types.Message, bot: Bot):
    logging.info("process_new_member: ФУНКЦИЯ ВЫЗВАНА!")
    chat_id = message.chat.id
    logging.info(f"process_new_member: Новый участник добавлен в чат {chat_id}")

    if not message.new_chat_members:
        logging.warning(f"process_new_member: Нет информации о новых участниках в чате {chat_id}.")
        return

    logging.info(f"process_new_member: Новые участники: {message.new_chat_members}")

    settings = database.get_chat_settings(chat_id)
    if not settings:
        database.create_chat_settings(chat_id)
        settings = database.get_chat_settings(chat_id)

    logging.info(f"process_new_member: Настройки чата: {settings}")

    if not settings or not settings['is_active']:
        logging.info(f"process_new_member: Казна выключена или не настроена в чате {chat_id}. Начисление награды пропущено.")
        return

    reward_per_invite = settings['reward_per_invite']
    logging.info(f"process_new_member: Награда за приглашение: {reward_per_invite}")

    if reward_per_invite <= 0:
        logging.info(f"process_new_member: Награда за приглашение не установлена в чате {chat_id}. Начисление награды пропущено.")
        return

    if message.from_user:
        inviter_id = message.from_user.id
        inviter_name = message.from_user.first_name
        logging.info(f"process_new_member: Пригласивший: ID={inviter_id}, Имя={inviter_name}")
    else:
        logging.warning(f"process_new_member: Не удалось определить пригласившего в чате {chat_id}.")
        return

    for new_member in message.new_chat_members:
        if new_member.id == bot.id:
            logging.info(f"process_new_member: Бот добавлен в чат, награда не начисляется.")
            continue

        database.add_invite(inviter_id, inviter_name, chat_id)
        logging.info(f"process_new_member: Добавлена запись о приглашении пользователя {inviter_id} пользователем {new_member.id}.")

        total_reward = reward_per_invite

        treasury_balance = database.get_treasury_balance(chat_id)
        logging.info(f"process_new_member: Баланс казны: {treasury_balance}")

        if treasury_balance < total_reward:
            await bot.send_message(chat_id, "Недостаточно средств в казне для выплаты награды за приглашения.")
            logging.info(f"process_new_member: Недостаточно средств в казне чата {chat_id} для выплаты награды за приглашения.")
            return

        database.deposit_to_treasury(chat_id, -total_reward)
        logging.info(f"process_new_member: Выдано {total_reward} из казны.")

        database.clear_invites(chat_id, inviter_id)
        logging.info(f"process_new_member: Очищен список приглашений для пользователя {inviter_id}.")

        text = f"<a href=\"tg://user?id={inviter_id}\">{inviter_name}</a> пригласил пользователя и получил награду {total_reward} KRUNN"

        try:
            await bot.send_message(chat_id, text, parse_mode=types.ParseMode.HTML)
            logging.info(f"process_new_member: Пользователю {inviter_name} начислена награда {total_reward} KRUNN за приглашения в чате {chat_id}")
            await asyncio.sleep(0.2) 

        except RetryAfter as e:
            logging.warning(f"Флуд контроль нарушился в process_new_member. Попробуй снова через {e.timeout} секунд.")
            await asyncio.sleep(e.timeout)
            try:
                await bot.send_message(chat_id, text, parse_mode=types.ParseMode.HTML)
            except Exception as ex:
                logging.error(f"Ошибка отправить сообщение снова : {ex}")


        except Exception as e:
            logging.error(f"process_new_member: Ошибка при отправке сообщения: {e}")

dp.register_message_handler(lambda message: process_new_member(message, bot), content_types=types.ContentTypes.NEW_CHAT_MEMBERS)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
     
