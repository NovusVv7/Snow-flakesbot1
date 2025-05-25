import telebot
import sqlite3
import random
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7650141860:AAGYFa2RnmgP8-djuctPE2mrKx8j357gX3U'
ADMIN_ID = 6359584002

bot = telebot.TeleBot(TOKEN)
roulette_bets = {}
mines_games = {}

# Настройки игры "Мины"
MINES_FIELD_SIZE = 49  # 7x7
MINES_COEFFICIENTS = [1.45, 1.79, 2.36, 5, 6, 12, 19, 55]
MINES_DEFAULT_BOMBS = 7

# Настройки рулетки
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        icecream INTEGER DEFAULT 1000,
        banned BOOLEAN DEFAULT FALSE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS mines_log (
        user_id INTEGER,
        bet_amount INTEGER,
        bombs INTEGER,
        result FLOAT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

# ... (остальные функции остаются без изменений до обработчиков)

@bot.message_handler(commands=["mines"])
def start_mines(msg):
    uid = msg.from_user.id
    if check_ban(uid):
        return
    
    try:
        args = msg.text.split()[1:]
        if len(args) < 1:
            return bot.reply_to(msg, "❌ Формат: /mines [ставка]")
        
        bet_amount = int(args[0])
        bombs = MINES_DEFAULT_BOMBS
        
        if get_balance(uid) < bet_amount:
            return bot.reply_to(msg, "❌ Недостаточно средств!")
        
        # Создаем игровое поле 7x7
        field = ['🟦']*MINES_FIELD_SIZE
        mines = random.sample(range(MINES_FIELD_SIZE), bombs)
        
        update_balance(uid, -bet_amount)
        mines_games[uid] = {
            'bet': bet_amount,
            'mines': mines,
            'opened': [],
            'coefficients': MINES_COEFFICIENTS.copy(),
            'cashout': False
        }
        
        # Создаем клавиатуру 7x7
        keyboard = InlineKeyboardMarkup()
        for i in range(0, 49, 7):
            row = []
            for j in range(i, i+7):
                row.append(InlineKeyboardButton(text=field[j], callback_data=f"mine_{j}"))
            keyboard.add(*row)
        keyboard.add(InlineKeyboardButton(text=f"💰 Забрать x{MINES_COEFFICIENTS[0]}", callback_data="mine_cashout"))
        
        bot.send_message(msg.chat.id,
                         f"💣 Игра «Мины 7x7»\n"
                         f"💰 Ставка: {bet_amount}🍦\n"
                         f"🚫 Количество мин: {bombs}\n"
                         f"🎰 Текущий коэффициент: x{MINES_COEFFICIENTS[0]}",
                         reply_markup=keyboard)

    except Exception as e:
        print(f"Ошибка в минах: {e}")
        bot.reply_to(msg, "❌ Ошибка! Формат: /mines [ставка]")

@bot.callback_query_handler(func=lambda call: call.data.startswith('mine'))
def handle_mines(call):
    uid = call.from_user.id
    if uid not in mines_games:
        return
    
    game = mines_games[uid]
    
    if call.data == "mine_cashout":
        if len(game['opened']) >= len(game['coefficients']):
            coeff = game['coefficients'][-1]
        else:
            coeff = game['coefficients'][len(game['opened'])]
        
        win = int(game['bet'] * coeff)
        update_balance(uid, win)
        del mines_games[uid]
        
        # Логирование
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO mines_log (user_id, bet_amount, bombs, result) VALUES (?, ?, ?, ?)",
                  (uid, game['bet'], MINES_DEFAULT_BOMBS, win))
        conn.commit()
        conn.close()
        
        bot.edit_message_text(f"🎉 Вы успешно забрали {win}🍦 (x{coeff})!",
                            call.message.chat.id,
                            call.message.message_id)
        return
    
    cell = int(call.data.split('_')[1])
    
    if cell in game['mines']:
        update_balance(uid, 0)
        del mines_games[uid]
        bot.edit_message_text(f"💥 Вы попали на мину! Проигрыш {game['bet']}🍦",
                            call.message.chat.id,
                            call.message.message_id)
    else:
        game['opened'].append(cell)
        step = len(game['opened'])
        
        # Обновляем клавиатуру
        new_text = f"💣 Игра «Мины 7x7»\n💰 Ставка: {game['bet']}🍦\n🚫 Мин: {MINES_DEFAULT_BOMBS}\n"
        keyboard = call.message.reply_markup
        
        # Обновляем кнопку
        for row in keyboard.keyboard:
            for btn in row:
                if btn.callback_data == call.data:
                    btn.text = '🟩'
        
        # Обновляем коэффициент
        if step < len(game['coefficients']):
            current_coeff = game['coefficients'][step]
        else:
            current_coeff = game['coefficients'][-1] * (1.5 ** (step - len(game['coefficients']) + 1))
        
        keyboard.keyboard[-1] = [InlineKeyboardButton(
            text=f"💰 Забрать x{current_coeff:.2f}" if step < 15 else "💰 Максимальный выигрыш",
            callback_data="mine_cashout")]
        
        bot.edit_message_text(f"{new_text}🎰 Текущий коэффициент: x{current_coeff:.2f}\n✅ Открыто клеток: {step}",
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=keyboard)

# Обновленная рулетка с мгновенным результатом
@bot.message_handler(func=lambda m: m.text.lower() == "го")
def roulette_start(msg):
    uid = msg.from_user.id
    if check_ban(uid):
        return
    
    if uid not in roulette_bets:
        return bot.reply_to(msg, "❌ Сначала сделайте ставку!")
    
    try:
        bet = roulette_bets[uid]
        result = random.randint(0, 36)
        color = 'красное' if result in RED_NUMBERS else 'черное' if result in BLACK_NUMBERS else ''
        parity = 'чет' if result%2 == 0 and result !=0 else 'нечет' if result !=0 else ''
        
        # Анимация
        anim = bot.send_message(msg.chat.id, "🎡 Рулетка запускается...")
        time.sleep(1)
        bot.edit_message_text("🎡 Крутим... 0", msg.chat.id, anim.message_id)
        time.sleep(1)
        bot.edit_message_text(f"🎡 Крутим... {result}", msg.chat.id, anim.message_id)
        time.sleep(1)
        
        # Результат
        bot.edit_message_text(f"🎯 Выпало: {result} {color} {parity}",
                            msg.chat.id,
                            anim.message_id)
        
        # Расчет выигрыша
        numbers_count = len(bet['numbers'])
        coeff = 36 / numbers_count if numbers_count > 0 else 0
        
        win = 0
        if result in bet['numbers']:
            win = int(bet['amount'] * coeff)
            update_balance(uid, win)
        
        # Результат
        result_text = (f"▫️ Ставка: {bet['amount']}🍦\n"
                      f"▫️ Коэффициент: x{coeff}\n"
                      f"▫️ Выигрыш: {'+' + str(win) if win else '0'}\n"
                      f"▫️ Новый баланс: {get_balance(uid)}🍦")
        
        del roulette_bets[uid]
        bot.send_message(msg.chat.id, result_text)

    except Exception as e:
        print(f"Ошибка рулетки: {e}")
        bot.reply_to(msg, "❌ Ошибка, попробуйте снова")

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()