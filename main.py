import telebot
from telebot import types
import random
import json
from collections import defaultdict

# Конфигурация
TOKEN = '7561318621:AAHLIMv1cQPXSkBYWkFCeys5XsXg2c4M3fc'
MIN_BET = 100
MAX_BET = 50000
BALANCE_FILE = 'balances.json'

bot = telebot.TeleBot(TOKEN)

# Коэффициенты выплат для европейской рулетки
PAYOUTS = {
    'straight': 35,       # Одно число
    'split': 17,          # Два соседних числа
    'street': 11,         # Три числа в строке
    'corner': 8,          # Четыре числа в квадрате
    'line': 5,            # Две смежные улицы (6 чисел)
    'dozen': 2,           // 1-12, 13-24, 25-36
    'column': 2,          // Колонка
    'even_odd': 1,        # Чет/Нечет
    'red_black': 1,       # Цвет
    'low_high': 1,        # 1-18/19-36
    'basket': 6           # 0-1-2 или 0-2-3
}

# Распределение номеров по цветам
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

class RouletteGame:
    def __init__(self):
        self.active_bets = defaultdict(list)
        self.load_balances()
        
    def load_balances(self):
        try:
            with open(BALANCE_FILE, 'r') as f:
                self.balances = json.load(f)
        except:
            self.balances = defaultdict(lambda: 10000)

    def save_balances(self):
        with open(BALANCE_FILE, 'w') as f:
            json.dump(self.balances, f)

    def determine_bet_type(self, bet_input):
        if '-' in bet_input:
            parts = list(map(int, bet_input.split('-')))
            diff = parts[1] - parts[0]
            if diff == 1: return 'split'
            if diff == 2: return 'street'
            if diff == 3: return 'corner'
            return 'line' if diff == 5 else 'dozen'
        if bet_input.lower() in ['red', 'black']: return 'red_black'
        if bet_input.lower() in ['even', 'odd']: return 'even_odd'
        if bet_input.lower() in ['low', 'high']: return 'low_high'
        return 'straight'

    def validate_bet(self, user_id, amount, bet_type):
        if not MIN_BET <= amount <= MAX_BET:
            return False, f"Ставка должна быть между {MIN_BET} и {MAX_BET}"
        if self.balances[str(user_id)] < amount:
            return False, "Недостаточно средств"
        return True, ""

    def calculate_payout(self, win_number, bet):
        # Реализация проверки всех типов ставок
        if bet['type'] == 'straight':
            return bet['amount'] * PAYOUTS[bet['type']] if int(bet['value']) == win_number else 0
        
        # Добавить проверки для других типов ставок...
        
        return 0

game = RouletteGame()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🎰 Спин', '💰 Баланс')
    bot.send_message(
        message.chat.id,
        f"Добро пожаловать в Vegas Royale!\n\n"
        f"Ваш баланс: {game.balances[str(message.from_user.id)]} EZZZY",
        reply_markup=markup
    )

@bot.message_handler(regexp=r'(\d+) ezzzy на (.*)')
def place_bet(message):
    user_id = message.from_user.id
    try:
        amount = int(message.text.split()[0])
        bet_value = message.text.split('на ')[1].strip()
        
        bet_type = game.determine_bet_type(bet_value)
        valid, reason = game.validate_bet(user_id, amount, bet_type)
        
        if not valid:
            return bot.reply_to(message, f"❌ {reason}")
            
        game.active_bets[user_id].append({
            'amount': amount,
            'type': bet_type,
            'value': bet_value,
            'user': message.from_user.first_name
        })
        
        game.balances[str(user_id)] -= amount
        game.save_balances()
        
        bot.reply_to(message, f"✅ Ставка {amount} EZZZY на {bet_value} принята!")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text == '🎰 Спин')
def spin_roulette(message):
    win_number = random.randint(0, 36)
    color = 'red' if win_number in RED_NUMBERS else 'black' if win_number != 0 else 'green'
    emoji = {'red': '🔴', 'black': '⚫', 'green': '🟢'}[color]
    
    result_text = f"🎰 Выпало: {win_number}{emoji}\n\n"
    total_payout = 0
    
    for user_id, bets in game.active_bets.items():
        for bet in bets:
            payout = game.calculate_payout(win_number, bet)
            if payout > 0:
                game.balances[str(user_id)] += payout
                total_payout += payout
                result_text += f"🏆 {bet['user']}: +{payout} EZZZY ({bet['value']})\n"
            else:
                result_text += f"💀 {bet['user']}: -{bet['amount']} EZZZY ({bet['value']})\n"
    
    game.save_balances()
    game.active_bets.clear()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔄 Повторить", callback_data='repeat'),
        types.InlineKeyboardButton("✖️ Удвоить", callback_data='double')
    )
    
    bot.send_message(message.chat.id, result_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    if call.data == 'repeat':
        # Реализация повторения ставки
        pass
    elif call.data == 'double':
        # Реализация удвоения
        pass

if __name__ == '__main__':
    bot.infinity_polling()