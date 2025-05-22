import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

DATABASE_NAME = 'db.db'


def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None

def create_tables():
    conn = get_db_connection()
    if conn is None:
        return 

    try:
        cursor = conn.cursor()

        #казнa
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 1,
                reward_per_invite INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS treasury_admins (
                chat_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS treasury (
                chat_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        ''')

        # рефка
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                inviter_id INTEGER,
                invited_id INTEGER,
                chat_id INTEGER,
                inviter_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id)
            )
        ''')

        # осноыное+рулетка
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            referrer_id INTEGER,
            referrals INTEGER DEFAULT 0,
            experience INTEGER DEFAULT 0,
            last_bonus_time INTEGER DEFAULT 0
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roulette_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            result TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roulette_bets (
            chat_id INTEGER,
            user_id INTEGER,
            amount INTEGER,
            spot TEXT,
            experience INTEGER DEFAULT 0
        )
        """)

        conn.commit()
        logging.info("Таблицы успешно созданы или уже существовали.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании таблиц: {e}")

    finally:
        conn.close()

create_tables()

def get_user(user_id):
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'balance': user[2],
                'level': user[3],
                'referrer_id': user[4],
                'referrals': user[5],
                'experience': user[6],
                'last_bonus_time': user[7]
            }
        return None

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении пользователя: {e}")
        return None

    finally:
        conn.close()


def add_user(user_id, username, referrer_id=None):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)",
            (user_id, username, referrer_id),
        )
        conn.commit()
        logging.info(f"Пользователь {user_id} успешно добавлен.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении пользователя: {e}")

    finally:
        conn.close()

def create_user(user_id, username, referrer_id=None):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)",
            (user_id, username, referrer_id),
        )
        conn.commit()
        logging.info(f"Пользователь {user_id} успешно создан.")

    except sqlite3.IntegrityError:
        logging.warning(f"Пользователь {user_id} уже существует.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании пользователя {user_id}: {e}")

    finally:
        conn.close()

def update_username(user_id, username):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
        conn.commit()
        logging.info(f"Имя пользователя {user_id} успешно обновлено.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении имени пользователя: {e}")

    finally:
        conn.close()

def update_balance(user_id, new_balance):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()
        logging.info(f"Баланс пользователя {user_id} успешно обновлен.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении баланса: {e}")

    finally:
        conn.close()
        
def get_balance(user_id):
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 0

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении баланса: {e}")
        return 0

    finally:
        conn.close()

def column_exists(cursor, table_name, column_name):
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке столбца: {e}")
        return False

def init_user_bonus(user_id: int, timestamp: int) -> bool:
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_bonus_time = ? WHERE user_id = ?", (timestamp, user_id))
        conn.commit()
        logging.info(f"[Бонус] last_bonus_time обновлен для {user_id}: {timestamp}")
        return True

    except sqlite3.Error as e:
        logging.error(f"Ошибка обновления бонуса: {e}")
        return False

    finally:
        conn.close()

def update_user_level(user_id: int, new_level: int):
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        user = get_user(user_id)
        if user and user['level'] < 5:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET level = level + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            logging.info(f"Уровень пользователя {user_id} успешно обновлён.")
            return True
        return False
    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении уровня пользователя: {e}")
        return False

    finally:
        conn.close()

def get_referrals(referrer_id):
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE referrer_id = ?", (referrer_id,))
        result = cursor.fetchall()
        return result

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении рефералов: {e}")
        return []

    finally:
        conn.close()

def increment_referral_count(user_id):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        logging.info(f"Количество рефералов для пользователя {user_id} увеличено.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при увеличении количества рефералов: {e}")

    finally:
        conn.close()

def register_user(user_id, username, referrer_id=None):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (user_id, username, referrer_id))
        conn.commit()
        logging.info(f"Пользователь {user_id} зарегистрирован или уже существовал.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при регистрации пользователя: {e}")

    finally:
        conn.close()

def get_transfer_limit(level):
    return level * 500

def add_roulette_result(chat_id, result):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO roulette_history (chat_id, result) VALUES (?, ?)", (chat_id, result))

        cursor.execute("""
            SELECT id FROM roulette_history 
            WHERE chat_id = ? 
            ORDER BY id DESC 
            LIMIT -1 OFFSET 8
        """, (chat_id,))
        
        rows_to_delete = cursor.fetchall()
        if rows_to_delete:
            ids = tuple(row[0] for row in rows_to_delete)
            placeholders = ','.join('?' for _ in ids)
            cursor.execute(f"DELETE FROM roulette_history WHERE id IN ({placeholders})", ids)
            logging.info(f"Удалены старые записи из истории рулетки для chat_id {chat_id}.")

        conn.commit()

    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении результата рулетки: {e}")

    finally:
        conn.close()

def get_total_users():
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()
        return result[0] if result else 0

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении общего количества пользователей: {e}")
        return 0

    finally:
        conn.close()

def get_last_roulette_results(chat_id):
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT result FROM roulette_history 
            WHERE chat_id = ? 
            ORDER BY id DESC 
            LIMIT 8
        """, (chat_id,))
        return [row[0] for row in cursor.fetchall()]

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении последних результатов рулетки: {e}")
        return []

    finally:
        conn.close()


def add_bet(chat_id, user_id, amount, spot):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO roulette_bets (chat_id, user_id, amount, spot) VALUES (?, ?, ?, ?)", (chat_id, user_id, amount, spot))
        conn.commit()
        logging.info(f"Ставка пользователя {user_id} добавлена в рулетку.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении ставки в рулетку: {e}")

    finally:
        conn.close()

