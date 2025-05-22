import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import sqlite3
import random
import config

# Настройка базы данных
conn = sqlite3.connect('snowflakes.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, 
              username TEXT,
              snowflakes INTEGER DEFAULT 0,
              banned BOOLEAN DEFAULT FALSE)''')
conn.commit()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Команды администратора
CREATOR_ID = config.CREATOR_ID
active_bets = {}
PAYOUTS = {
    1: 35,   # Прямая ставка
    2: 17,   # Сплит
    3: 11,   # Стрит
    4: 8,    # Угол
    6: 5,    # Линия
    12: 2,   # Дюжины/колонки
    18: 1    # Чет/нечет, красное/черное
}

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    update.message.reply_text("❄️ Добро пожаловать в Snowflake Bot! Используй команды:\n"
                             "💎 Баланс - показать снежинки\n"
                             "🎰 Рулетка [сумма] [числа/диапазоны]\n"
                             "🎁 Передать [@юзер] [сумма]\n"
                             "❌ Отмена - отменить текущую ставку")

def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    snowflakes = cursor.execute("SELECT snowflakes FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
    update.message.reply_text(f"❄️ Ваш баланс: {snowflakes} снежинок")

def transfer(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = update.message.text.split()[1:]
    
    if len(args) != 2 or not args[1].isdigit():
        update.message.reply_text("❌ Формат: Передать @юзер сумма")
        return
    
    recipient_username = args[0].lstrip('@')
    amount = int(args[1])
    
    recipient = cursor.execute("SELECT user_id, snowflakes FROM users WHERE username=?", 
                             (recipient_username,)).fetchone()
    
    if not recipient:
        update.message.reply_text("❌ Пользователь не найден")
        return
        
    sender_balance = cursor.execute("SELECT snowflakes FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
    
    if sender_balance < amount:
        update.message.reply_text("❌ Недостаточно снежинок")
        return
        
    cursor.execute("UPDATE users SET snowflakes = snowflakes - ? WHERE user_id=?", (amount, user_id))
    cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE user_id=?", (amount, recipient[0]))
    conn.commit()
    update.message.reply_text(f"✅ Успешно передано {amount} снежинок пользователю @{recipient_username}")

def give_snowflakes(update: Update, context: CallbackContext):
    if update.effective_user.id != CREATOR_ID:
        return
    
    args = update.message.text.split()[1:]
    if len(args) != 2 or not args[1].isdigit():
        update.message.reply_text("❌ Формат: /give @юзер сумма")
        return
    
    username = args[0].lstrip('@')
    amount = int(args[1])
    
    cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE username=?", (amount, username))
    conn.commit()
    update.message.reply_text(f"✅ Выдано {amount} снежинок пользователю @{username}")

def take_snowflakes(update: Update, context: CallbackContext):
    if update.effective_user.id != CREATOR_ID:
        return
    
    args = update.message.text.split()[1:]
    if len(args) != 2 or not args[1].isdigit():
        update.message.reply_text("❌ Формат: /take @юзер сумма")
        return
    
    username = args[0].lstrip('@')
    amount = int(args[1])
    
    cursor.execute("UPDATE users SET snowflakes = snowflakes - ? WHERE username=?", (amount, username))
    conn.commit()
    update.message.reply_text(f"✅ Изъято {amount} снежинок у @{username}")

def ban_user(update: Update, context: CallbackContext):
    if update.effective_user.id != CREATOR_ID:
        return
    
    username = update.message.text.split()[1].lstrip('@')
    cursor.execute("UPDATE users SET banned = TRUE WHERE username=?", (username,))
    conn.commit()
    update.message.reply_text(f"⛔ Пользователь @{username} забанен")

def roulette(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = update.message.text.split()[1:]
    
    if args and args[0].lower() in ['отмена', 'cancel']:
        if user_id in active_bets:
            del active_bets[user_id]
            update.message.reply_text("❄️ Ставка отменена!")
        else:
            update.message.reply_text("❌ Нет активных ставок для отмены")
        return
    
    if len(args) < 2:
        update.message.reply_text("❌ Формат: Рулетка [ставка] [числа/диапазоны через пробел]\n"
                                 "Пример: Рулетка 1000 0 2 5 14-17\n"
                                 "Для отмены: Рулетка отмена")
        return
    
    try:
        bet = int(args[0])
        if bet < 10:
            update.message.reply_text("❌ Минимальная ставка: 10 снежинок")
            return
    except ValueError:
        update.message.reply_text("❌ Неверная сумма ставки")
        return
    
    active_bets[user_id] = {
        'bet_amount': bet,
        'numbers': set(),
        'ranges': []
    }
    
    valid = True
    for item in args[1:]:
        if '-' in item:
            try:
                start, end = map(int, item.split('-'))
                if 0 <= start <= end <= 36:
                    active_bets[user_id]['ranges'].append((start, end))
                else:
                    valid = False
            except:
                valid = False
        elif item.isdigit():
            num = int(item)
            if 0 <= num <= 36:
                active_bets[user_id]['numbers'].add(num)
            else:
                valid = False
        else:
            valid = False
        
        if not valid:
            del active_bets[user_id]
            update.message.reply_text(f"❌ Некорректное значение: {item}")
            return
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm_bet'),
         InlineKeyboardButton("❌ Отменить", callback_data='cancel_bet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bet_info = "Выбранные позиции:\n"
    if active_bets[user_id]['numbers']:
        bet_info += f"Числа: {', '.join(map(str, sorted(active_bets[user_id]['numbers'])))}\n"
    for r in active_bets[user_id]['ranges']:
        bet_info += f"Диапазон: {r[0]}-{r[1]}\n"
    
    update.message.reply_text(
        f"❄️ Подтвердите ставку:\n"
        f"Сумма: {bet} снежинок\n"
        f"{bet_info}\n"
        f"У вас есть 30 секунд для подтверждения!",
        reply_markup=reply_markup
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if data == 'confirm_bet':
        if user_id not in active_bets:
            query.answer("❌ Ставка уже отменена")
            return
            
        bet_data = active_bets[user_id]
        del active_bets[user_id]
        
        user_balance = cursor.execute("SELECT snowflakes, banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        
        if user_balance[1]:
            query.edit_message_text("⛔ Вы забанены!")
            return
            
        if user_balance[0] < bet_data['bet_amount']:
            query.edit_message_text("❌ Недостаточно снежинок")
            return
        
        total_numbers = len(bet_data['numbers'])
        for r in bet_data['ranges']:
            total_numbers += r[1] - r[0] + 1
        
        result = random.randint(0, 36)
        red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        color = 'красное' if result in red_numbers else 'черное' if result !=0 else 'зеленое'
        win = False
        
        if result in bet_data['numbers']:
            win = True
        else:
            for r in bet_data['ranges']:
                if r[0] <= result <= r[1]:
                    win = True
                    break
        
        closest_payout = min(PAYOUTS.keys(), key=lambda x: abs(x - total_numbers))
        payout_multiplier = PAYOUTS[closest_payout] if closest_payout <= total_numbers else 0
        
        if win:
            payout = payout_multiplier * bet_data['bet_amount']
            cursor.execute("UPDATE users SET snowflakes = snowflakes + ? WHERE user_id=?", 
                         (payout, user_id))
            conn.commit()
            message = f"🎉 Выигрыш! Выпало: {result} ({color})\n💰 +{payout} снежинок!"
        else:
            cursor.execute("UPDATE users SET snowflakes = snowflakes - ? WHERE user_id=?", 
                         (bet_data['bet_amount'], user_id))
            conn.commit()
            message = f"💔 Проигрыш! Выпало: {result} ({color})\n❄️ -{bet_data['bet_amount']} снежинок"
        
        query.edit_message_text(message)
        
    elif data == 'cancel_bet':
        if user_id in active_bets:
            del active_bets[user_id]
            query.edit_message_text("❄️ Ставка отменена")
        else:
            query.answer("❌ Нет активной ставки")

def main():
    updater = Updater(config.TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex(r'^баланс$'), balance))
    dp.add_handler(MessageHandler(Filters.regex(r'^передать '), transfer))
    dp.add_handler(MessageHandler(Filters.regex(r'^рулетка '), roulette))
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    dp.add_handler(CommandHandler("give", give_snowflakes))
    dp.add_handler(CommandHandler("take", take_snowflakes))
    dp.add_handler(CommandHandler("ban", ban_user))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()