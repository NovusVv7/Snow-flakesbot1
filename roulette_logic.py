import random
import math

active_bets = {}
LAST_ROULETTE_RESULTS = {}

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}


def parse_bets(text):
    try:
        amount, *bets = text.lower().split()
        amount = int(amount)
        if amount < 10:
            return []
        parsed = []
        seen = set()
        for bet in bets:
            bet = bet.strip()
            if is_valid_bet(bet) and (amount, bet) not in seen:
                parsed.append((amount, bet))
                seen.add((amount, bet))
        return parsed
    except Exception:
        return []


def is_valid_bet(bet):
    try:
        if bet.isdigit():
            return 0 <= int(bet) <= 36

        if "-" in bet:
            parts = bet.split("-")
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                start, end = map(int, parts)
                return 0 <= start <= end <= 36

        return bet in {
            "ч", "н", "чет", "нечет", "odd", "even",
            "к", "одд", "евен", "чёрное", "черное", "red", "black",
            "1-12", "13-24", "25-36", "1-18", "19-36", "0-36"
        }
    except Exception:
        return False

def is_winner(bet, result):
    try:
        number = int(result)
        bet = bet.lower()

        if bet.isdigit() and int(bet) == number:
            return True

        if "-" in bet:
            parts = bet.split("-")
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                start, end = map(int, parts)
                if start <= number <= end:
                    return True

        if bet in ["чет", "even", "евен"] and number != 0 and number % 2 == 0:
            return True
        if bet in ["нечет", "odd", "одд"] and number != 0 and number % 2 == 1:
            return True

        if bet in ["к", "red"] and number in RED_NUMBERS:
            return True
        if bet in ["чёрное", "черное", "ч", "black"] and number in BLACK_NUMBERS:
            return True

    except Exception as e:
        print(f"❌ Ошибка в is_winner: {e}")
    return False
    
def get_multiplier(bet):
    try:
        bet = bet.lower()

        if bet.isdigit():
            return 36

        if "-" in bet:
            parts = bet.split("-")
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                start, end = map(int, parts)
                count = end - start + 1
                if count > 0:
                    multiplier = round(36 / count)
                    # Округляем в большую сторону
                    return max(1, multiplier)

        if bet in {
            "ч", "н", "чет", "нечет", "odd", "even",
            "к", "одд", "евен", "чёрное", "черное", "red", "black"
        }:
            return 2

    except Exception as e:
        print(f"❌ Ошибка в get_multiplier: {e}")
    return 0


def spin_roulette():
    return str(random.randint(0, 36))


def get_color_emoji(num):
    try:
        n = int(num)
        if n == 0:
            return "🟢"
        if n in RED_NUMBERS:
            return "🔴"
        if n in BLACK_NUMBERS:
            return "⚫️"
    except:
        pass
    return ""


def update_last_roulette(chat_id, result):
    if chat_id not in LAST_ROULETTE_RESULTS:
        LAST_ROULETTE_RESULTS[chat_id] = []
    LAST_ROULETTE_RESULTS[chat_id].append(result)
    if len(LAST_ROULETTE_RESULTS[chat_id]) > 8:
        LAST_ROULETTE_RESULTS[chat_id].pop(0)


def get_last_roulette(chat_id):
    results = LAST_ROULETTE_RESULTS.get(chat_id, [])
    if not results:
        return "Последние ставки: нет"
    return "Последние ставки: " + " | ".join(results)


def calculate_winners(bets, result):
    winners = []
    for user_id, amount, bet in bets:
        if is_winner(bet, result):
            multiplier = get_multiplier(bet)
            win = amount * multiplier
            winners.append((user_id, win, bet))
    return winners


def format_bet_log(bets, result, winners, chat_id=None):
    from database import get_user

    lines = [f"🎩 Рулетка: {result} {get_color_emoji(result)}"]

    if chat_id:
        lines.append(get_last_roulette(chat_id))

    lines.append("\n❗Ставки:")
    for user_id, amount, bet in bets:
        user_data = get_user(user_id)
        name = user_data['username'] if user_data and 'username' in user_data else (user_data['first_name'] if user_data and 'first_name' in user_data else "Неизвестный пользователь")
        lines.append(f"— {name} поставил {amount} KRUNN на {bet}")

    lines.append("")
    if winners:
        lines.append("😰 Победители:")
        for user_id, win, bet in winners:
            user_data = get_user(user_id)
            name = user_data['username'] if user_data and 'username' in user_data else (user_data['first_name'] if user_data and 'first_name' in user_data else "Неизвестный пользователь")
            lines.append(f"— {name} выиграл {win} KRUNN на {bet}")
    else:
        lines.append("Никто не выиграл ❌")

    return "\n".join(lines)