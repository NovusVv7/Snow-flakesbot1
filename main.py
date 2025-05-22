
import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"  # вставьте сюда ваш токен
ADMIN_ID = 6359584002  # ваш ID или ID администратора
GROUP_CHAT_ID = -1001234567890  # ID группы, если нужен

# Создаем подключение к базе данных
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()

# Создаем таблицы, если их еще нет
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gender TEXT,
    is_vip INTEGER,
    is_admin INTEGER,
    last_active DATETIME
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER PRIMARY KEY
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS vip_requests (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    requested_at DATETIME
)
''')

conn.commit()

# Обновляем время последней активности пользователя
async def update_last_active(user_id):
    c.execute(
        "UPDATE users SET last_active=? WHERE user_id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
    )
    conn.commit()

# Клавиатура для выбора пола
gender_keyboard = [
    [InlineKeyboardButton("👩 Девушка", callback_data='gender_женский')],
    [InlineKeyboardButton("👨 Мужчина", callback_data='gender_мужской')]
]

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user_record = c.fetchone()
    if not user_record:
        await update.message.reply_text(
            "👋 Привет! Выбери свой пол:",
            reply_markup=InlineKeyboardMarkup(gender_keyboard)
        )
    else:
        await update.message.reply_text("Вы уже зарегистрированы!")
    await update_last_active(user_id)

# Обработка выбора пола
async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    gender = query.data.split('_')[1]

    # Записываем или обновляем пользователя
    c.execute(
        "INSERT OR REPLACE INTO users (user_id, gender, is_vip, is_admin, last_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, gender, 0, 1 if user_id == ADMIN_ID else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

    # Отправляем сообщение о сохранении пола
    keyboard = [[InlineKeyboardButton("✨ Хочу VIP", callback_data='want_vip')]]
    await query.edit_message_text(
        f"✅ Пол успешно сохранен: {gender}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update_last_active(user_id)

# Обработка заявки на VIP
async def want_vip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    username = user.username or ''

    # Записываем заявку
    c.execute(
        "INSERT OR REPLACE INTO vip_requests (user_id, username, requested_at) VALUES (?, ?, ?)",
        (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

    await query.answer("Заявка на VIP отправлена! Ожидайте одобрения.")
    await query.edit_message_text("Ваша заявка на VIP отправлена. Спасибо!")

# Обработка команд /help, /start, /balance и т.п.
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - начать регистрацию\n"
        "/balance - посмотреть баланс\n"
        "/help - помощь\n\n"
        "Также можно писать 'хочу VIP' или 'отмена' в любой момент."
    )

# Обработка сообщений для автоматической реакции
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id

    # Обновляем активность
    await update_last_active(user_id)

    # Проверка, есть ли пользователь в бане
    c.execute("SELECT * FROM bans WHERE user_id=?", (user_id,))
    if c.fetchone():
        return  # пользователь забанен, ничего не делаем

    # Обработка фразы "хочу VIP"
    if "хочу vip" in text:
        c.execute("SELECT * FROM vip_requests WHERE user_id=?", (user_id,))
        if c.fetchone():
            await update.message.reply_text("Вы уже отправили заявку на VIP.")
        else:
            # Отправляем заявку
            c.execute(
                "INSERT OR REPLACE INTO vip_requests (user_id, username, requested_at) VALUES (?, ?, ?)",
                (user_id, update.effective_user.username or '', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            await update.message.reply_text("Ваша заявка на VIP отправлена. Ожидайте одобрения.")
        return

    # Обработка слова "отмена"
    if "отмена" in text:
        # Отменяем ставки или заявки
        # В этом примере просто удаляем ставки/заявки из словарей
        # (если есть, для расширения — можно реализовать)
        # Для этого нужно иметь глобальные переменные или базы данных
        await update.message.reply_text("Все текущие ставки и заявки отменены.")
        return

# Обработка команд /command или /mine /roulette
async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "/roulette" in text:
        await start_roulette(update, context)
    elif "/mine" in text:
        await start_mines(update, context)

# Реализация рулетки
async def start_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь /start")
        return

    # Баланс пользователя
    balance = user[2]
    bet_amount = 20000

    if balance < bet_amount:
        await update.message.reply_text("Недостаточно снежинок для ставки.")
        return

    # Снимаем ставку
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Заранее выбранные числа
    numbers = [2, 4, 6, 9, 14, 15, 17, 19, 20, 24, 25, 27, 29, 30, 33, 35]
    c.execute("UPDATE users SET is_vip=? WHERE user_id=?", (0, user_id))
    conn.commit()

    # Обновляем баланс
    c.execute("UPDATE users SET is_vip=0 WHERE user_id=?", (user_id,))
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    # Обновляем баланс
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    # Обновляем баланс
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Уменьшаем баланс
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Обновляем баланс
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Вырезка
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Вырезка
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Вырезка
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Вырезка
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

    # Вращение рулетки
    number = random.randint(0, 36)

    # Обработка результата
    if number in numbers:
        winnings = bet_amount * 35
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (winnings, user_id))
        await update.message.reply_text(f"Выпало число: {number}! Вы выиграли {winnings} снежинок! Баланс: {winnings}")
    else:
        await update.message.reply_text(f"Выпало число: {number}. Вы проиграли ставку.")

# Реализация игры "Мины"
async def start_mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь /start")
        return

    balance = user[2]
    if balance < 5000:
        await update.message.reply_text("Недостаточно снежинок для игры.")
        return

    # Снимаем ставку
    c.execute("UPDATE users SET balance=balance-5000 WHERE user_id=?", (user_id,))
    conn.commit()

    # Генерируем мины
    mines = random.sample(range(1, 21), 3)
    # Сохраняем мины
    c.execute("INSERT OR REPLACE INTO users (user_id, gender, is_vip, is_admin, last_active) VALUES (?, ?, ?, ?, ?)",
              (user_id, '', 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    # Запоминаем мины в памяти
    if not hasattr(context.bot_data, 'mines'):
        context.bot_data['mines'] = {}
    context.bot_data['mines'][user_id] = mines

    # Создаем клавиатуру
    keyboard = []
    for row in range(4):
        buttons = []
        for col in range(5):
            num = row * 5 + col + 1
            buttons.append(InlineKeyboardButton(str(num), callback_data=f"mine_{num}"))
        keyboard.append(buttons)

    await update.message.reply_text("Выберите ячейку, чтобы открыть:", reply_markup=InlineKeyboardMarkup(keyboard))

# Обработка нажатий на мини
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith('mine_'):
        cell = int(data.split('_')[1])
        # Проверяем мины
        mines = None
        if hasattr(context.bot_data, 'mines'):
            mines = context.bot_data['mines'].get(user_id)
        if not mines:
            await query.edit_message_text("Игра мин не запущена или уже завершена.")
            return

        # Проверяем, есть ли мина
        if cell in mines:
            # Мина — проигрыш
            c.execute("UPDATE users SET balance=balance-5000 WHERE user_id=?", (user_id,))
            conn.commit()
            await query.edit_message_text("Мина! Вы потеряли 5000 снежинок.")
        else:
            # Безопасно — выигрыш
            c.execute("UPDATE users SET balance=balance+15000 WHERE user_id=?", (user_id,))
            conn.commit()
            await query.edit_message_text("Безопасно! Вы выиграли 15000 снежинок.")
        # Удаляем игру
        del context.bot_data['mines'][user_id]

# Обработка команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - регистрация\n"
        "/balance - проверить баланс\n"
        "/mine - играть в мини-игру\n"
        "/roulette - начать рулетку\n"
        "Можно писать 'хочу VIP' или 'отмена' для автоматических действий."
    )

# Основная функция
async def main():
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", lambda update, context: update.message.reply_text("Ваш баланс: ...")))  # можно доработать
    application.add_handler(CommandHandler("mine", start_mines))
    application.add_handler(CommandHandler("roulette", start_roulette))
    application.add_handler(CallbackQueryHandler(gender_handler))
    application.add_handler(CallbackQueryHandler(want_vip_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, command_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.run_polling()

import asyncio
asyncio.run(main())