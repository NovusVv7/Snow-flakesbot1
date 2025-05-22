
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler

TOKEN = "YOUR_BOT_TOKEN"  # замените на ваш токен
ADMINS = ['6359584002']  # ID админов как строки
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

    # Обновляем статистику
    if user_id not in data["user_balance"]:
        data["user_balance"][user_id] = 0
        data["total_players"] += 1
        save_data(data)

    # Проверка заблокированных
    if user_id in data["banned_users"]:
        update.message.reply_text("🚫 Вы заблокированы!")
        return

    # Показывать баланс
    if text == 'б' or text == '/баланс' or text == 'баланс':
        balance = data["user_balance"].get(user_id, 0)
        update.message.reply_text(f"❄️ Твой баланс: {balance} снежинок")
        return

    # Текущие команды
    if text.startswith('/'):
        # Обработка команд
        parts = text.split()
        cmd = parts[0]

        # Админские команды
        if user_id in ADMINS:
            if cmd == '/выдать':
                try:
                    target_id = parts[1]
                    amount = int(parts[2])
                    data["user_balance"][target_id] = data["user_balance"].get(target_id, 0) + amount
                    update.message.reply_text(f"✅ Выдано {amount} снежинок пользователю {target_id}")
                except:
                    update.message.reply_text("❌ Формат: /выдать [user_id] [amount]")
                save_data(data)
                return

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
                return

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
                return

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
                return

            elif cmd == '/топ':
                top_list = sorted(data["user_balance"].items(), key=lambda x: x[1], reverse=True)[:10]
                msg = "🔥 Топ по снежинкам:\n"
                for i, (uid, bal) in enumerate(top_list, 1):
                    msg += f"{i}. Пользователь {uid} — {bal} снежинок\n"
                update.message.reply_text(msg)
                return

            elif cmd == '/статистика':
                total = data.get("total_players", 0)
                update.message.reply_text(f"👥 Зарегистрировано игроков: {total}")
                return

            elif cmd == '/передать':
                try:
                    target_id = parts[1]
                    amount = int(parts[2])
                    sender_balance = data["user_balance"].get(user_id, 0)
                    if sender_balance < amount:
                        update.message.reply_text("❌ Недостаточно снежинок.")
                        return
                    data["user_balance"][user_id] -= amount
                    data["user_balance"][target_id] = data["user_balance"].get(target_id, 0) + amount
                    update.message.reply_text(f"✅ Передано {amount} снежинок пользователю {target_id}")
                except:
                    update.message.reply_text("❌ Формат: /передать [user_id] [amount]")
                save_data(data)
                return

    # Если не команда, проверить на игру
    # Игра рулетка
    if text in ['го', 'го!','go','start']:
        update.message.reply_text("🎲 Сделайте ставку! Например:\n"
                                  "500 15\nили\n100 1-10\nили\n50 красный\nили\n20 чет")
        data["user_bets"][user_id] = {'stage': 'waiting'}
        save_data(data)
        return

    # Обработка ставки
    if user_id in data["user_bets"]:
        bet_info = data["user_bets"][user_id]
        if bet_info.get('stage') == 'waiting':
            # Парсим ставку
            try:
                parts = text.split()
                amount = int(parts[0])
                bet_value = ' '.join(parts[1:])
                balance = data["user_balance"].get(user_id, 0)

                if amount <= 0 or amount > balance:
                    update.message.reply_text("❌ Недопустимая ставка.")
                    return

                # Проверка диапазона
                if '-' in bet_value:
                    start_end = bet_value.split('-')
                    start, end = int(start_end[0]), int(start_end[1])
                    if not(0 <= start <= end <=36):
                        update.message.reply_text("❌ Неверный диапазон.")
                        return
                elif bet_value in ['красный', 'красный', 'red']:
                    bet_type = 'red'
                elif bet_value in ['черный', 'черный', 'black']:
                    bet_type = 'black'
                elif bet_value in ['нечет', 'нечет', 'odd']:
                    bet_type = 'odd'
                elif bet_value in ['чет', 'чет', 'even']:
                    bet_type = 'even'
                else:
                    # число
                    bet_number = int(bet_value)
                    if not(0 <= bet_number <=36):
                        update.message.reply_text("❌ Число вне диапазона.")
                        return
                # Все хорошо, делаем ставку
                data["user_bets"][user_id] = {
                    'stage': 'placed',
                    'amount': amount,
                    'bet_value': bet_value,
                    'balance': balance
                }
                save_data(data)
                update.message.reply_text("✅ Ваша ставка принята! Ждите результатов...")
                # Запускаем рулетку
                run_roulette(update, context, user_id)
            except:
                update.message.reply_text("❌ Неверный формат ставки. Например:\n500 15\nили\n100 1-10\nили\n50 красный")
        return

def run_roulette(update: Update, context: CallbackContext, user_id):
    global data
    # Генерируем результат
    winning_number = random.randint(0,36)
    color = 'red' if winning_number in [1,3,5,7,9,12,14,16,19,21,23,25,27,30,32,34,36] else 'black'
    parity = 'odd' if winning_number %2 ==1 else 'even'

    user_bet = data["user_bets"].get(user_id)
    if not user_bet:
        return

    amount = user_bet['amount']
    bet_value = user_bet['bet_value']
    balance = user_bet['balance']

    # Проверка ставки
    win = False
    payout = 0

    # Диапазон
    if '-' in bet_value:
        start, end = map(int, bet_value.split('-'))
        if start <= winning_number <= end:
            win = True
            payout = amount * (36 / (end - start + 1))
    # Число
    elif bet_value.isdigit():
        if int(bet_value) == winning_number:
            win = True
            payout = amount * 35
    elif bet_value in ['красный', 'red']:
        if color == 'red':
            win = True
            payout = amount * 2
    elif bet_value in ['черный', 'black']:
        if color == 'black':
            win = True
            payout = amount * 2
    elif bet_value in ['нечет', 'odd']:
        if parity == 'odd':
            win = True
            payout = amount * 2
    elif bet_value in ['чет', 'even']:
        if parity == 'even':
            win = True
            payout = amount * 2
    else:
        # Неизвестная ставка
        update.message.reply_text("❌ Неизвестный тип ставки.")
        return

    # Обновляем баланс
    if win:
        data["user_balance"][user_id] = balance + int(payout)
        result_text = f"🎉 Выпало число: {winning_number} ({color}, {parity})\nВы выиграли! +{int(payout)} снежинок"
    else:
        data["user_balance"][user_id] = balance - amount
        result_text = f"🎲 Выпало число: {winning_number} ({color}, {parity})\nВы проиграли {amount} снежинок"

    # Удаляем ставку
    del data["user_bets"][user_id]
    save_data(data)

    # Отправляем результат
    context.bot.send_message(chat_id=update.effective_chat.id, text=result_text)

# Запуск бота
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    print("Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()