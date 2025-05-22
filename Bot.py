import json
import os
import random
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))

# Файл хранения данных
DATA_FILE = "data.json"

# Загрузка данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "user_balance": {},
        "banned_users": [],
        "user_bets": {}
    }

# Сохранение данных
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Инициализация данных
data = load_data()
user_bets = data["user_bets"]
user_balance = data["user_balance"]
banned_users = set(data["banned_users"])

# Парсинг ставок
def parse_bet(bet_str: str):
    try:
        if '-' in bet_str:
            parts = list(map(int, bet_str.split('-')))
            if len(parts) == 2 and 0 <= parts[0] <= parts[1] <= 36:
                return ('range', (parts[0], parts[1]))
        else:
            num = int(bet_str)
            if 0 <= num <= 36:
                return ('number', num)
    except:
        return None
    return None

# Обработка сообщений
def handle_message(update: Update, context: CallbackContext):
    global data
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_id in banned_users:
        update.message.reply_text("🚫 Вы заблокированы!")
        return

    if text == 'б':
        balance = user_balance.get(str(user_id), 0)
        update.message.reply_text(f"❄️ Ваш баланс: {balance} снежинок")
        return

    if user_id in ADMINS:
        if text.startswith('/выдать'):
            try:
                _, target_id, amount = text.split()
                amount = int(amount)
                user_balance[target_id] = user_balance.get(target_id, 0) + amount
                data["user_balance"] = user_balance
                save_data(data)
                update.message.reply_text(f"✅ Выдано {amount} снежинок пользователю {target_id}")
            except:
                update.message.reply_text("❌ Формат: /выдать [user_id] [amount]")

        elif text.startswith('/забрать'):
            try:
                _, target_id, amount = text.split()
                amount = int(amount)
                if user_balance.get(target_id, 0) < amount:
                    update.message.reply_text("❌ У пользователя недостаточно средств")
                    return
                user_balance[target_id] = user_balance.get(target_id, 0) - amount
                data["user_balance"] = user_balance
                save_data(data)
                update.message.reply_text(f"✅ Изъято {amount} снежинок у пользователя {target_id}")
            except:
                update.message.reply_text("❌ Формат: /забрать [user_id] [amount]")

        elif text.startswith('/бан'):
            try:
                _, target_id = text.split()
                banned_users.add(target_id)
                data["banned_users"] = list(banned_users)
                save_data(data)
                update.message.reply_text(f"✅ Пользователь {target_id} заблокирован")
            except:
                update.message.reply_text("❌ Формат: /бан [user_id]")

    # Сохраняем данные
    data = {
        "user_balance": user_balance,
        "banned_users": list(banned_users),
        "user_bets": user_bets
    }
    save_data(data)

# Запуск бота
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    print("Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
