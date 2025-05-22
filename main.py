import os
import logging
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import ChatNotFound

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get the API token from the environment variable
TOKEN = os.getenv("API_TOKEN")
if not TOKEN:
    logging.error("API_TOKEN environment variable not set!")
    exit(1)  # Exit if the token is missing

# Initialize the bot with the token from the environment
bot = Bot(TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"
ADMIN_ID = 6359584002  # Ваш ID

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except FileNotFoundError:
        logging.warning("Database file not found. Creating a new one.")
        return {"users": {}, "banned": [], "history": {}}
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from database file. Using default database.")
        return {"users": {}, "banned": [], "history": {}}
    return {"users": {}, "banned": [], "history": {}}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving database: {e}")

db = load_db()

def get_user_id_from_username(username):
    for user_id, data in db["users"].items():
        if "username" in data and data["username"] == username:
            return user_id
    return None

@dp.message_handler(commands
