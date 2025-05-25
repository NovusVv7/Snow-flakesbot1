import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)

games = {}
roulette_bets = {}
mines_games = {}

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    # ... (существующие таблицы)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mines_log (
            user_id INTEGER,
            bet_amount INTEGER,
            bombs INTEGER,
            coefficient FLOAT,
            win INTEGER,
            time TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

# ... (остальные существующие функции)

# ============= НОВЫЕ ФУНКЦИИ =============

@bot.message_handler(commands=['мины'])
def start_mines(msg):
    try:
        bet = int(msg.text.split()[1])
        uid = msg.from_user.id
        if get_balance(uid) < bet:
            return bot.reply_to(msg, "Недостаточно средств!")
        
        update_balance(uid, -bet)
        bombs = 5  # Количество мин
        mines = random.sample(range(25), bombs)
        
        keyboard = InlineKeyboardMarkup()
        buttons = [InlineKeyboardButton("🟦", callback_data=f"mine_{i}") for i in range(25)]
        for i in range(0, 25, 5):
            keyboard.row(*buttons[i:i+5])
        keyboard.row(InlineKeyboardButton("💣 Забрать x1.5", callback_data="cashout"))
        
        mines_games[uid] = {
            'bet': bet,
            'mines': mines,
            'opened': [],
            'coeff': 1.5
        }
        
        bot.send_message(msg.chat.id, f"💣 Игра «Мины»\nСтавка: {bet}🍦", reply_markup=keyboard)
    
    except:
        bot.reply_to(msg, "Используй: /мины [ставка]")

@bot.callback_query_handler(func=lambda call: call.data.startswith('mine'))
def handle_mine_click(call):
    uid = call.from_user.id
    if uid not in mines_games:
        return
    
    game = mines_games[uid]
    cell = int(call.data.split('_')[1])
    
    if cell in game['mines']:
        bot.edit_message_text("💥 БОМБА! Вы проиграли!", call.message.chat.id, call.message.message_id)
        del mines_games[uid]
        return
    
    game['opened'].append(cell)
    game['coeff'] *= 1.5
    
    keyboard = call.message.reply_markup
    for btn in keyboard.keyboard:
        for b in btn:
            if b.callback_data == call.data:
                b.text = "🟩"
    
    keyboard.keyboard[-1][0].text = f"💣 Забрать x{game['coeff']:.1f}"
    
    bot.edit_message_text(
        f"💣 Открыто клеток: {len(game['opened']}\n💰 Коэффициент: x{game['coeff']:.1f}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'cashout')
def cashout_mines(call):
    uid = call.from_user.id
    game = mines_games[uid]
    win = int(game['bet'] * game['coeff'])
    update_balance(uid, win)
    bot.edit_message_text(f"🎉 Вы выиграли {win}🍦!", call.message.chat.id, call.message.message_id)
    del mines_games[uid]

@bot.message_handler(commands=['топ'])
def top_balance(msg):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, icecream FROM users ORDER BY icecream DESC LIMIT 10")
    top = c.fetchall()
    conn.close()
    
    text = "🏆 Топ игроков:\n"
    for i, (name, balance) in enumerate(top, 1):
        text += f"{i}. {name}: {balance}🍦\n"
    
    bot.send_message(msg.chat.id, text)

@bot.message_handler(commands=['стата'])
def stats(msg):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT SUM(icecream) FROM users")
    total = c.fetchone()[0] or 0
    conn.close()
    
    bot.send_message(msg.chat.id, f"📊 Статистика:\n👥 Игроков: {users}\n💰 Всего монет: {total}🍦")

@bot.message_handler(commands=['забрать'])
def take_money(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, uid, amount = msg.text.split()
        update_balance(int(uid), -int(amount))
        bot.send_message(msg.chat.id, f"Успешно изъято {amount}🍦 у {uid}")
    except:
        bot.reply_to(msg, "Используй: /забрать [ID] [сумма]")

@bot.message_handler(commands=['ban'])
def ban_user(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(msg.text.split()[1])
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET icecream = 0 WHERE user_id = ?", (uid,))
        conn.commit()
        conn.close()
        bot.send_message(msg.chat.id, f"⛔ Пользователь {uid} забанен!")
    except:
        bot.reply_to(msg, "Используй: /ban [ID]")

@bot.message_handler(commands=['info'])
def user_info(msg):
    try:
        uid = int(msg.text.split()[1]) if len(msg.text.split()) > 1 else msg.from_user.id
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT first_name, icecream FROM users WHERE user_id = ?", (uid,))
        name, balance = c.fetchone()
        conn.close()
        bot.send_message(msg.chat.id, f"👤 {name}\n🆔 ID: {uid}\n💰 Баланс: {balance}🍦")
    except:
        bot.reply_to(msg, "Ошибка запроса информации")

@bot.message_handler(commands=['лог'])
def bet_log(msg):
    uid = msg.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT bet_text, result, win, time FROM bets WHERE user_id = ? ORDER BY time DESC LIMIT 10", (uid,))
    logs = c.fetchall()
    conn.close()
    
    text = "📝 Последние ставки:\n\n"
    for log in logs:
        text += f"🎰 {log[0]}\n🎯 Результат: {log[1]}\n💰 Выигрыш: {log[2]}🍦\n⏰ {log[3]}\n\n"
    
    bot.send_message(msg.chat.id, text)

# ============= ИСПРАВЛЕНИЯ =============

@bot.message_handler(func=lambda m: m.text.lower() == "го")
def roulette_start(msg):
    uid = msg.from_user.id
    if uid not in roulette_bets:
        return bot.reply_to(msg, "Сначала сделайте ставку!")
    
    # ... (остальная логика рулетки без изменений)
    # Добавить запись в лог для каждой ставки

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()