
import random
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# Токен бота
TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"  # замените на ваш токен

# Списки и словари
active_users = set()
user_pairs = {}  # user_id: partner_id
user_profiles = {}  # user_id: {'comments': [], 'reactions': 0}
vip_users = {123456789}  # замените на свои ID

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active_users.add(user_id)
    user_profiles.setdefault(user_id, {'comments': [], 'reactions': 0})
    await update.message.reply_text("Вы зарегистрированы! Напишите сообщение, и я соединю вас с собеседником.\nИли используйте /поиск для поиска собеседника.")

# Проверка VIP
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in vip_users:
        await update.message.reply_text("Вы VIP пользователь! 🎉")
    else:
        await update.message.reply_text("Вы не VIP.")

# Кто есть в боте
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_list = list(active_users)
    if not users_list:
        text = "Нет активных пользователей."
    else:
        text = "Активные пользователи:\n" + "\n".join(str(uid) for uid in users_list)
    await update.message.reply_text(text)

# Профиль
async def профиль(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = user_profiles.get(user_id, {'comments': [], 'reactions': 0})
    comments = profile['comments']
    reactions = profile['reactions']
    comments_text = "\n".join(comments) if comments else "Нет комментариев."
    await update.message.reply_text(
        f"Ваш профиль:\nКомментарии:\n{comments_text}\nРеакции: {reactions}"
    )

# Реакции
async def react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("Используйте /react 👍 или /react 👎")
        return
    reaction = parts[1]
    if reaction in ['👍', '👎']:
        user_profiles.setdefault(user_id, {'comments': [], 'reactions': 0})
        if reaction == '👍':
            user_profiles[user_id]['reactions'] += 1
        else:
            user_profiles[user_id]['reactions'] -= 1
        await update.message.reply_text(f"Реакция {reaction} добавлена!")
    else:
        await update.message.reply_text("Допустимы только реакции 👍 или 👎.")

# Обработка сообщений и мультимедиа
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Если пользователь в паре
    partner_id = user_pairs.get(user_id)
    if partner_id:
        try:
            # Пересылаем текст или мультимедиа
            if update.message.text:
                await context.bot.send_message(chat_id=partner_id, text=update.message.text)
            elif update.message.photo:
                for photo in update.message.photo:
                    await context.bot.send_photo(chat_id=partner_id, photo=photo.file_id)
            elif update.message.video:
                await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
            elif update.message.voice:
                await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)
            elif update.message.document:
                await context.bot.send_document(chat_id=partner_id, document=update.message.document.file_id)
            else:
                await context.bot.send_message(chat_id=partner_id, text="Получено мультимедиа.")
            await update.message.reply_text("Сообщение отправлено.")
        except:
            await update.message.reply_text("Не удалось отправить сообщение.")
        return

    # Если не в паре, ищем собеседника
    await update.message.reply_text("Ищу собеседника... Пожалуйста, подождите.")
    # Добавляем пользователя в активных
    active_users.add(user_id)
    # Ищем другого
    users_list = list(active_users - {user_id})
    if not users_list:
        await update.message.reply_text("Нет других пользователей для общения. Попробуйте позже.")
        return

    recipient_id = random.choice(users_list)
    user_pairs[user_id] = recipient_id
    user_pairs[recipient_id] = user_id

    await context.bot.send_message(chat_id=recipient_id, text="Вам новый собеседник! Напишите ему сообщение.")
    await update.message.reply_text("Вы соединены с собеседником!")

# Команда /поиск (можно использовать для поиска собеседника)
async def поиск(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Удаляем из пар, если есть
    partner_id = user_pairs.pop(user_id, None)
    if partner_id:
        try:
            await context.bot.send_message(chat_id=partner_id, text="Ваш собеседник вышел из разговора.")
        except:
            pass
    await update.message.reply_text("Ищу собеседника... Пожалуйста, подождите.")
    # Добавляем в активных
    active_users.add(user_id)
    users_list = list(active_users - {user_id})
    if not users_list:
        await update.message.reply_text("Нет других пользователей для общения. Попробуйте позже.")
        return
    recipient_id = random.choice(users_list)
    user_pairs[user_id] = recipient_id
    user_pairs[recipient_id] = user_id
    await context.bot.send_message(chat_id=recipient_id, text="Вам новый собеседник! Напишите ему сообщение.")
    await update.message.reply_text("Вы соединены с новым собеседником!")

# Команда /skip
async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = user_pairs.pop(user_id, None)
    if partner_id:
        try:
            await context.bot.send_message(chat_id=partner_id, text="Ваш собеседник пропустил вас.")
        except:
            pass
        user_pairs.pop(partner_id, None)
        await update.message.reply_text("Вы пропустили собеседника.")
    else:
        await update.message.reply_text("Вы не в разговоре.")
    # Ищем нового
    active_users.add(user_id)
    users_list = list(active_users - {user_id})
    if not users_list:
        await update.message.reply_text("Нет других пользователей для общения.")
        return
    new_partner_id = random.choice(users_list)
    user_pairs[user_id] = new_partner_id
    user_pairs[new_partner_id] = user_id
    await context.bot.send_message(chat_id=new_partner_id, text="Вам новый собеседник! Напишите ему сообщение.")
    await update.message.reply_text("Вы соединены с новым собеседником!")

# Основная функция
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vip", vip))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("профиль", профиль))
    app.add_handler(CommandHandler("react", react))
    app.add_handler(CommandHandler("поиск", поиск))
    app.add_handler(CommandHandler("skip", skip))
    # Обработчики мультимедиа и текста
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.VOICE | filters.Document.ALL | filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    print("Бот запущен.")
    app.run_polling()

if __name__ == '__main__':
    main()