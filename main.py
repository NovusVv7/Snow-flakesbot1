
import json
import os
import random
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"  # вставьте ваш токен
ADMINS = ['6359584002']
DATA_FILE = "data.json"

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
        data["user_balance"][user_id] = 10000
        data["total_players"] += 1
        save_data(data)

    # Проверка заблокированных
    if user_id in data["banned_users"]:
        update.message.reply_text("🚫 Вы заблокированы!")
        return

    # Баланс
    if text in ['б', '/баланс', 'баланс']:
        balance = data["user_balance"].get(user_id, 0)
        update.message.reply_text(f"❄️ Твой баланс: {balance} снежинок❄️")
        return

    # Отмена ставки
    if text == '/отмена':
        if user_id in data["user_bets"]:
            del data["user_bets"][user_id]
            save_data(data)
            update.message.reply_text("🚫 Ваша ставка отменена.")
        else:
            update.message.reply_text("❗ У вас нет активной ставки.")
        return

    # Запуск рулетки
    if text == 'го':
        start_roulette(update, context, user_id)
        return

    # Обработка ставок
    handle_bet_message(update, context, user_id, text)

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
            bet_value = 'красный'
        elif bet_input in ['черный', 'black']:
            bet_type = 'color'
            bet_value = 'черный'
        elif bet_input in ['нечет', 'нечет', 'odd']:
            bet_type = 'parity'
            bet_value = 'нечет'
        elif bet_input in ['чет', 'even']:
            bet_type = 'parity'
            bet_value = 'чет'
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
        start_roulette(update, context, user_id)

    except Exception as e:
        print(f"Ошибка: {e}")
        update.message.reply_text("❌ Ошибка обработки ставки.")

def start_roulette(update, context, user_id):
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

    # Проверка выигрыша
    if bet['type'] == 'range':
        s, e = bet['value']['start'], bet['value']['end']
        if s <= result_number <= e:
            win = True
            payout = amount * (36 / (e - s + 1))
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

    if win:
        new_balance = int(balance + payout)
        data["user_balance"][user_id] = new_balance
        msg = f"🎉 Выпало число: *{result_number}* ({color}, {parity})\n🎉 Вы выиграли! +{int(payout)} снежинок❄️"
    else:
        new_balance = int(balance - amount)
        data["user_balance"][user_id] = new_balance
        msg = f"🎲 Выпало число: *{result_number}* ({color}, {parity})\n❌ Вы проиграли {amount} снежинок❄️"

    # Удаляем ставку
    del data["user_bets"][user_id]
    save_data(data)

    # Отправляем результат
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')

def handle_command(update, context):
    global data
    user_id = str(update.effective_user.id)
    parts = update.message.text.split()
    cmd = parts[0]

    if user_id not in ADMINS:
        return

    if cmd == '/выдать':
        try:
            target_id = parts[1]
            amount = int(parts[2])
            data["user_balance"][target_id] = data["user_balance"].get(target_id, 0) + amount
            update.message.reply_text(f"✅ Выдано {amount} снежинок пользователю {target_id}")
        except:
            update.message.reply_text("❌ Формат: /выдать [user_id] [amount]")
        save_data(data)
    elif cmd == '/забрать':
        try:
            target_id = parts[1]
            amount = int(parts[2])
            if data["user_balance"].get(target_id, 0) < amount:
                update.message.reply_text("❌ У пользователя недостаточно средств")
                return
            data["user_balance"][target_id] -= amount
            update.message.reply_text(f"✅ Забрано {amount} снежинок у пользователя {target_id}")
        except:
            update.message.reply_text("❌ Формат: /забрать [user_id] [amount]")
        save_data(data)
    elif cmd == '/бан':
        try:
            target_id = parts[1]
            if target_id not in data["banned_users"]:
                data["banned_users"].append(target_id)
                update.message.reply_text(f"✅ Пользователь {target_id} заблокирован")
            else:
                update.message.reply_text("ℹ️ Пользователь уже заблокирован")
        except:
            update.message.reply_text("❌ Формат: /бан [user_id]")
        save_data(data)
    elif cmd == '/разбан':
        try:
            target_id = parts[1]
            if target_id in data["banned_users"]:
                data["banned_users"].remove(target_id)
                update.message.reply_text(f"✅ Пользователь {target_id} разблокирован")
            else:
                update.message.reply_text("ℹ️ Пользователь не заблокирован")
        except:
            update.message.reply_text("❌ Формат: /разбан [user_id]")
        save_data(data)
    elif cmd == '/топ':
        top_list = sorted(data["user_balance"].items(), key=lambda x: x[1], reverse=True)[:10]
        msg = "🔥 Топ игроков:\n"
        for i, (uid, bal) in enumerate(top_list, 1):
            msg += f"{i}. Пользователь {uid}: {bal} снежинок❄️\n"
        update.message.reply_text(msg)

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