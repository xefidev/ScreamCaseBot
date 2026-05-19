import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiohttp import web
import aiohttp_cors
import hashlib
import string
import random

# --- НАСТРОЙКИ ---
TOKEN = "8660260631:AAF9yETvvFVrIUUsP5twUZtPzik-0jaJUog"
ADMIN_IDS = [7782281997, 5396975347]
APP_URL = "https://scream-case-bot.vercel.app"
CHANNEL_URL = "https://t.me/ScreamCase"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect('database.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (user_id INTEGER PRIMARY KEY, 
                         stars INTEGER DEFAULT 0, 
                         tickets INTEGER DEFAULT 0,
                         referred_by INTEGER,
                         join_date TEXT, 
                         last_daily TEXT,
                         total_donated_stars INTEGER DEFAULT 0,
                         total_donated_ton REAL DEFAULT 0.0,
                         username TEXT,
                         first_name TEXT,
                         photo_url TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS payments 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes 
                        (code TEXT PRIMARY KEY, 
                         reward INTEGER, 
                         type TEXT, 
                         active BOOLEAN DEFAULT 1,
                         min_donation_24h INTEGER DEFAULT 0,
                         expires_at TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS ton_transactions 
                        (tx_id TEXT PRIMARY KEY, user_id INTEGER, amount REAL, date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tasks 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         title TEXT, 
                         reward INTEGER, 
                         type TEXT, 
                         url TEXT, 
                         chat_id TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS user_tasks 
                        (user_id INTEGER, 
                         task_id INTEGER, 
                         status TEXT DEFAULT 'completed', 
                         PRIMARY KEY (user_id, task_id))''')
        
        # Миграции
        try: conn.execute("ALTER TABLE users ADD COLUMN total_donated_stars INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN total_donated_ton REAL DEFAULT 0.0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN last_daily TEXT")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN photo_url TEXT")
        except: pass
        try: conn.execute("ALTER TABLE promocodes ADD COLUMN min_donation_24h INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE promocodes ADD COLUMN expires_at TEXT")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN tickets INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN admin_luck INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE users ADD COLUMN total_spent INTEGER DEFAULT 0")
        except: pass
        
        # Ensure default tasks exist
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tasks")
        if cur.fetchone()[0] <= 2: # Check if we need to add more or refresh
            # Clear and re-insert for consistency in this update
            cur.execute("DELETE FROM tasks")
            cur.execute("INSERT INTO tasks (title, reward, type, url, chat_id) VALUES (?, ?, ?, ?, ?)",
                        ("Подписка на канал", 100, "channel", "https://t.me/ScreamCase", "@ScreamCase"))
            cur.execute("INSERT INTO tasks (title, reward, type, url) VALUES (?, ?, ?, ?)",
                        ("Пригласить 5 друзей", 500, "referral_5", ""))
            cur.execute("INSERT INTO tasks (title, reward, type, url, chat_id) VALUES (?, ?, ?, ?, ?)",
                        ("Вступить в наш чат", 1, "chat", "https://t.me/ScreamCaseChat", "@ScreamCaseChat"))
            cur.execute("INSERT INTO tasks (title, reward, type, url) VALUES (?, ?, ?, ?)",
                        ("Открыть 1 бесплатный кейс", 1, "open_free", ""))
            cur.execute("INSERT INTO tasks (title, reward, type, url) VALUES (?, ?, ?, ?)",
                        ("Пригласить 1 друга", 1, "referral_1", ""))
            conn.commit()

    print("✅ База данных полностью готова")

# --- CASE DATA (Server Side) ---
CASES_DATA = {
    1: {'min': 0, 'max': 667},    # Promo Case
    2: {'min': 0, 'max': 100},    # Daily Case
    3: {'min': 100, 'max': 667},  # Snoop Case
    4: {'min': 200, 'max': 599},  # Lover's Case
    5: {'min': 0, 'max': 199},    # Hobo Case
    6: {'min': 0, 'max': 50},     # Risky Box
    7: {'min': 0, 'max': 599},    # Scam Box
    8: {'min': 100, 'max': 444},  # Ebati Case
    9: {'min': 50, 'max': 222},   # Pussy Case
    10: {'min': 100, 'max': 250}  # Skolnik Case
}

# This list matches giftData.js
ALL_GIFTS = [
  {"price": 15, "name": "Bear", "image": "/asset/Gifts/15S_Bear.png"},
  {"price": 25, "name": "Rosae", "image": "/asset/Gifts/25S_Rosae.png"},
  {"price": 40, "name": "Lol Pops", "image": "/asset/Gifts/40S_Lol Pops.png"},
  {"price": 50, "name": "Cake", "image": "/asset/Gifts/50S_Cake.png"},
  {"price": 50, "name": "GiftBox", "image": "/asset/Gifts/50S_GiftBox.png"},
  {"price": 100, "name": "Flowers", "image": "/asset/Gifts/100S_Flowers.png"},
  {"price": 300, "name": "Instant Ramens", "image": "/asset/Gifts/300S_Instant Ramens.png"},
  {"price": 300, "name": "Xmas Stockings", "image": "/asset/Gifts/300S_Xmas Stockings.png"},
  {"price": 320, "name": "Spring Baskets", "image": "/asset/Gifts/320S_Spring Baskets.png"},
  {"price": 330, "name": "Swag Bags", "image": "/asset/Gifts/330S_Swag Bags.png"},
  {"price": 340, "name": "Winter Wreaths", "image": "/asset/Gifts/340S_Winter Wreaths.png"},
  {"price": 350, "name": "Jester Hats", "image": "/asset/Gifts/350S_Jester Hats.png"},
  {"price": 380, "name": "Hex Pots", "image": "/asset/Gifts/380S_Hex Pots.png"},
  {"price": 400, "name": "Easter Eggs", "image": "/asset/Gifts/400S_Easter Eggs.png"},
  {"price": 400, "name": "Pool Floats", "image": "/asset/Gifts/400S_Pool Floats.png"},
  {"price": 400, "name": "Restless Jars", "image": "/asset/Gifts/400S_Restless Jars.png"},
  {"price": 400, "name": "Witch Hats", "image": "/asset/Gifts/400S_Witch Hats.png"},
  {"price": 420, "name": "Magic Potions", "image": "/asset/Gifts/420S_Magic Potions.png"},
  {"price": 420, "name": "Snoop Cigars", "image": "/asset/Gifts/420S_Snoop Cigars.png"},
  {"price": 430, "name": "Desk Calendars", "image": "/asset/Gifts/430S_Desk Calendars.png"},
  {"price": 430, "name": "Love Potions", "image": "/asset/Gifts/430S_Love Potions.png"},
  {"price": 440, "name": "Fresh Socks", "image": "/asset/Gifts/440S_Fresh Socks.png"},
  {"price": 440, "name": "Westside Signs", "image": "/asset/Gifts/440S_Westside Signs.png"},
  {"price": 450, "name": "Top Hats", "image": "/asset/Gifts/450S_Top Hats.png"},
  {"price": 480, "name": "Vice Creams", "image": "/asset/Gifts/480S_Vice Creams.png"},
  {"price": 500, "name": "Ice Creams", "image": "/asset/Gifts/500S_Ice Creams.png"},
  {"price": 500, "name": "Jolly Chimps", "image": "/asset/Gifts/500S_Jolly Chimps.png"},
  {"price": 500, "name": "Sakura Flowers", "image": "/asset/Gifts/500S_Sakura Flowers.png"},
  {"price": 500, "name": "Swiss Watches", "image": "/asset/Gifts/500S_Swiss Watches.png"},
  {"price": 510, "name": "Input Keys", "image": "/asset/Gifts/510S_Input Keys.png"},
  {"price": 550, "name": "Scared Cats", "image": "/asset/Gifts/550S_Scared Cats.png"},
  {"price": 555, "name": "Clover Pins", "image": "/asset/Gifts/555S_Clover Pins.png"},
  {"price": 600, "name": "Lush Bouquets", "image": "/asset/Gifts/600S_Lush Bouquets.png"},
  {"price": 600, "name": "Victory Medals", "image": "/asset/Gifts/600S_Victory Medals.png"},
  {"price": 605, "name": "Hypno Lollipops", "image": "/asset/Gifts/605S_Hypno Lollipops.png"},
  {"price": 650, "name": "Valentine Boxes", "image": "/asset/Gifts/650S_Valentine Boxes.png"},
  {"price": 666, "name": "Voodoo Dolls", "image": "/asset/Gifts/666S_Voodoo Dolls.png"},
  {"price": 700, "name": "Heroic Helmets", "image": "/asset/Gifts/700S_Heroic Helmets.png"},
  {"price": 705, "name": "Cookie Hearts", "image": "/asset/Gifts/705S_Cookie Hearts.png"},
  {"price": 750, "name": "Moon Pendants", "image": "/asset/Gifts/750S_Moon Pendants.png"},
  {"price": 777, "name": "Trapped Hearts", "image": "/asset/Gifts/777S_Trapped Hearts.png"},
  {"price": 800, "name": "Snake Boxes", "image": "/asset/Gifts/800S_Snake Boxes.png"},
  {"price": 800, "name": "Tama Gadgets", "image": "/asset/Gifts/800S_Tama Gadgets.png"},
  {"price": 850, "name": "Bunny Muffins", "image": "/asset/Gifts/850S_Bunny Muffins.png"},
  {"price": 880, "name": "Faith Amulets", "image": "/asset/Gifts/880S_Faith Amulets.png"},
  {"price": 900, "name": "Bonded Rings", "image": "/asset/Gifts/900S_Bonded Rings.png"},
  {"price": 900, "name": "Timeless Books", "image": "/asset/Gifts/900S_Timeless Books.png"},
  {"price": 950, "name": "Crystal Balls", "image": "/asset/Gifts/950S_Crystal Balls.png"},
  {"price": 950, "name": "Hearth", "image": "/asset/Gifts/950S_Hearth.png"},
  {"price": 950, "name": "Holiday Drinks", "image": "/asset/Gifts/950S_Holiday Drinks.png"},
  {"price": 990, "name": "Vintage Cigars", "image": "/asset/Gifts/990S_Vintage Cigars.png"},
  {"price": 1000, "name": "Artisan Bricks", "image": "/asset/Gifts/1000S_Artisan Bricks.png"},
  {"price": 1100, "name": "Electric Skulls", "image": "/asset/Gifts/1100S_Electric Skulls.png"},
  {"price": 1100, "name": "Gem Signets", "image": "/asset/Gifts/1100S_Gem Signets.png"},
  {"price": 1100, "name": "Neko Helmets", "image": "/asset/Gifts/1100S_Neko Helmets.png"},
  {"price": 1200, "name": "Diamond Rings", "image": "/asset/Gifts/1200S_Diamond Rings.png"},
  {"price": 1200, "name": "Heart Lockets", "image": "/asset/Gifts/1200S_Heart Lockets.png"},
  {"price": 1200, "name": "Star Notepads", "image": "/asset/Gifts/1200S_Star Notepads.png"},
  {"price": 1300, "name": "Astral Shards", "image": "/asset/Gifts/1300S_Astral Shards.png"},
  {"price": 1300, "name": "Signet Rings", "image": "/asset/Gifts/1300S_Signet Rings.png"},
  {"price": 1300, "name": "Skull Flowers", "image": "/asset/Gifts/1300S_Skull Flowers.png"},
  {"price": 1400, "name": "Ion Gems", "image": "/asset/Gifts/1400S_Ion Gems.png"},
  {"price": 1400, "name": "Party Sparklers", "image": "/asset/Gifts/1400S_Party Sparklers.png"},
  {"price": 1500, "name": "Berry Boxes", "image": "/asset/Gifts/1500S_Berry Boxes.png"},
  {"price": 1500, "name": "Cupid Charms", "image": "/asset/Gifts/1500S_Cupid Charms.png"},
  {"price": 1500, "name": "Mighty Arms", "image": "/asset/Gifts/1500S_Mighty Arms.png"},
  {"price": 1500, "name": "Santa Hats", "image": "/asset/Gifts/1500S_Santa Hats.png"},
  {"price": 1600, "name": "Sky Stilettos", "image": "/asset/Gifts/1600S_Sky Stilettos.png"},
  {"price": 1800, "name": "Rare Birds", "image": "/asset/Gifts/1800S_Rare Birds.png"},
  {"price": 1800, "name": "Snow Mittens", "image": "/asset/Gifts/1800S_Snow Mittens.png"},
  {"price": 1900, "name": "Mood Packs", "image": "/asset/Gifts/1900S_Mood Packs.png"},
  {"price": 2000, "name": "Light Swords", "image": "/asset/Gifts/2000S_Light Swords.png"},
  {"price": 2026, "name": "Big Years", "image": "/asset/Gifts/2026S_Big Years.png"},
  {"price": 2100, "name": "Hanging Stars", "image": "/asset/Gifts/2100S_Hanging Stars.png"},
  {"price": 2100, "name": "Record Players", "image": "/asset/Gifts/2100S_Record Players.png"},
  {"price": 2200, "name": "Jingle Bells", "image": "/asset/Gifts/2200S_Jingle Bells.png"},
  {"price": 2200, "name": "Mini Oscars", "image": "/asset/Gifts/2200S_Mini Oscars.png"},
  {"price": 2300, "name": "Spy Agarics", "image": "/asset/Gifts/2300S_Spy Agarics.png"},
  {"price": 2400, "name": "Sleigh Bells", "image": "/asset/Gifts/2400S_Sleigh Bells.png"},
  {"price": 2500, "name": "Loot Bags", "image": "/asset/Gifts/2500S_Loot Bags.png"},
  {"price": 2600, "name": "Precious Peaches", "image": "/asset/Gifts/2600S_Precious Peaches.png"},
  {"price": 2800, "name": "Kissed Frogs", "image": "/asset/Gifts/2800S_Kissed Frogs.png"},
  {"price": 3100, "name": "Mad Pumpkins", "image": "/asset/Gifts/3100S_Mad Pumpkins.png"},
  {"price": 3300, "name": "Ionic Dryers", "image": "/asset/Gifts/3300S_Ionic Dryers.png"},
  {"price": 3500, "name": "Money Pots", "image": "/asset/Gifts/3500S_Money Pots.png"},
  {"price": 4500, "name": "Flying Brooms", "image": "/asset/Gifts/4500S_Flying Brooms.png"},
  {"price": 4799, "name": "Toy Bears", "image": "/asset/Gifts/4799S_Toy Bears.png"},
  {"price": 5000, "name": "Genie Lamps", "image": "/asset/Gifts/5000S_Genie Lamps.png"},
  {"price": 7500, "name": "Low Riders", "image": "/asset/Gifts/7500S_Low Riders.png"},
  {"price": 12595, "name": "Nail Bracelets", "image": "/asset/Gifts/12595S_Nail Bracelets.png"},
  {"price": 19047, "name": "Stellar Rockets", "image": "/asset/Gifts/19047S_Stellar Rockets.png"},
]

def get_gifts_in_range(min_p, max_p):
    return [g for g in ALL_GIFTS if g['price'] >= min_p and g['price'] <= max_p]

def register_or_get(user_id, username=None, first_name=None, photo_url=None, referred_by=None):
    """Register user if new, or return existing user data. Always update profile."""
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT stars, join_date, admin_luck FROM users WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        
        if res:
            # Update profile info on every call
            update_user_profile(user_id, username, first_name, photo_url)
            return res, False
        
        # New user registration
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Validate referred_by (cannot refer self, must exist)
        ref_id = None
        if referred_by and str(referred_by).isdigit():
            ref_id = int(referred_by)
            if ref_id == user_id:
                ref_id = None
            else:
                cur.execute("SELECT user_id FROM users WHERE user_id = ?", (ref_id,))
                if not cur.fetchone():
                    ref_id = None

        cur.execute("""INSERT INTO users 
                       (user_id, stars, join_date, username, first_name, photo_url, referred_by, tickets, admin_luck) 
                       VALUES (?, 0, ?, ?, ?, ?, ?, 0, 0)""", 
                     (user_id, date, username, first_name, photo_url, ref_id))
        
        # If referred, give the referrer a ticket
        if ref_id:
            cur.execute("UPDATE users SET tickets = tickets + 1 WHERE user_id = ?", (ref_id,))
            logger.info(f"User {user_id} joined via referral {ref_id}. Referrer got 1 ticket.")
            # We will notify referrer in start_cmd
            
        conn.commit()
        return (0, date), True

def update_user_profile(user_id, username=None, first_name=None, photo_url=None):
    """Update user profile information."""
    with sqlite3.connect('database.db') as conn:
        updates = []
        params = []
        
        if username:
            updates.append("username = ?")
            params.append(username)
        if first_name:
            updates.append("first_name = ?")
            params.append(first_name)
        if photo_url:
            updates.append("photo_url = ?")
            params.append(photo_url)
        
        if updates:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            conn.execute(query, tuple(params))
            conn.commit()

def update_balance(user_id, amount, mode="add", is_donation=False):
    with sqlite3.connect('database.db') as conn:
        if mode == "add":
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id))
            if is_donation:
                conn.execute("UPDATE users SET total_donated_stars = total_donated_stars + ? WHERE user_id = ?", (amount, user_id))
                
                # Referral reward: 10%
                user_res = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
                if user_res and user_res[0]:
                    ref_id = user_res[0]
                    reward = int(amount * 0.1)
                    if reward > 0:
                        conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (reward, ref_id))
                        conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                                     (ref_id, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        logger.info(f"Referrer {ref_id} got {reward} stars from {user_id}'s donation")
                        # Try to notify referrer (async task might be better, but we are inside synchronous db helper)
                        # We will handle notification in api handlers or bot handlers
        else:
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (amount, user_id))
        
        conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                     (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

# --- ЦЕНЫ КЕЙСОВ ---
CASES_PRICES = {
    1: 0,   # Promo Case
    2: 0,   # Daily Case
    3: 667, # Snoop Case
    4: 599, # Lover's Case
    5: 199, # Hobo Case
    6: 50,  # Risky Box
    7: 111, # Scam Box
    8: 444, # Ebati Case
    9: 222, # Pussy Case
    10: 250 # Skolnik Case
}

# --- ОБРАБОТКА КОМАНД ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    """Handle /start command - register user and show main menu"""
    try:
        referred_by = command.args if command.args else None
        
        # Register/update user profile
        data, is_new = register_or_get(
            message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            photo_url=message.from_user.photo_url if hasattr(message.from_user, 'photo_url') else None,
            referred_by=referred_by
        )
        
        if is_new:
            logger.info(f"New user registered: {message.from_user.id} - {message.from_user.full_name}")
            # Notify all admins
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, 
                        f"🚀 **Новый пользователь!**\n\n👤 Имя: {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n🏷 Юзернейм: @{message.from_user.username}", 
                        parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")
            
            # Notify referrer
            if referred_by and str(referred_by).isdigit():
                ref_id = int(referred_by)
                if ref_id != message.from_user.id:
                    try:
                        await bot.send_message(ref_id, f"🎉 По вашей ссылке перешел новый пользователь! Вы получили +1 билет 🎫")
                    except Exception as e:
                        logger.error(f"Failed to notify referrer: {e}")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Открыть ScreamCase", web_app=WebAppInfo(url=APP_URL))],
            [InlineKeyboardButton(text="📢 Канал", url=CHANNEL_URL)]
        ])
        await message.answer(f"Привет! Твой баланс: {data[0]} ⭐", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error in start_cmd: {e}")
        await message.answer("❌ Ошибка при запуске. Попробуйте позже.")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    """Handle /help command - show available commands"""
    try:
        text = "📖 **Команды бота**\n\n"
        text += "• `/start` — Запуск приложения\n"
        text += "• `/help` — Справка по командам\n"
        
        if message.from_user.id in ADMIN_IDS:
            text += "\n🛠 **Админ-панель:**\n"
            text += "• `/+ <число>` — Добавить себе звезд\n"
            text += "• `/setbalance <ID> <число>` — Установить баланс пользователю\n"
            text += "• `/user <ID>` — Информация об игроке\n"
            text += "• `/stats` — Общая статистика\n"
            text += "• `/addpromo <код|random> <часы> <мин_звезд_24ч> <награда>` — Создать промокод\n"
            text += "• `/broadcast` — Рассылка сообщений\n"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")
        await message.answer("❌ Ошибка при получении справки.")

@dp.message(Command("addpromo"))
async def admin_add_promo(message: types.Message, command: CommandObject):
    """
    Handle /addpromo [название ИЛИ word random] [длительность в часах] [мин. сумма пополнения в звёздах] [награда]
    """
    try:
        if message.from_user.id not in ADMIN_IDS:
            return
        
        if not command.args:
            await message.answer("❌ Пример: `/addpromo mypromo 24 100 500` (код, часы, мин. звезды за 24ч, награда)", parse_mode="Markdown")
            return
            
        args = command.args.split()
        if len(args) < 4:
            await message.answer("❌ Недостаточно аргументов. Пример: `/addpromo random 24 100 500`", parse_mode="Markdown")
            return
            
        code_input = args[0]
        hours = int(args[1])
        min_stars = int(args[2])
        reward = int(args[3])
        
        if code_input.lower() == "random":
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        else:
            code = code_input.upper()
            
        expires_at = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        
        with sqlite3.connect('database.db') as conn:
            conn.execute(
                "INSERT INTO promocodes (code, reward, type, active, min_donation_24h, expires_at) VALUES (?, ?, 'stars', 1, ?, ?)",
                (code, reward, min_stars, expires_at)
            )
            conn.commit()
            
        await message.answer(f"✅ Промокод создан!\n\n🎫 Код: `{code}`\n💰 Награда: `{reward}` ⭐\n⏳ Длительность: `{hours}` ч.\n⭐ Мин. пополнение: `{min_stars}` (за 24ч)", parse_mode="Markdown")
        
    except sqlite3.IntegrityError:
        await message.answer("❌ Такой промокод уже существует.")
    except Exception as e:
        logger.error(f"Error in admin_add_promo: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("+"))
async def admin_add(message: types.Message):
    """Handle /+ command - add stars to admin account"""
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Пример: `/+ 100`", parse_mode="Markdown")
            return
        
        amount = int(parts[1])
        if amount <= 0:
            await message.answer("❌ Количество должно быть > 0.")
            return
        
        update_balance(message.from_user.id, amount, "add")
        logger.info(f"Admin {message.from_user.id} added {amount} stars to themselves")
        await message.answer(f"✅ Добавлено {amount} ⭐")
    except ValueError:
        await message.answer("❌ Некорректное число. Пример: `/+ 100`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_add: {e}")
        await message.answer("❌ Ошибка при добавлении звезд.")

@dp.message(Command("setbalance"))
async def admin_set(message: types.Message):
    """Handle /setbalance command - set user balance"""
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❌ Пример: `/setbalance 123456 500`", parse_mode="Markdown")
            return
        
        target_id = int(parts[1])
        amount = int(parts[2])
        
        if amount < 0:
            await message.answer("❌ Количество не может быть отрицательным.")
            return
        
        update_balance(target_id, amount, "set")
        logger.info(f"Admin {message.from_user.id} set balance for {target_id} to {amount}")
        await message.answer(f"✅ Баланс ID `{target_id}` установлен на `{amount}` ⭐", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Некорректные параметры.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_set: {e}")
        await message.answer("❌ Ошибка при установке баланса.")

@dp.message(Command("user"))
async def admin_user_info(message: types.Message):
    """Handle /user command - show user info"""
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Пример: `/user 123456`", parse_mode="Markdown")
            return
        
        user_id = int(parts[1])
        with sqlite3.connect('database.db') as conn:
            user = conn.execute(
                "SELECT user_id, stars, join_date, total_donated_stars, total_donated_ton, tickets FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
        
        if not user:
            await message.answer(f"❌ Пользователь `{user_id}` не найден.", parse_mode="Markdown")
            return
        
        text = f"""👤 **Информация о пользователе**
🆔 ID: `{user[0]}`
⭐ Баланс: `{user[1]}`
🎫 Билеты: `{user[5]}`
📅 Дата присоединения: `{user[2]}`
💎 Всего пожертвовано звёзд: `{user[3]}`
💰 Всего пожертвовано TON: `{user[4]:.4f}`"""
        await message.answer(text, parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_user_info: {e}")
        await message.answer("❌ Ошибка при получении информации.")

@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    """Handle /stats command - show global statistics"""
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        
        with sqlite3.connect('database.db') as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_stars = conn.execute("SELECT SUM(stars) FROM users").fetchone()[0] or 0
            total_donated = conn.execute("SELECT SUM(total_donated_stars) FROM users").fetchone()[0] or 0
            total_ton = conn.execute("SELECT SUM(total_donated_ton) FROM users").fetchone()[0] or 0
        
        text = f"""📊 **Глобальная статистика**
👥 Всего пользователей: `{total_users}`
⭐ Звёзд в системе: `{total_stars}`
💎 Всего пожертвовано звёзд: `{total_donated}`
💰 Всего пожертвовано TON: `{total_ton:.4f}`"""
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await message.answer("❌ Ошибка при получении статистики.")

@dp.message(Command("Chance"))
async def admin_chance(message: types.Message):
    """Handle /Chance [0-100] command - set admin luck"""
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Пример: `/Chance 100`", parse_mode="Markdown")
            return
        
        luck = int(parts[1])
        if not (0 <= luck <= 100):
            await message.answer("❌ Значение должно быть от 0 до 100.")
            return
        
        with sqlite3.connect('database.db') as conn:
            conn.execute("UPDATE users SET admin_luck = ? WHERE user_id = ?", (luck, message.from_user.id))
            conn.commit()
        
        logger.info(f"Admin {message.from_user.id} set their luck to {luck}")
        await message.answer(f"🎰 God Mode: Luck set to `{luck}%`", parse_mode="Markdown")
    except (ValueError, IndexError):
        await message.answer("❌ Некорректное число. Пример: `/Chance 100`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_chance: {e}")
        await message.answer("❌ Ошибка при установке удачи.")

async def check_membership(user_id: int):
    """Check if user is a member of the linked channel"""
    try:
        member = await bot.get_chat_member(chat_id="@ScreamCase", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership for {user_id}: {e}")
        return False

# --- API ДЛЯ САЙТА ---

async def api_check_sub(request):
    """GET /api/check_sub?user_id=... - Check if user is subscribed to channel"""
    try:
        uid = request.query.get("user_id")
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        is_member = await check_membership(int(uid))
        return web.json_response({"is_subscribed": is_member})
    except Exception as e:
        logger.error(f"Error in api_check_sub: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_get_tasks(request):
    """GET /api/tasks?user_id=... - Get available tasks for user"""
    try:
        uid = request.query.get("user_id")
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        with sqlite3.connect('database.db') as conn:
            # Get tasks not completed by user
            res = conn.execute("""
                SELECT id, title, reward, type, url FROM tasks 
                WHERE id NOT IN (SELECT task_id FROM user_tasks WHERE user_id = ?)
            """, (uid,)).fetchall()
            
        tasks = [{"id": r[0], "title": r[1], "reward": r[2], "type": r[3], "url": r[4]} for r in res]
        return web.json_response(tasks)
    except Exception as e:
        logger.error(f"Error in api_get_tasks: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_verify_task(request):
    """POST /api/tasks/verify - Verify task completion and give reward"""
    try:
        data = await request.json()
        uid = data.get("user_id")
        tid = data.get("task_id")
        
        if not uid or not tid: return web.json_response({"error": "invalid_data"}, status=400)
        
        uid, tid = int(uid), int(tid)
        
        with sqlite3.connect('database.db') as conn:
            # Check if already completed
            completed = conn.execute("SELECT 1 FROM user_tasks WHERE user_id = ? AND task_id = ?", (uid, tid)).fetchone()
            if completed:
                return web.json_response({"error": "already_completed"}, status=400)
            
            task = conn.execute("SELECT title, reward, type, chat_id FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not task:
                return web.json_response({"error": "task_not_found"}, status=404)
            
            title, reward, ttype, chat_id = task
            is_valid = False
            
            if ttype == "channel":
                is_valid = await check_membership(uid)
            elif ttype == "chat":
                # Check membership in chat
                try:
                    member = await bot.get_chat_member(chat_id=chat_id or "@ScreamCaseChat", user_id=uid)
                    is_valid = member.status in ["member", "administrator", "creator"]
                except:
                    is_valid = False
            elif ttype == "referral_5":
                # Check if user has at least 5 referrals
                ref_count = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,)).fetchone()[0]
                if ref_count >= 5:
                    is_valid = True
            elif ttype == "referral_1":
                # Check if user has at least 1 referral
                ref_count = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,)).fetchone()[0]
                if ref_count >= 1:
                    is_valid = True
            elif ttype == "open_free":
                # Check if user has opened at least 1 case (free cases have price 0 or 1)
                # We can check transactions or payments
                opened = conn.execute("SELECT COUNT(*) FROM payments WHERE user_id = ? AND amount = 0", (uid,)).fetchone()[0]
                if opened >= 1:
                    is_valid = True
            else:
                # Custom or simple tasks (just click)
                is_valid = True
                
            if is_valid:
                conn.execute("INSERT INTO user_tasks (user_id, task_id) VALUES (?, ?)", (uid, tid))
                conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (reward, uid))
                conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                             (uid, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                logger.info(f"User {uid} completed task {tid} ({title}) and got {reward} stars")
                return web.json_response({"success": True, "reward": reward})
            else:
                return web.json_response({"error": "task_not_met"}, status=400)
                
    except Exception as e:
        logger.error(f"Error in api_verify_task: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_balance(request):
    """GET /api/balance - Get user balance and tickets"""
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            res = conn.execute("SELECT stars, tickets, total_donated_stars, total_spent FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        
        if not res:
            return web.json_response({"stars": 0, "tickets": 0, "donor": 0, "spent": 0})
            
        return web.json_response({
            "stars": res[0], 
            "tickets": res[1],
            "donor": res[2],
            "spent": res[3]
        })
    except ValueError:
        return web.json_response({"error": "invalid_user_id"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_balance: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_referrals(request):
    """GET /api/user/referrals - Get user referrals count and list"""
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        with sqlite3.connect('database.db') as conn:
            res = conn.execute(
                "SELECT user_id, username, first_name, photo_url, total_donated_stars FROM users WHERE referred_by = ?",
                (uid,)
            ).fetchall()
        
        referrals = [
            {
                "user_id": r[0],
                "username": r[1],
                "first_name": r[2],
                "photo_url": r[3],
                "donated": r[4]
            } for r in res
        ]
        
        return web.json_response({
            "count": len(referrals),
            "referrals": referrals
        })
    except ValueError:
        return web.json_response({"error": "invalid_user_id"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_referrals: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_leaderboard(request):
    """GET /api/leaderboard - Get top 10 donors (excluding admins)"""
    try:
        # Exclude IDs 7782281997 and 5396975347
        exclude_ids = ",".join(map(str, ADMIN_IDS))
        
        with sqlite3.connect('database.db') as conn:
            res = conn.execute(
                f"SELECT user_id, username, first_name, photo_url, total_donated_stars FROM users "
                f"WHERE user_id NOT IN ({exclude_ids}) "
                f"ORDER BY total_donated_stars DESC LIMIT 10"
            ).fetchall()
        
        leaderboard = [
            {
                "user_id": r[0], 
                "username": r[1], 
                "first_name": r[2], 
                "photo_url": r[3], 
                "donated": r[4]
            } for r in res
        ]
        return web.json_response(leaderboard)
    except Exception as e:
        logger.error(f"Error in api_leaderboard: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_wheel_spin(request):
    """
    POST /api/wheel/spin - Spin the wheel of fortune
    """
    try:
        data = await request.json()
        uid = data.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        cost = 50
        
        # Fixed segments for the wheel (Server-side defined)
        # 12 segments as per SEGMENT_ANGLE = 360 / 12
        SEGMENTS = [15, 50, 20, 100, 25, 200, 30, 300, 40, 500, 50, 150]
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars, admin_luck FROM users WHERE user_id = ?", (uid,)).fetchone()
            if not user:
                return web.json_response({"error": "user_not_found"}, status=404)
            
            balance, admin_luck = user
            if balance < cost:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            is_god_mode = False
            if uid in ADMIN_IDS and admin_luck > 0:
                if random.random() * 100 < admin_luck:
                    is_god_mode = True

            if is_god_mode:
                # Force max prize (500 is at index 9)
                prize = 500
                prize_index = 9
            else:
                rand = random.random() * 100
                if rand < 0.8: # <1% - Jackpot (500)
                    prize_index = 9
                elif rand < 15: # ~14% - Mid (100, 150, 200, 300)
                    prize_index = random.choice([3, 5, 7, 11])
                else: # ~85% - Common
                    prize_index = random.choice([0, 1, 2, 4, 6, 8, 10])
                
                prize = SEGMENTS[prize_index]
            
            # Deduct cost and add prize
            # Admin God Mode Refund: Credit spent stars back (cost is effectively 0)
            if is_god_mode:
                new_balance = balance + prize # cost not deducted
            else:
                new_balance = balance - cost + prize
                conn.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (cost, uid))
                
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (new_balance, uid))
            if not is_god_mode:
                conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                             (uid, -cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, prize, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
            logger.info(f"User {uid} spun wheel: won {prize} (index {prize_index}). God Mode: {is_god_mode}")
            
        return web.json_response({
            "success": True,
            "win_amount": prize,
            "prize_index": prize_index,
            "new_balance": new_balance,
            "god_mode": is_god_mode
        })
    except Exception as e:
        logger.error(f"Error in api_wheel_spin: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_open_case(request):
    """
    POST /api/open_case - Open a case (paid or free)
    """
    try:
        data = await request.json()
        uid = data.get("user_id")
        case_id = data.get("case_id")
        
        if not uid or case_id is None:
            return web.json_response({"error": "invalid_data"}, status=400)
        
        case_id = int(case_id)
        price = CASES_PRICES.get(case_id)
        
        if price is None:
            return web.json_response({"error": "invalid_case"}, status=400)
        
        if case_id == 2: return await _handle_claim_daily(uid)
        if case_id == 1: return await _handle_claim_promo(uid, data.get("code"))
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars, admin_luck FROM users WHERE user_id = ?", (int(uid),)).fetchone()
            if not user: return web.json_response({"error": "user_not_found"}, status=404)
            
            balance, admin_luck = user
            if balance < price:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            is_god_mode = False
            if int(uid) in ADMIN_IDS and admin_luck > 0:
                if random.random() * 100 < admin_luck:
                    is_god_mode = True

            # Get case range
            case_info = CASES_DATA.get(case_id)
            if not case_info:
                return web.json_response({"error": "case_data_missing"}, status=500)
            
            drop_items = get_gifts_in_range(case_info['min'], case_info['max'])
            if not drop_items:
                drop_items = ALL_GIFTS[:10] # Fallback
            
            if is_god_mode:
                # Force best item (highest price)
                won_item = max(drop_items, key=lambda x: x['price'])
            else:
                # Regular generation logic
                cheap = [i for i in drop_items if i['price'] <= 50]
                mid = [i for i in drop_items if 50 < i['price'] <= 150]
                jackpot = [i for i in drop_items if i['price'] > 150]
                
                rand = random.random() * 100
                if rand < 85 and cheap:
                    won_item = random.choice(cheap)
                elif rand < 97 and mid:
                    won_item = random.choice(mid)
                elif jackpot:
                    won_item = random.choice(jackpot)
                else:
                    won_item = random.choice(drop_items)

            # Deduct if not God Mode
            if not is_god_mode:
                conn.execute("UPDATE users SET stars = stars - ?, total_spent = total_spent + ? WHERE user_id = ?", (price, price, uid))
                conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                             (int(uid), -price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            logger.info(f"User {uid} opened case {case_id}: won {won_item['name']} ({won_item['price']}). God Mode: {is_god_mode}")
        
        return web.json_response({
            "success": True, 
            "item": won_item,
            "deducted": 0 if is_god_mode else price, 
            "god_mode": is_god_mode
        })
    except Exception as e:
        logger.error(f"Error in api_open_case: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_upgrade(request):
    """
    POST /api/upgrade - Upgrade item
    """
    try:
        data = await request.json()
        uid = data.get("user_id")
        cost = int(data.get("cost", 0))
        chance = float(data.get("chance", 0))
        
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars, admin_luck FROM users WHERE user_id = ?", (int(uid),)).fetchone()
            if not user: return web.json_response({"error": "user_not_found"}, status=404)
            
            balance, admin_luck = user
            if balance < cost:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            is_god_mode = False
            if int(uid) in ADMIN_IDS and admin_luck > 0:
                if random.random() * 100 < admin_luck:
                    is_god_mode = True
            
            success = is_god_mode or (random.random() * 100 < chance)
            
            if not is_god_mode:
                conn.execute("UPDATE users SET stars = stars - ?, total_spent = total_spent + ? WHERE user_id = ?", (cost, cost, uid))
                conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                             (int(uid), -cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            
        return web.json_response({"success": success, "god_mode": is_god_mode})
    except Exception as e:
        logger.error(f"Error in api_upgrade: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def _handle_claim_daily(uid):
    """
    Claim daily free case
    SECURITY: 24h cooldown is STRICT - checked before update
    """
    try:
        uid = int(uid)
        now = datetime.now()
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", (uid,)).fetchone()
            
            if not user:
                return web.json_response({"error": "user_not_found"}, status=404)
            
            last_daily_str = user[0]
            
            # Check 24h cooldown
            if last_daily_str:
                try:
                    last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
                    time_diff = (now - last_daily).total_seconds()
                    
                    if time_diff < 86400:  # 24 hours = 86400 seconds
                        wait_seconds = int(86400 - time_diff)
                        logger.info(f"User {uid} attempted daily claim too soon. Wait: {wait_seconds}s")
                        return web.json_response({
                            "error": "daily_cooldown_active",
                            "wait_seconds": wait_seconds
                        }, status=403)
                except ValueError:
                    # Invalid datetime format, treat as never claimed
                    pass
            
            # Update last_daily timestamp
            conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", 
                        (now.strftime("%Y-%m-%d %H:%M:%S"), uid))
            conn.commit()
            
            logger.info(f"User {uid} claimed daily case")
        
        return web.json_response({"success": True})
    
    except ValueError as e:
        logger.error(f"ValueError in _handle_claim_daily: {e}")
        return web.json_response({"error": "invalid_data"}, status=400)
    except Exception as e:
        logger.error(f"Error in _handle_claim_daily: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def _handle_claim_promo(uid, code):
    """
    Claim promo code reward
    SECURITY CHECKS:
    1. Code must exist in promocodes table
    2. Code must not be expired
    3. Code must be active
    4. User must meet minimum donation requirement (if set)
    5. NO rewards for invalid/random strings
    """
    try:
        uid = int(uid)
        code = str(code).strip().upper()  # Normalize code
        
        if not code or len(code) == 0 or len(code) > 50:
            logger.warning(f"User {uid} attempted invalid promo code: '{code}'")
            return web.json_response({"error": "invalid_code_format"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            # Check 1: Code exists
            promo = conn.execute(
                "SELECT reward, type, active, min_donation_24h, expires_at FROM promocodes WHERE UPPER(code) = ?",
                (code,)
            ).fetchone()
            
            if not promo:
                logger.warning(f"User {uid} attempted non-existent promo code: {code}")
                return web.json_response({"error": "invalid_code"}, status=404)
            
            reward, promo_type, is_active, min_donation_24h, expires_at = promo
            
            # Check 2: Code must be active
            if not is_active:
                logger.warning(f"User {uid} attempted inactive promo code: {code}")
                return web.json_response({"error": "code_inactive"}, status=403)
            
            # Check 3: Code must not be expired
            if expires_at:
                try:
                    expiry_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() > expiry_dt:
                        logger.warning(f"User {uid} attempted expired promo code: {code}")
                        return web.json_response({"error": "code_expired"}, status=403)
                except ValueError:
                    logger.error(f"Invalid expires_at format for promo {code}")
                    return web.json_response({"error": "server_error"}, status=500)
            
            # Check 4: Minimum donation requirement
            if min_donation_24h > 0:
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                donated_result = conn.execute(
                    "SELECT SUM(amount) FROM payments WHERE user_id = ? AND date > ? AND amount > 0",
                    (uid, yesterday)
                ).fetchone()
                
                donated_amount = donated_result[0] or 0
                
                if donated_amount < min_donation_24h:
                    logger.warning(f"User {uid} doesn't meet min donation for promo {code}. Required: {min_donation_24h}, Donated: {donated_amount}")
                    return web.json_response({
                        "error": "minimum_donation_required",
                        "required": min_donation_24h,
                        "current": donated_amount
                    }, status=403)
            
            # All checks passed - grant reward
            if promo_type == "stars":
                conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (reward, uid))
                conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                            (uid, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                
                logger.info(f"User {uid} claimed promo code {code} for {reward} stars")
            else:
                logger.warning(f"Unknown promo type for code {code}: {promo_type}")
                return web.json_response({"error": "invalid_reward_type"}, status=500)
        
        return web.json_response({"success": True, "reward": reward, "type": promo_type})
    
    except ValueError as e:
        logger.error(f"ValueError in _handle_claim_promo: {e}")
        return web.json_response({"error": "invalid_data"}, status=400)
    except Exception as e:
        logger.error(f"Error in _handle_claim_promo: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily(request):
    """POST /api/claim_daily - Claim daily free case"""
    try:
        data = await request.json()
        return await _handle_claim_daily(data.get("user_id"))
    except Exception as e:
        logger.error(f"Error in api_claim_daily: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_promo(request):
    """POST /api/claim_promo - Claim promo code"""
    try:
        data = await request.json()
        return await _handle_claim_promo(data.get("user_id"), data.get("code"))
    except Exception as e:
        logger.error(f"Error in api_claim_promo: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_ton_success(request):
    """
    POST /api/ton_success - Register TON payment
    SECURITY:
    - Transaction hash MUST be unique (checked in ton_transactions table)
    - Transaction is stored BEFORE adding stars
    - Duplicate transactions are REJECTED immediately
    """
    try:
        data = await request.json()
        uid = data.get("user_id")
        amount_ton = data.get("amount")
        tx_hash = data.get("tx_id") or data.get("boc")  # Support tx_id or boc
        
        if not uid or amount_ton is None or not tx_hash:
            logger.warning(f"Incomplete TON payment data: user_id={uid}, amount={amount_ton}, tx_hash={bool(tx_hash)}")
            return web.json_response({"error": "invalid_data"}, status=400)
        
        uid = int(uid)
        
        try:
            amount_ton = float(amount_ton)
            if amount_ton <= 0:
                return web.json_response({"error": "invalid_amount"}, status=400)
        except ValueError:
            return web.json_response({"error": "invalid_amount"}, status=400)
        
        # Hash the transaction to prevent reuse
        tx_hash_normalized = hashlib.sha256(str(tx_hash).encode()).hexdigest()
        
        # Conversion rate: 1 TON = 100 stars (adjustable)
        stars_to_add = int(amount_ton * 100)
        
        with sqlite3.connect('database.db') as conn:
            # Check if transaction was already processed
            existing = conn.execute(
                "SELECT tx_id FROM ton_transactions WHERE tx_id = ?",
                (tx_hash_normalized,)
            ).fetchone()
            
            if existing:
                logger.warning(f"Duplicate TON transaction detected: {tx_hash_normalized}")
                return web.json_response({"error": "transaction_already_processed"}, status=400)
            
            # CRITICAL: Store transaction first
            conn.execute(
                "INSERT INTO ton_transactions (tx_id, user_id, amount, date) VALUES (?, ?, ?, ?)",
                (tx_hash_normalized, uid, amount_ton, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            # THEN add stars to user
            conn.execute(
                "UPDATE users SET stars = stars + ?, total_donated_ton = total_donated_ton + ? WHERE user_id = ?",
                (stars_to_add, amount_ton, uid)
            )
            # Add to payments for promo code checks
            conn.execute(
                "INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)",
                (uid, stars_to_add, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            
            logger.info(f"TON payment processed: User {uid}, {amount_ton} TON = {stars_to_add} stars, TX: {tx_hash_normalized[:16]}...")
        
        # Send notification to user
        try:
            await bot.send_message(uid, f"✅ Пополнение успешно! +{stars_to_add} ⭐")
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")
        
        # Notify admins
        try:
            for admin_id in ADMIN_IDS:
                await bot.send_message(admin_id, f"💰 User {uid} topped up: {amount_ton} TON = {stars_to_add} ⭐")
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
        
        return web.json_response({"success": True, "stars_added": stars_to_add})
    
    except ValueError as e:
        logger.error(f"ValueError in api_ton_success: {e}")
        return web.json_response({"error": "invalid_data"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_ton_success: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_admin_create_promo(request):
    """
    POST /api/admin/create_promo - Create promotional code
    SECURITY: Only admins can create promos (verified by admin_id)
    """
    try:
        data = await request.json()
        admin_id = data.get("admin_id")
        code = data.get("code")
        reward = data.get("reward")
        days = data.get("days", 7)
        min_donation = data.get("min_donation", 0)
        promo_type = data.get("type", "stars")
        
        # Verify admin
        if not admin_id or int(admin_id) not in ADMIN_IDS:
            logger.warning(f"Unauthorized promo creation attempt from user {admin_id}")
            return web.json_response({"error": "unauthorized"}, status=403)
        
        # Validate inputs
        if not code or not isinstance(code, str) or len(code) < 3 or len(code) > 50:
            return web.json_response({"error": "invalid_code"}, status=400)
        
        try:
            reward = int(reward)
            min_donation = int(min_donation)
            days = int(days)
        except (ValueError, TypeError):
            return web.json_response({"error": "invalid_parameters"}, status=400)
        
        if reward <= 0 or days < 0 or min_donation < 0:
            return web.json_response({"error": "invalid_parameters"}, status=400)
        
        code = code.strip().upper()
        expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        with sqlite3.connect('database.db') as conn:
            # Check if code already exists
            existing = conn.execute("SELECT code FROM promocodes WHERE UPPER(code) = ?", (code,)).fetchone()
            if existing:
                logger.warning(f"Admin {admin_id} attempted to create existing promo code: {code}")
                return web.json_response({"error": "code_already_exists"}, status=409)
            
            conn.execute(
                """INSERT INTO promocodes (code, reward, type, active, min_donation_24h, expires_at) 
                   VALUES (?, ?, ?, 1, ?, ?)""",
                (code, reward, promo_type, min_donation, expires_at)
            )
            conn.commit()
            
            logger.info(f"Admin {admin_id} created promo code: {code}, reward={reward}, expires={expires_at}")
        
        return web.json_response({
            "success": True,
            "code": code,
            "reward": reward,
            "expires_at": expires_at
        })
    
    except Exception as e:
        logger.error(f"Error in api_admin_create_promo: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_invoice(request):
    """POST /api/create_invoice - Create Telegram payment invoice"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        amount = data.get("amount")
        
        if not user_id or not amount:
            return web.json_response({"error": "invalid_data"}, status=400)
        
        try:
            amount = int(amount)
            if amount <= 0:
                return web.json_response({"error": "invalid_amount"}, status=400)
        except ValueError:
            return web.json_response({"error": "invalid_amount"}, status=400)
        
        try:
            link = await bot.create_invoice_link(
                title="Пополнение Stars",
                description=f"Покупка {amount} звёзд",
                payload=f"stars_{user_id}_{amount}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Stars", amount=amount)]
            )
            logger.info(f"Invoice created for user {user_id}: {amount} stars")
            return web.json_response({"link": link})
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return web.json_response({"error": "invoice_creation_failed"}, status=500)
    
    except Exception as e:
        logger.error(f"Error in api_invoice: {e}")
        return web.json_response({"error": "server_error"}, status=500)

@dp.pre_checkout_query()
async def checkout(q: types.PreCheckoutQuery):
    """Handle pre-checkout query - always approve"""
    try:
        await q.answer(ok=True)
        logger.info(f"Pre-checkout query approved for user {q.from_user.id}")
    except Exception as e:
        logger.error(f"Error in checkout: {e}")
        await q.answer(ok=False, error_message="Server error")

@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
    """Handle successful payment from Telegram"""
    try:
        payload = m.successful_payment.invoice_payload
        parts = payload.split("_")
        
        if len(parts) < 3 or parts[0] != "stars":
            logger.error(f"Invalid payload format: {payload}")
            await m.answer("❌ Ошибка при обработке платежа.")
            return
        
        user_id = int(parts[1])
        amount = int(parts[2])
        
        if user_id != m.from_user.id:
            logger.warning(f"Payment mismatch: payload={user_id}, sender={m.from_user.id}")
            await m.answer("❌ Ошибка при обработке платежа.")
            return
        
        update_balance(user_id, amount, "add", is_donation=True)
        logger.info(f"Payment successful for user {user_id}: +{amount} stars")
        await m.answer(f"✅ Спасибо за покупку! +{amount} ⭐")
        
        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"💰 **Новое пополнение!**\n👤 Юзер: {m.from_user.full_name} (`{user_id}`)\n⭐ Количество: `{amount}` звёзд", parse_mode="Markdown")
            except: pass
            
    except Exception as e:
        logger.error(f"Error in success_pay: {e}")
        await m.answer("❌ Ошибка при обработке платежа.")

# --- BROADCAST SYSTEM ---

broadcast_data = {}

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    """Admin command to start a broadcast"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("📝 Отправьте сообщение для рассылки (поддерживаются фото, Markdown и кнопки в формате `Текст - URL`).")

@dp.message(F.from_user.id.in_(ADMIN_IDS) & (F.text | F.photo | F.caption))
async def preview_broadcast(message: types.Message):
    """Show preview of the broadcast message"""
    if message.text == "/broadcast" or message.text and message.text.startswith("/"):
        return

    # Parse buttons from the end of text/caption if they exist
    content = message.text or message.caption or ""
    lines = content.split("\n")
    buttons = []
    clean_text_lines = []
    
    for line in lines:
        if " - http" in line:
            parts = line.split(" - ")
            if len(parts) >= 2:
                btn_text = parts[0].strip()
                btn_url = parts[1].strip()
                buttons.append(InlineKeyboardButton(text=btn_text, url=btn_url))
        else:
            clean_text_lines.append(line)
    
    clean_text = "\n".join(clean_text_lines).strip()
    
    kb_list = []
    if buttons:
        # Arrange buttons in rows of 2
        for i in range(0, len(buttons), 2):
            kb_list.append(buttons[i:i+2])
    
    # Control buttons
    kb_list.append([
        InlineKeyboardButton(text="✅ ОТПРАВИТЬ", callback_query_id="send_bc"), # Dummy id for structure
        InlineKeyboardButton(text="❌ ОТМЕНА", callback_query_id="cancel_bc")
    ])
    
    # We use a custom string for callback_data because InlineKeyboardButton expects it
    # But wait, aiogram 3.x uses CallbackData objects or simple strings.
    # I'll use simple strings.
    
    control_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ОТПРАВИТЬ", callback_data="bc_send"),
         InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="bc_cancel")]
    ])
    
    # Add user buttons to control kb
    if buttons:
        user_kb = []
        for i in range(0, len(buttons), 2):
            user_kb.append(buttons[i:i+2])
        full_kb = InlineKeyboardMarkup(inline_keyboard=user_kb + control_kb.inline_keyboard)
    else:
        full_kb = control_kb

    # Store message for later
    broadcast_data[message.from_user.id] = {
        "text": clean_text,
        "photo": message.photo[-1].file_id if message.photo else None,
        "kb": [[{"text": b.text, "url": b.url} for b in buttons]] if buttons else None
    }
    
    await message.answer("👀 **Предпросмотр рассылки:**", parse_mode="Markdown")
    if message.photo:
        await message.answer_photo(message.photo[-1].file_id, caption=clean_text, reply_markup=full_kb, parse_mode="Markdown")
    else:
        await message.answer(clean_text, reply_markup=full_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bc_"))
async def handle_broadcast_callback(callback: types.CallbackQuery):
    """Handle send/cancel buttons for broadcast"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    action = callback.data.split("_")[1]
    
    if action == "cancel":
        broadcast_data.pop(callback.from_user.id, None)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("❌ Рассылка отменена.")
        await callback.answer()
        return
    
    data = broadcast_data.get(callback.from_user.id)
    if not data:
        await callback.answer("❌ Данные не найдены. Попробуйте снова.")
        return
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("🚀 Рассылка запущена...")
    await callback.answer()
    
    # Build keyboard for broadcast
    kb = None
    if data["kb"]:
        buttons = []
        for row in data["kb"]:
            row_btns = [InlineKeyboardButton(text=b["text"], url=b["url"]) for b in row]
            buttons.append(row_btns)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Get all users
    with sqlite3.connect('database.db') as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    
    count = 0
    errors = 0
    for (user_id,) in users:
        try:
            if data["photo"]:
                await bot.send_photo(user_id, data["photo"], caption=data["text"], reply_markup=kb, parse_mode="Markdown")
            else:
                await bot.send_message(user_id, data["text"], reply_markup=kb, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05) # Rate limiting
        except Exception:
            errors += 1
    
    await callback.message.answer(f"✅ Рассылка завершена!\nДоставлено: `{count}`\nОшибок: `{errors}`", parse_mode="Markdown")
    broadcast_data.pop(callback.from_user.id, None)

async def main():
    """Main bot entry point"""
    init_db()
    
    # Setup aiohttp app
    app = web.Application()
    
    # Register API routes
    app.router.add_get('/api/check_sub', api_check_sub)
    app.router.add_get('/api/tasks', api_get_tasks)
    app.router.add_post('/api/tasks/verify', api_verify_task)
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/referrals', api_referrals) # Renamed to match api.js expectations later
    app.router.add_get('/api/leaderboard', api_leaderboard)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/claim_daily', api_claim_daily)
    app.router.add_post('/api/claim_promo', api_claim_promo)
    app.router.add_post('/api/create_invoice', api_invoice)
    app.router.add_post('/api/admin/create_promo', api_admin_create_promo)
    app.router.add_post('/api/ton_success', api_ton_success)
    app.router.add_post('/api/wheel/spin', api_wheel_spin)
    app.router.add_post('/api/upgrade', api_upgrade)
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Start aiohttp server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("✅ API server started on port 8080")
    
    # Start bot polling
    logger.info("✅ Bot polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())