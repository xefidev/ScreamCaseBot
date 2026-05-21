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

HYPE_TEMPLATES = [
    "@{username}, 20 секунд назад пользователь id {fake_id} выиграл Astral Shard за 20К ⭐\n\n🔥 Испытай свою удачу, твои шансы на победу в платной рулетке увеличены на 34% (всего на час)!",
    "🚨 СКИДКА ДО КРИТИЧЕСКОГО МИНИМУМА!\n\nТолько в ближайшие 30 минут стоимость открытия 'Scream Case' снижена! Успей забрать топовые подарки, пока админ спит. Шанс дропа окупаемого дропа повышен x2!",
    "🎁 Бонус выходного дня!\n\nКаждый, кто зайдет в приложение прямо сейчас, получит +2 бесплатных тикета на баланс! Не упусти халяву, заходи в профиль!",
    "🌙 Ночной режим активирован.\n\nПо статистике, именно ночью выпадает самый дорогой дроп. Прямо сейчас кто-то крутит рулетку и забирает сочные призы. А чего ждешь ты? Твой бонусный процент на удачу уже активирован!",
]

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
                         last_daily TEXT DEFAULT '1970-01-01 00:00:00',
                         total_donated_stars INTEGER DEFAULT 0,
                         total_donated_ton REAL DEFAULT 0.0,
                         total_spent INTEGER DEFAULT 0,
                         username TEXT,
                         first_name TEXT,
                         photo_url TEXT,
                         promo_opened INTEGER DEFAULT 0,
                         cases_opened_count INTEGER DEFAULT 0,
                         successful_upgrades_count INTEGER DEFAULT 0)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS payments 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, date TEXT)''')
        
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
        
        conn.execute('''CREATE TABLE IF NOT EXISTS user_achievements 
                        (user_id INTEGER, 
                         achievement_id TEXT, 
                         progress INTEGER DEFAULT 0,
                         is_claimed INTEGER DEFAULT 0,
                         PRIMARY KEY (user_id, achievement_id))''')
        
        # Миграции
        migrations = [
            "ALTER TABLE users ADD COLUMN total_donated_stars INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN total_donated_ton REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN last_daily TEXT DEFAULT '1970-01-01 00:00:00'",
            "ALTER TABLE users ADD COLUMN username TEXT",
            "ALTER TABLE users ADD COLUMN first_name TEXT",
            "ALTER TABLE users ADD COLUMN photo_url TEXT",
            "ALTER TABLE users ADD COLUMN tickets INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN referred_by INTEGER",
            "ALTER TABLE users ADD COLUMN promo_opened INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN cases_opened_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN successful_upgrades_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN total_spent INTEGER DEFAULT 0",
        ]
        
        for migration in migrations:
            try:
                conn.execute(migration)
            except:
                pass

        # Initialize tasks
        cur = conn.cursor()
        cur.execute("DELETE FROM user_tasks")
        cur.execute("DELETE FROM tasks")
        referral_tasks = [
            ("Пригласить 1 друга", 1, "referral_1", "", ""),
            ("Пригласить 2 друзей", 2, "referral_2", "", ""),
            ("Пригласить 3 друзей", 3, "referral_3", "", ""),
            ("Пригласить 4 друзей", 4, "referral_4", "", ""),
            ("Пригласить 5 друзей", 5, "referral_5", "", ""),
        ]
        cur.executemany(
            "INSERT INTO tasks (title, reward, type, url, chat_id) VALUES (?, ?, ?, ?, ?)",
            referral_tasks
        )
        conn.commit()

    print("✅ База данных полностью готова")

# --- CASE DATA (Server Side) ---
CASES_DATA = {
    1: {'min': 15, 'max': 500},   # Promo Case
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

CASES_PRICES = {
    1: 0,   # Promo Case (Free once)
    2: 1,   # Daily Case (1 Star)
    3: 667, # Snoop Case
    4: 599, # Lover's Case
    5: 199, # Hobo Case
    6: 50,  # Risky Box
    7: 111, # Scam Box
    8: 444, # Ebati Case
    9: 222, # Pussy Case
    10: 250 # Skolnik Case
}

def get_gifts_in_range(min_p, max_p):
    return [g for g in ALL_GIFTS if g['price'] >= min_p and g['price'] <= max_p]

def register_or_get(user_id, username=None, first_name=None, photo_url=None, referred_by=None):
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT stars, join_date FROM users WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        
        if res:
            update_user_profile(user_id, username, first_name, photo_url)
            return res, False
        
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
                       (user_id, stars, join_date, username, first_name, photo_url, referred_by, tickets) 
                       VALUES (?, 0, ?, ?, ?, ?, ?, 0)""", 
                     (user_id, date, username, first_name, photo_url, ref_id))
        
        if ref_id:
            cur.execute("UPDATE users SET tickets = tickets + 1 WHERE user_id = ?", (ref_id,))
            logger.info(f"User {user_id} joined via referral {ref_id}")
            
        conn.commit()
        return (0, date), True

def update_user_profile(user_id, username=None, first_name=None, photo_url=None):
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
                
                user_res = conn.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)).fetchone()
                if user_res and user_res[0]:
                    ref_id = user_res[0]
                    reward = int(amount * 0.1)
                    if reward > 0:
                        conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (reward, ref_id))
                        conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                                     (ref_id, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        logger.info(f"Referrer {ref_id} got {reward} stars from {user_id}'s donation")
        else:
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (amount, user_id))
        
        conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                     (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

# --- ОБРАБОТКА КОМАНД ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    try:
        referred_by = command.args if command.args else None
        
        data, is_new = register_or_get(
            message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            photo_url=message.from_user.photo_url if hasattr(message.from_user, 'photo_url') else None,
            referred_by=referred_by
        )
        
        if is_new:
            logger.info(f"New user registered: {message.from_user.id} - {message.from_user.full_name}")
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, 
                        f"🚀 **Новый пользователь!**\n\n👤 Имя: {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n🏷 Юзернейм: @{message.from_user.username}", 
                        parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")
            
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
            text += "• `/admin_send <текст>` — Рассылка всем пользователям\n"
            text += "• `/hype <номер_шаблона>` — Маркетинговая рассылка\n"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")
        await message.answer("❌ Ошибка при получении справки.")

@dp.message(Command("+"))
async def admin_add(message: types.Message):
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
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return
        
        with sqlite3.connect('database.db') as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_stars = conn.execute("SELECT SUM(stars) FROM users").fetchone()[0] or 0
            total_issued = conn.execute("SELECT SUM(amount) FROM payments WHERE amount > 0").fetchone()[0] or 0
            total_donated = conn.execute("SELECT SUM(total_donated_stars) FROM users").fetchone()[0] or 0
            total_ton = conn.execute("SELECT SUM(total_donated_ton) FROM users").fetchone()[0] or 0
        
        text = f"""📊 **Глобальная статистика**
👥 Всего пользователей: `{total_users}`
⭐ Звёзд в системе: `{total_stars}`
🎁 Звёзд выдано: `{total_issued}`
💎 Всего пожертвовано звёзд: `{total_donated}`
💰 Всего пожертвовано TON: `{total_ton:.4f}`"""
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await message.answer("❌ Ошибка при получении статистики.")

@dp.message(Command("admin_send"))
async def admin_send(message: types.Message, command: CommandObject):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        text_to_send = (command.args or "").strip()
        if not text_to_send:
            await message.answer("❌ Пример: `/admin_send Текст рассылки`", parse_mode="Markdown")
            return

        await message.answer("⏳ Рассылка запущена...")
        
        with sqlite3.connect('database.db') as conn:
            users = conn.execute('SELECT user_id FROM users').fetchall()
        
        sent = 0
        failed = 0
        for (uid,) in users:
            try:
                await bot.send_message(uid, text_to_send)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        
        await message.answer(f"✅ Рассылка завершена.\nДоставлено: `{sent}`\nОшибок: `{failed}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_send: {e}")
        await message.answer("❌ Ошибка при рассылке.")

@dp.message(Command("hype"))
async def admin_hype(message: types.Message, command: CommandObject):
    try:
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ Вы не администратор.")
            return

        try:
            template_number = int((command.args or "").strip())
        except ValueError:
            await message.answer("❌ Пример: `/hype 1`\nДоступные шаблоны: 1-4", parse_mode="Markdown")
            return

        if template_number < 1 or template_number > len(HYPE_TEMPLATES):
            await message.answer("❌ Доступные шаблоны: 1-4")
            return

        template_index = template_number - 1
        await message.answer(f"⏳ Hype-рассылка #{template_number} запущена...")

        template = HYPE_TEMPLATES[template_index]
        
        with sqlite3.connect('database.db') as conn:
            users = conn.execute('SELECT user_id, username, first_name FROM users').fetchall()
        
        sent = 0
        failed = 0
        for (uid, username, first_name) in users:
            try:
                clean_username = (username or first_name or "игрок").strip() or "игрок"
                text = template.format(
                    username=clean_username.lstrip("@"),
                    fake_id=random.randint(100000000, 9999999999),
                )
                await bot.send_message(uid, text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        
        await message.answer(f"✅ Hype-рассылка завершена.\nДоставлено: `{sent}`\nОшибок: `{failed}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_hype: {e}")
        await message.answer("❌ Ошибка при запуске hype-рассылки.")

async def check_membership(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id="@ScreamCase", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership for {user_id}: {e}")
        return False

# --- API ДЛЯ САЙТА ---

async def api_check_sub(request):
    try:
        uid = request.query.get("user_id")
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        is_member = await check_membership(int(uid))
        return web.json_response({"is_subscribed": is_member})
    except Exception as e:
        logger.error(f"Error in api_check_sub: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_balance(request):
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            res = conn.execute("SELECT stars, tickets, total_donated_stars, total_spent, promo_opened FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        
        if not res:
            return web.json_response({"stars": 0, "tickets": 0, "donor": 0, "spent": 0, "promo_opened": 0})
            
        return web.json_response({
            "stars": res[0], 
            "tickets": res[1],
            "donor": res[2],
            "spent": res[3],
            "promo_opened": res[4]
        })
    except ValueError:
        return web.json_response({"error": "invalid_user_id"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_balance: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_referrals(request):
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

async def api_open_case(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        case_id = data.get("case_id")
        
        if not uid or case_id is None:
            return web.json_response({"error": "invalid_data"}, status=400)
        
        case_id = int(case_id)
        uid = int(uid)
        
        # Daily Case
        if case_id == 2: 
            res = await api_claim_daily_internal(uid)
            if res.status == 200:
                case_info = CASES_DATA.get(2)
                won_item = _get_random_gift(case_info['min'], case_info['max'])
                _increment_achievement_progress(uid, 'cases_opened')
                return web.json_response({"success": True, "item": won_item, "deducted": 1})
            return res

        price = CASES_PRICES.get(case_id)
        if price is None:
            return web.json_response({"error": "invalid_case"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars, promo_opened FROM users WHERE user_id = ?", (uid,)).fetchone()
            if not user: return web.json_response({"error": "user_not_found"}, status=404)
            
            balance, promo_opened = user
            
            # Promo Case
            if case_id == 1:
                if promo_opened:
                    return web.json_response({"error": "already_opened"}, status=403)
                conn.execute("UPDATE users SET promo_opened = 1 WHERE user_id = ?", (uid,))
                price = 0

            if balance < price:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            case_info = CASES_DATA.get(case_id)
            if not case_info:
                return web.json_response({"error": "case_data_missing"}, status=500)
            
            won_item = _get_random_gift(case_info['min'], case_info['max'])

            conn.execute("UPDATE users SET stars = stars - ?, total_spent = total_spent + ?, cases_opened_count = cases_opened_count + 1 WHERE user_id = ?", (price, price, uid))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, -price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            
            _increment_achievement_progress(uid, 'cases_opened')
            
            logger.info(f"User {uid} opened case {case_id}: won {won_item['name']} ({won_item['price']}).")
        
        return web.json_response({
            "success": True, 
            "item": won_item,
            "deducted": price
        })
    except Exception as e:
        logger.error(f"Error in api_open_case: {e}")
        return web.json_response({"error": "server_error"}, status=500)

def _get_random_gift(min_p, max_p):
    drop_items = get_gifts_in_range(min_p, max_p)
    if not drop_items:
        drop_items = ALL_GIFTS[:10]
    
    cheap = [i for i in drop_items if i['price'] <= 50]
    mid = [i for i in drop_items if 50 < i['price'] <= 150]
    jackpot = [i for i in drop_items if i['price'] > 150]
    
    rand = random.random() * 100
    if rand < 85 and cheap:
        return random.choice(cheap)
    elif rand < 97 and mid:
        return random.choice(mid)
    elif jackpot:
        return random.choice(jackpot)
    else:
        return random.choice(drop_items)

def _increment_achievement_progress(user_id, achievement_type):
    mapping = {
        'cases_opened': ['first_step', 'ludoman'],
        'upgrades_successful': ['upgrade_master']
    }
    
    a_ids = mapping.get(achievement_type, [])
    with sqlite3.connect('database.db') as conn:
        for aid in a_ids:
            conn.execute("""
                INSERT INTO user_achievements (user_id, achievement_id, progress) 
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, achievement_id) DO UPDATE SET progress = progress + 1
            """, (user_id, aid))
        conn.commit()

async def api_upgrade(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        cost = int(data.get("cost", 0))
        chance = float(data.get("chance", 0))
        item_price = int(data.get("item_price", 0))
        
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars FROM users WHERE user_id = ?", (int(uid),)).fetchone()
            if not user: return web.json_response({"error": "user_not_found"}, status=404)
            
            balance = user[0]
            if balance < cost:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            success = random.random() * 100 < chance
            
            consolation = None
            if not success and item_price > 100:
                consolation_item = _get_random_gift(0, 100)
                consolation = {
                    "type": "poor_case",
                    "item": consolation_item
                }

            conn.execute("UPDATE users SET stars = stars - ?, total_spent = total_spent + ? WHERE user_id = ?", (cost, cost, int(uid)))
            if success:
                conn.execute("UPDATE users SET successful_upgrades_count = successful_upgrades_count + 1 WHERE user_id = ?", (int(uid),))
                _increment_achievement_progress(int(uid), 'upgrades_successful')

            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (int(uid), -cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            
        return web.json_response({"success": success, "consolation": consolation})
    except Exception as e:
        logger.error(f"Error in api_upgrade: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_wheel_spin(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        cost = 50
        
        SEGMENTS = [15, 50, 20, 100, 25, 200, 30, 300, 40, 500, 50, 150]
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars FROM users WHERE user_id = ?", (uid,)).fetchone()
            if not user:
                return web.json_response({"error": "user_not_found"}, status=404)
            
            balance = user[0]
            if balance < cost:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            rand = random.random() * 100
            if rand < 0.8:
                prize_index = 9
            elif rand < 15:
                prize_index = random.choice([3, 5, 7, 11])
            else:
                prize_index = random.choice([0, 1, 2, 4, 6, 8, 10])
            
            prize = SEGMENTS[prize_index]
            
            new_balance = balance - cost + prize
            conn.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (cost, uid))
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (new_balance, uid))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, -cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, prize, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
            logger.info(f"User {uid} spun wheel: won {prize}")
            
        return web.json_response({
            "success": True,
            "win_amount": prize,
            "prize_index": prize_index,
            "new_balance": new_balance
        })
    except Exception as e:
        logger.error(f"Error in api_wheel_spin: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily_internal(uid):
    try:
        uid = int(uid)
        now = datetime.now()
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", (uid,)).fetchone()
            
            if not user:
                return web.json_response({"error": "user_not_found"}, status=404)
            
            last_daily_str = user[0]
            
            if last_daily_str and last_daily_str != "1970-01-01 00:00:00":
                try:
                    last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
                    time_diff = (now - last_daily).total_seconds()
                    
                    if time_diff < 86400:
                        wait_seconds = int(86400 - time_diff)
                        logger.info(f"User {uid} attempted daily claim too soon. Wait: {wait_seconds}s")
                        return web.json_response({
                            "error": "daily_cooldown_active",
                            "wait_seconds": wait_seconds
                        }, status=403)
                except ValueError:
                    pass
            
            conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", 
                        (now.strftime("%Y-%m-%d %H:%M:%S"), uid))
            conn.commit()
            
            logger.info(f"User {uid} claimed daily case")
        
        return web.json_response({"success": True})
    
    except Exception as e:
        logger.error(f"Error in api_claim_daily_internal: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_daily(request):
    try:
        data = await request.json()
        return await api_claim_daily_internal(data.get("user_id"))
    except Exception as e:
        logger.error(f"Error in api_claim_daily: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_ton_success(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        amount_ton = data.get("amount")
        tx_hash = data.get("tx_id") or data.get("boc")
        
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
        
        tx_hash_normalized = hashlib.sha256(str(tx_hash).encode()).hexdigest()
        stars_to_add = int(amount_ton * 100)
        
        with sqlite3.connect('database.db') as conn:
            existing = conn.execute(
                "SELECT tx_id FROM ton_transactions WHERE tx_id = ?",
                (tx_hash_normalized,)
            ).fetchone()
            
            if existing:
                logger.warning(f"Duplicate TON transaction detected: {tx_hash_normalized}")
                return web.json_response({"error": "transaction_already_processed"}, status=400)
            
            conn.execute(
                "INSERT INTO ton_transactions (tx_id, user_id, amount, date) VALUES (?, ?, ?, ?)",
                (tx_hash_normalized, uid, amount_ton, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            conn.execute(
                "UPDATE users SET stars = stars + ?, total_donated_ton = total_donated_ton + ? WHERE user_id = ?",
                (stars_to_add, amount_ton, uid)
            )
            conn.execute(
                "INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)",
                (uid, stars_to_add, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            
            logger.info(f"TON payment processed: User {uid}, {amount_ton} TON = {stars_to_add} stars")
        
        try:
            await bot.send_message(uid, f"✅ Пополнение успешно! +{stars_to_add} ⭐")
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")
        
        try:
            for admin_id in ADMIN_IDS:
                await bot.send_message(admin_id, f"💰 User {uid} topped up: {amount_ton} TON = {stars_to_add} ⭐")
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
        
        return web.json_response({"success": True, "stars_added": stars_to_add})
    
    except Exception as e:
        logger.error(f"Error in api_ton_success: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_invoice(request):
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
    try:
        await q.answer(ok=True)
        logger.info(f"Pre-checkout query approved for user {q.from_user.id}")
    except Exception as e:
        logger.error(f"Error in checkout: {e}")
        await q.answer(ok=False, error_message="Server error")

@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
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
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"💰 **Новое пополнение!**\n👤 Юзер: {m.from_user.full_name} (`{user_id}`)\n⭐ Количество: `{amount}` звёзд", parse_mode="Markdown")
            except: pass
            
    except Exception as e:
        logger.error(f"Error in success_pay: {e}")
        await m.answer("❌ Ошибка при обработке платежа.")

async def api_get_achievements(request):
    try:
        uid = request.query.get("user_id")
        if not uid: return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        ACHIEVEMENTS = [
            {'id': 'first_step', 'title': 'Первый шаг', 'goal': 1, 'reward': 1},
            {'id': 'upgrade_master', 'title': 'Мастер Апгрейдов', 'goal': 3, 'reward': 15},
            {'id': 'ludoman', 'title': 'Истинный Лудоман', 'goal': 10, 'reward': 10}
        ]
        
        with sqlite3.connect('database.db') as conn:
            for a in ACHIEVEMENTS:
                conn.execute("INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?, ?)", (uid, a['id']))
            
            res = conn.execute("SELECT achievement_id, progress, is_claimed FROM user_achievements WHERE user_id = ?", (uid,)).fetchall()
            
        data = []
        for r in res:
            aid, prog, claimed = r
            info = next((a for a in ACHIEVEMENTS if a['id'] == aid), None)
            if info:
                data.append({
                    **info,
                    "progress": prog,
                    "is_claimed": bool(claimed)
                })
        
        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error in api_get_achievements: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_claim_achievement(request):
    try:
        data = await request.json()
        uid = data.get("user_id")
        aid = data.get("achievement_id")
        
        if not uid or not aid: return web.json_response({"error": "invalid_data"}, status=400)
        
        ACHIEVEMENTS = [
            {'id': 'first_step', 'title': 'Первый шаг', 'goal': 1, 'reward': 1},
            {'id': 'upgrade_master', 'title': 'Мастер Апгрейдов', 'goal': 3, 'reward': 15},
            {'id': 'ludoman', 'title': 'Истинный Лудоман', 'goal': 10, 'reward': 10}
        ]
        
        info = next((a for a in ACHIEVEMENTS if a['id'] == aid), None)
        if not info: return web.json_response({"error": "achievement_not_found"}, status=404)

        uid = int(uid)
        with sqlite3.connect('database.db') as conn:
            res = conn.execute("SELECT progress, is_claimed FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (uid, aid)).fetchone()
            if not res: return web.json_response({"error": "not_found"}, status=404)
            
            prog, claimed = res
            if claimed: return web.json_response({"error": "already_claimed"}, status=400)
            if prog < info['goal']: return web.json_response({"error": "not_reached"}, status=400)
            
            conn.execute("UPDATE user_achievements SET is_claimed = 1 WHERE user_id = ? AND achievement_id = ?", (uid, aid))
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (info['reward'], uid))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, info['reward'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
        return web.json_response({"success": True, "reward": info['reward']})
    except Exception as e:
        logger.error(f"Error in api_claim_achievement: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def main():
    init_db()
    
    app = web.Application()
    
    app.router.add_get('/api/check_sub', api_check_sub)
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/referrals', api_referrals)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/claim_daily', api_claim_daily)
    app.router.add_post('/api/create_invoice', api_invoice)
    app.router.add_post('/api/ton_success', api_ton_success)
    app.router.add_post('/api/wheel/spin', api_wheel_spin)
    app.router.add_post('/api/upgrade', api_upgrade)
    app.router.add_get('/api/achievements', api_get_achievements)
    app.router.add_post('/api/achievements/claim', api_claim_achievement)
    
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("✅ API server started on port 8080")
    
    logger.info("✅ Bot polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
