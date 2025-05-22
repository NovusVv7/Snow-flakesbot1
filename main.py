import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime, timedelta

TOKEN = "ВАШ_ТОКЕН_БОТА"
ADMIN_ID = ВАШ_ID_ТЕЛЕГРАМ
GROUP_CHAT_ID = "ВАШ_ID_ЧАТА"

conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, 
              gender TEXT, 
              is_vip INTEGER, 
              is_admin INTEGER,
              last_active DATETIME)''')
conn.commit()

gender_keyboard = [
    [InlineKeyboardButton("👩 Девушка", callback_data='gender_женский')],
    [InlineKeyboardButton("👨 Мужчина", callback_data='gender_мужской')]
]

async def update_last_active(user_id):
    c.execute("UPDATE users SET last_active=? WHERE user_id=?", 
             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        await update.message.reply_text(
            "👋 Привет! Выбери свой пол:",
            reply_markup=InlineKeyboardMarkup(gender_keyboard)
    else:
        await update.message.reply_text("Вы уже зарегистрированы!")
    await update_last_active(user_id)

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    gender = query.data.split('_')[1]
    
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)",
              (user_id, gender, 0, 1 if user_id == ADMIN_ID else 0, 
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    
    await query.edit_message_text(f"✅ Пол успешно сохранен: {gender}")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_last_active(user_id)
    
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    if user[1] != 'женский' and user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступно только для девушек")
        return
    
    caption = f"{'👑 VIP: ' if user[2] else ''}{update.message.caption or ''}"
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=file_id,
            caption=caption
        )
    elif update.message.video:
        file_id = update.message.video.file_id
        await context.bot.send_video(
            chat_id=GROUP_CHAT_ID,
            video=file_id,
            caption=caption
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_last_active(user_id)
    
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    
    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь через /start")
        return
    
    if user[1] != 'женский' and user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступно только для девушек")
        return
    
    message_text = f"{'👑 VIP: ' if user[2] else ''}{update.message.text}"
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=message_text
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Команда доступна только администратору")
        return
    
    # Общее количество пользователей
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # Активные за последние 24 часа
    active_time = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT COUNT(*) FROM users WHERE last_active > ?", (active_time,))
    active_users = c.fetchone()[0]
    
    # Количество VIP
    c.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
    vip_users = c.fetchone()[0]
    
    response = (
        f"📊 Статистика бота:\n"
        f"• Всего пользователей: {total_users}\n"
        f"• Активных за 24ч: {active_users}\n"
        f"• VIP-пользователей: {vip_users}"
    )
    
    await update.message.reply_text(response)

async def grant_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Команда доступна только администратору")
        return
    
    try:
        target_id = int(context.args[0])
        c.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (target_id,))
        conn.commit()
        await update.message.reply_text(f"✅ VIP выдан пользователю {target_id}")
    except:
        await update.message.reply_text("Использование: /grant_vip [user_id]")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(gender_handler, pattern='^gender_'))
    app.add_handler(CommandHandler("grant_vip", grant_vip))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    app.run_polling()

if __name__ == '__main__':
    main()