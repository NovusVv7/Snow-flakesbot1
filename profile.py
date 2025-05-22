from aiogram import types
from aiogram.dispatcher.filters import Text
from database import get_user


async def handle_profile(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.reply("❗Ты не зарегистрирован в системе!\nНапиши /start")
        return

    user_id, username, balance, level, referrer_id = user
    profile_text = (
        f"😊 <b>Твой профиль</b>\n\n"
        f"🌟 <b>ID:</b> {user_id}\n"
        f"💰 <b>Баланс:</b> {balance} круннов\n"
        f"🔮 <b>Уровень:</b> {level}\n"
    )

    if referrer_id:
        referrer = get_user(referrer_id)
        referrer_name = referrer[1] if referrer else "Неизвестный"
        profile_text += f"🛐 <b>Пригласил:</b> {referrer_name}"

    await message.reply(profile_text, parse_mode="HTML")


async def handle_other_profile(message: types.Message):
    try:
        target_user_id = int(message.text.strip())
        user = get_user(target_user_id)

        if not user:
            await message.reply("❗Такого пользователя не существует.")
            return

        user_id, username, balance, level, referrer_id = user
        profile_text = (
            f"📄 <b>Профиль пользователя {username}</b>\n\n"
            f"🌟 <b>ID:</b> {user_id}\n"
            f"💰 <b>Баланс:</b> {balance} круннов\n"
            f"🔮 <b>Уровень:</b> {level}\n"
        )

        if referrer_id:
            referrer = get_user(referrer_id)
            referrer_name = referrer[1] if referrer else "Неизвестный"
            profile_text += f"🛐 <b>Пригласил:</b> {referrer_name}"

        await message.reply(profile_text, parse_mode="HTML")
    except ValueError:
        await message.reply("❗Неверный формат. Введите ID пользователя для просмотра.")

def add_experience(user_id: int, amount: int):
    """Начислить опыт игроку и проверить повышение уровня"""
    user = get_user(user_id)
    if not user:
        logging.warning(f"Пользователь с ID {user_id} не найден.")
        return

    current_exp = user.get('experience', 0) or 0
    new_exp = current_exp + amount
    update_experience(user_id, new_exp)

    user['experience'] = new_exp
    level_up = check_level_up(user)

    return level_up

def register_profile(dp):
    dp.register_message_handler(handle_profile, Text(equals="профиль", ignore_case=True), state="*")
    dp.register_message_handler(handle_other_profile, lambda msg: msg.text.isdigit(), state="*")
