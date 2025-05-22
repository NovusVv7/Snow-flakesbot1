
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"  # замените на ваш токен
ADMINS = ['6359584002']  # список ID админов как строки
DATA_FILE = "data.json"

# Инициализация данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "user_balance": {},
        "banned_users": [],
        "user_bets": {},
        "total_players": 0
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data = load_data()

# Обработка сообщений
def handle_message(update: Update, context: CallbackContext):
    global data
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower()

    # Регистрация нового пользователя
    if user_id not in data["user_balance"]:
        data["user_balance"][user_id] = 10000  # стартовые снежинки
        data["total_players"] += 1
        save_data(data)

    # Проверка заблокированных
    if user_id in data["banned_users"]:
        update.message.reply_text("🚫 Вы заблокированы!")
        return

    # Баланс команда
    if text in ['б', '/баланс', 'баланс']:
        balance = data["user_balance"].get(user_id, 0)
        update.message.reply_text(f"❄️ Твой баланс: {balance} снежинок❄️")
        return

    # Запуск рулетки
    if text == 'го':
        start_roulette(update, context, user_id)
        return

    # Обработка ставок
    handle_bet_message(update, context, user_id, text)

# Обработка ставок
def handle_bet_message(update: Update, context: CallbackContext, user_id, text):
    global data
    if user_id in data["user_bets"]:
        update.message.reply_text("❗ У вас уже есть активная ставка. Подождите результата.")
        return

    try:
        parts = text.split()
        amount = int(parts[0])
        bet_input = ' '.join(parts[1:])

        balance = data["user_balance"].get(user_id, 0)
        if amount <= 0:
            update.message.reply_text("❌ Сумма должна быть больше 0.")
            return
        if amount > balance:
            update.message.reply_text("❌ Недостаточно снежинок❄️.")
            return

        # Анализ ставки
        bet_type = None
        bet_value = None

        if '-' in bet_input:
            start_end = bet_input.split('-')
            start, end = int(start_end[0]), int(start_end[1])
            if not (0 <= start <= end <= 36):
                update.message.reply_text("❌ Неверный диапазон.")
                return
            bet_type = 'range'
            bet_value = {'start': start, 'end': end}
        elif bet_input in ['красный', 'red']:
            bet_type = 'color'
            bet_value = 'red'
        elif bet_input in ['черный', 'black']:
            bet_type = 'color'
            bet_value = 'black'
        elif bet_input in ['нечет', 'нечет', 'odd']:
            bet_type = 'parity'
            bet_value = 'odd'
        elif bet_input in ['чет', 'even']:
            bet_type = 'parity'
            bet_value = 'even'
        elif all(c.isdigit() or c == ' ' for c in bet_input):
            nums = list(set(int(n) for n in bet_input.split() if n.isdigit()))
            if all(0 <= n <= 36 for n in nums):
                bet_type = 'multiple'
                bet_value = nums
            else:
                update.message.reply_text("❌ Неверные числа.")
                return
        elif len(parts) == 2 and parts[1].isdigit():
            num = int(parts[1])
            if 0 <= num <= 36:
                bet_type = 'number'
                bet_value = num
            else:
                update.message.reply_text("❌ Неверное число.")
                return
        else:
            update.message.reply_text("❌ Неизвестный формат ставки.")
            return

        # Сохраняем ставку
        data["user_bets"][user_id] = {
            'amount': amount,
            'type': bet_type,
            'value': bet_value,
            'balance': balance
        }
        save_data(data)

        # Запускаем рулетку
        run_roulette(update, context, user_id)
    except:
        update.message.reply_text("❌ Ошибка обработки ставки.")

# Запуск рулетки и подсчет результата
def run_roulette(update: Update, context: CallbackContext, user_id):
    global data
    result_number = random.randint(0,36)
    red_numbers = [1,3,5,7,9,12,14,16,19,21,23,25,27,30,32,34,36]
    color = 'красный' if result_number in red_numbers else 'черный'
    parity = 'нечет' if result_number % 2 == 1 else 'чет'

    bet = data["user_bets"].get(user_id)
    if not bet:
        return

    amount = bet['amount']
    balance = bet['balance']
    win = False
    payout = 0
    msg = ""

    # Проверка выигрыша
    if bet['type'] == 'range':
        start, end = bet['value']['start'], bet['value']['end']
        if start <= result_number <= end:
            win = True
            payout = amount * (36 / (end - start + 1))
    elif bet['type'] == 'color':
        if bet['value'] == color:
            win = True
            payout = amount * 2
    elif bet['type'] == 'parity':
        if bet['value'] == parity:
            win = True
            payout = amount * 2
    elif bet['type'] == 'multiple':
        if result_number in bet['value']:
            win = True
            payout = amount * 35
    elif bet['type'] == 'number':
        if bet['value'] == result_number:
            win = True
            payout = amount * 36

    # Обновление баланса
    if win:
        data["user_balance"][user_id] = int(balance + payout)
        msg = f"🔥❄️ Выпало число: *{result_number}* ({color}, {parity})\nВы выиграли! +{int(payout)} снежинок❄️"
    else:
        data["user_balance"][user_id] = int(balance - amount)
        msg = f"🎲 Выпало число: *{result_number}* ({color}, {parity})\nВы проиграли {amount} снежинок❄️"

    # Удаляем ставку
    del data["user_bets"][user_id]
    save_data(data)

    # Отправляем результат
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')

# Основной запуск
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', lambda u, c: u.message.reply_text("Напишите 'Го' чтобы начать игру.")))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CommandHandler('выдать', handle_command))
    dp.add_handler(CommandHandler('забрать', handle_command))
    dp.add_handler(CommandHandler('бан', handle_command))
    dp.add_handler(CommandHandler('разбан', handle_command))
    dp.add_handler(CommandHandler('топ', handle_command))

    print("Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()