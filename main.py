import json
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
import random
import os

TOKEN = "7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc"  # Получить у @BotFather
ADMINS = ['6359584002']  # ID администраторов как строки
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"user_balance": {}, "banned_users": [], "user_bets": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data = load_data()

def handle_message(update: Update, context: CallbackContext):
    global data
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower()

    # Загрузка актуальных данных
    user_balance = data["user_balance"]
    banned_users = data["banned_users"]
    user_bets = data["user_bets"]

    if user_id in banned_users:
        update.message.reply_text("🚫 Вы заблокированы!")
        return

    # Показать баланс
    if text == 'б':
        balance = user_balance.get(user_id, 0)
        update.message.reply_text(f"❄️ Ваш баланс: {balance} снежинок")
        return

    # Админ-команды
    if user_id in ADMINS:
        if text.startswith('/выдать'):
            try:
                _, target_id, amount = text.split()
                amount = int(amount)
                user_balance[target_id] = user_balance.get(target_id, 0) + amount
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
                user_balance[target_id] -= amount
                update.message.reply_text(f"✅ Изъято {amount} снежинок у пользователя {target_id}")
            except:
                update.message.reply_text("❌ Формат: /забрать [user_id] [amount]")

        elif text.startswith('/бан'):
            try:
                _, target_id = text.split()
                if target_id not in banned_users:
                    banned_users.append(target_id)
                    update.message.reply_text(f"✅ Пользователь {target_id} заблокирован")
                else:
                    update.message.reply_text("ℹ️ Пользователь уже заблокирован")
            except:
                update.message.reply_text("❌ Формат: /бан [user_id]")

    # Обновление данных
    data = {
        "user_balance": user_balance,
        "banned_users": banned_users,
        "user_bets": user_bets
    }
    save_data(data)

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    print("Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()