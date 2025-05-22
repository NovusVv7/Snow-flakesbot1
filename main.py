
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

users = {}
current_roulette_bets = {}  # Для хранения ставок каждого пользователя
current_mines = {}  # Для хранения состояния мин

START_BALANCE = 60000

# Функция для получения данных пользователя
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            'balance': START_BALANCE,
            'snowflakes': 0,
            'banned': False
        }
    return users[user_id]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"Привет! Добро пожаловать! Ваш баланс: {user['balance']} снежинок."
    )

# Команда /balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(f"Ваш баланс: {user['balance']} снежинок.")

# Команда /give
async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Используйте /give <айди> <количество>")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except:
        await update.message.reply_text("Некорректные параметры.")
        return
    giver = get_user(update.effective_user.id)
    if giver['balance'] < amount:
        await update.message.reply_text("Недостаточно снежинок.")
        return
    target = get_user(target_id)
    giver['balance'] -= amount
    target['snowflakes'] += amount
    await update.message.reply_text(f"Вы передали {amount} снежинок пользователю {target_id}.")

# Команда /бан
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ADMIN_ID:
        await update.message.reply_text("Нет прав.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте /ban <айди>")
        return
    user_id = int(context.args[0])
    user = get_user(user_id)
    user['banned'] = True
    await update.message.reply_text(f"Пользователь {user_id} забанен.")

# Обработка сообщений для автоматической ставки на рулетку
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user['banned']:
        return
    # Обработка команды "отмена"
    if "отмена" in text:
        if user_id in current_roulette_bets:
            del current_roulette_bets[user_id]
            await update.message.reply_text("Ваша ставка отменена.")
        if user_id in current_mines:
            del current_mines[user_id]
            await update.message.reply_text("Игра мин отменена.")

    # Игра "Мины" без /mine
    if "мины" in text:
        await start_mines(update, context)

# Запуск рулетки с автоматической ставкой
async def start_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    bet_amount = 20000
    if user['balance'] < bet_amount:
        await update.message.reply_text("Недостаточно снежинок для ставки.")
        return
    user['balance'] -= bet_amount
    # Заранее выбранные числа
    numbers = [2, 4, 6, 9, 14, 15, 17, 19, 20, 24, 25, 27, 29, 30, 33, 35]
    current_roulette_bets[update.effective_user.id] = {
        'amount': bet_amount,
        'numbers': numbers
    }
    await update.message.reply_text(
        f"Сделана ставка {bet_amount} снежинок на числа: {numbers}. Ждите вращения рулетки..."
    )
    # Вращение рулетки
    await spin_roulette(update, context)

# Вращение рулетки
async def spin_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = random.randint(0, 36)
    # Обработка ставок
    for user_id, bet in current_roulette_bets.items():
        user = get_user(user_id)
        if number in bet['numbers']:
            winnings = bet['amount'] * 35
            user['balance'] += winnings
            try:
                await context.bot.send_message(user_id, f"Выпало число: {number}! Вы выиграли {winnings} снежинок! Баланс: {user['balance']}")
            except:
                pass
        else:
            try:
                await context.bot.send_message(user_id, f"Выпало число: {number}. Вы проиграли ставку.")
            except:
                pass
    # Очистка ставок
    current_roulette_bets.clear()

# Игра "Мины"
async def start_mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user['balance'] < 5000:
        await update.message.reply_text("Недостаточно снежинок для игры.")
        return
    user['balance'] -= 5000
    mines = random.sample(range(1, 21), 3)  # 3 мины из 20
    current_mines[update.effective_user.id] = mines
    # Создаем клавиатуру для выбора
    keyboard = []
    for row in range(4):
        buttons = []
        for col in range(5):
            num = row * 5 + col + 1
            buttons.append(InlineKeyboardButton(str(num), callback_data=f"mine_{num}"))
        keyboard.append(buttons)
    await update.message.reply_text("Выберите ячейку, чтобы открыть:", reply_markup=InlineKeyboardMarkup(keyboard))

# Обработка нажатий на мины
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user['banned']:
        return
    if data.startswith('mine_'):
        cell = int(data.split('_')[1])
        if user_id not in current_mines:
            await query.edit_message_text("Игра мин не запущена.")
            return
        mines = current_mines[user_id]
        if cell in mines:
            user['balance'] -= 5000
            await query.edit_message_text(f"Мина! Вы потеряли 5000 снежинок. Баланс: {user['balance']}")
        else:
            user['balance'] += 15000
            await query.edit_message_text(f"Безопасно! Вы выиграли 15000 снежинок! Баланс: {user['balance']}")
        del current_mines[user_id]

# Обработка команд /roulette и /mine
async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "/roulette" in text:
        await start_roulette(update, context)
    elif "/mine" in text:
        await start_mines(update, context)

# Основная функция
async def main():
    application = ApplicationBuilder().token('YOUR_BOT_TOKEN').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("give", give))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"\/(roulette|mine)"), command_handler))

    await application.run_polling()

import asyncio
asyncio.run(main())