def update_experience(user_id, new_exp):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET experience = ? WHERE user_id = ?", (new_exp, user_id))
        conn.commit()
        logging.info(f"Опыт пользователя {user_id} обновлен до {new_exp}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении опыта пользователя: {e}")

    finally:
        conn.close()

def add_exp(user_id: int, amount: int):
    if amount <= 0:
        logging.error("Количество опыта должно быть положительным.")
        return

    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT experience FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row is not None:
            current_exp = row[0] if row[0] is not None else 0
            new_exp = current_exp + amount
            cursor.execute("UPDATE users SET experience = ? WHERE user_id = ?", (new_exp, user_id))
            conn.commit()
            logging.info(f"Опыт пользователя {user_id} увеличен на {amount}. Новое значение опыта: {new_exp}.")
        else:
            logging.error(f"Пользователь с ID {user_id} не найден.")

    finally:
        conn.close()

def get_all_bets(chat_id):
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, amount, spot FROM roulette_bets WHERE chat_id = ?", (chat_id,))
        return cursor.fetchall()

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении всех ставок в рулетке: {e}")
        return []

    finally:
        conn.close()

def get_user_bets(chat_id, user_id):
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT amount, spot FROM roulette_bets WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        return cursor.fetchall()

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении ставок пользователя в рулетке: {e}")
        return []

    finally:
        conn.close()

def get_chat_settings(chat_id):
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT is_active, reward_per_invite FROM chat_settings WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        if result:
            return {'is_active': result[0], 'reward_per_invite': result[1]}
        else:
            return None 

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении настроек чата: {e}")
        return None

    finally:
        conn.close()

def create_chat_settings(chat_id):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_settings (chat_id, is_active, reward_per_invite) VALUES (?, ?, ?)",
            (chat_id, 1, 0), 
        )
        conn.commit()
        logging.info(f"Созданы настройки чата по умолчанию для chat_id {chat_id}.")

    except sqlite3.IntegrityError:
        logging.warning(f"Настройки чата для chat_id {chat_id} уже существуют.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании настроек чата: {e}")

    finally:
        conn.close()



def set_reward_per_invite(chat_id, reward_per_invite):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT chat_id FROM chat_settings WHERE chat_id = ?", (chat_id,))
        existing_chat = cursor.fetchone()

        if existing_chat is None:
            create_chat_settings(chat_id)

        cursor.execute("UPDATE chat_settings SET reward_per_invite = ? WHERE chat_id = ?", (reward_per_invite, chat_id))
        conn.commit()
        logging.info(f"Награда за приглашение в чат {chat_id} обновлена до {reward_per_invite}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при установке награды за приглашение: {e}")

    finally:
        conn.close()


def is_treasury_admin(chat_id, user_id):
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM treasury_admins WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        result = cursor.fetchone()
        return result is not None

    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке, является ли пользователь админом казны: {e}")
        return False

    finally:
        conn.close()


def add_treasury_admin(chat_id, user_id):
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO treasury_admins (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
        conn.commit()
        logging.info(f"Пользователь {user_id} добавлен в админы казны для чата {chat_id}.")
        return True

    except sqlite3.IntegrityError:
        logging.warning(f"Пользователь {user_id} уже является админом казны для чата {chat_id}.")
        return False

    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении админа казны: {e}")
        return False

    finally:
        conn.close()

def get_treasury_balance(chat_id):
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM treasury WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return 0

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении баланса казны: {e}")
        return 0

    finally:
        conn.close()

def deposit_to_treasury(chat_id, amount):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO treasury (chat_id, balance) VALUES (?, 0)", (chat_id,))
        cursor.execute("UPDATE treasury SET balance = balance + ? WHERE chat_id = ?", (amount, chat_id))
        conn.commit()
        logging.info(f"В казну чата {chat_id} внесено {amount}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при внесении депозита в казну: {e}")

    finally:
        conn.close()

def add_invite(inviter_id, inviter_name, chat_id):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO invites (inviter_id, inviter_name, chat_id) VALUES (?, ?, ?)", (inviter_id, inviter_name, chat_id))
        conn.commit()
        logging.info(f"Запись о приглашении пользователя {inviter_id} добавлена в чат {chat_id}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении приглашения: {e}")

    finally:
        conn.close()

def get_unrewarded_invites(chat_id, inviter_id):
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM invites WHERE chat_id = ? AND inviter_id = ?", (chat_id, inviter_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении невознагражденных приглашений: {e}")
        return 0

    finally:
        conn.close()

def clear_invites(chat_id, inviter_id):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invites WHERE chat_id = ? AND inviter_id = ?", (chat_id, inviter_id))
        conn.commit()
        logging.info(f"Записи о приглашениях пользователя {inviter_id} очищены в чате {chat_id}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при очистке приглашений: {e}")

    finally:
        conn.close()

def delete_user_bets(chat_id, user_id):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM roulette_bets WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()
        logging.info(f"Ставки пользователя {user_id} удалены в чате {chat_id}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при удалении ставок пользователя: {e}")

    finally:
        conn.close()

def add_balance(user_id: int, amount: int):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            new_balance = row[0] + amount
            cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
            conn.commit()
            logging.info(f"Баланс пользователя {user_id} увеличен на {amount}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при добавлении баланса пользователю: {e}")

    finally:
        conn.close()

def clear_bets(chat_id):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM roulette_bets WHERE chat_id = ?", (chat_id,))
        conn.commit()
        logging.info(f"Ставки в рулетке очищены в чате {chat_id}.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при очистке ставок: {e}")

    finally:
        conn.close()
