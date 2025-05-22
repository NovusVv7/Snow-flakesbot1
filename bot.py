import random
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Токен бота
TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"

# Список активных пользователей
active_users = set()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text

    # Добавляем пользователя в активных
    active_users.add(user_id)

    # Находим других активных пользователей
    users_list = list(active_users - {user_id})
    if not users_list:
        await update.message.reply_text("Нет других пользователей для общения. Попробуйте позже.")
        return

    # Выбираем случайного собеседника
    recipient_id = random.choice(users_list)

    try:
        # Пересылаем сообщение
        await context.bot.send_message(chat_id=recipient_id, text=message_text)
        # Можно добавить подтверждение отправителю
        await update.message.reply_text("Сообщение отправлено.")
    except:
        # Если не удалось отправить (например, пользователь заблокировал бота)
        await update.message.reply_text("Не удалось отправить сообщение. Попробуйте позже.")

# Запуск бота
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
  
