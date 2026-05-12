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

    print("✅ База данных полностью готова")

def register_or_get(user_id, username=None, first_name=None, photo_url=None, referred_by=None):
    """Register user if new, or return existing user data. Always update profile."""
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT stars, join_date FROM users WHERE user_id = ?", (user_id,))
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
                       (user_id, stars, join_date, username, first_name, photo_url, referred_by, tickets) 
                       VALUES (?, 0, ?, ?, ?, ?, ?, 0)""", 
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
            text += "• `/createpromo <код> <награда> <дни>` — Создать промокод\n"
            text += "• `/broadcast` — Рассылка сообщений\n"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")
        await message.answer("❌ Ошибка при получении справки.")

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

# --- API ДЛЯ САЙТА ---

async def api_balance(request):
    """GET /api/balance - Get user balance and tickets"""
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            res = conn.execute("SELECT stars, tickets FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        
        if not res:
            return web.json_response({"stars": 0, "tickets": 0})
            
        return web.json_response({"stars": res[0], "tickets": res[1]})
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
    Logic:
    - Cost: 50 stars
    - Server determines result based on odds
    - Rebalance: High prizes (<1% for 500+)
    """
    try:
        data = await request.json()
        uid = data.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        uid = int(uid)
        cost = 50
        
        with sqlite3.connect('database.db') as conn:
            user = conn.execute("SELECT stars FROM users WHERE user_id = ?", (uid,)).fetchone()
            if not user:
                return web.json_response({"error": "user_not_found"}, status=404)
            
            balance = user[0]
            if balance < cost:
                return web.json_response({"error": "insufficient_funds"}, status=403)
            
            # Odds Logic
            import random
            rand = random.random() * 100
            
            # Possible prize values (stars)
            # Rebalanced:
            # <1% : 500+
            # 14% : 100-300
            # 85% : 15-50
            
            if rand < 0.8: # <1%
                prize = random.choice([500, 750, 1000])
            elif rand < 15: # ~14%
                prize = random.choice([100, 150, 200, 250, 300])
            else: # ~85%
                prize = random.choice([15, 20, 25, 30, 40, 50])
            
            # Deduct cost and add prize
            new_balance = balance - cost + prize
            conn.execute("UPDATE users SET stars = ? WHERE user_id = ?", (new_balance, uid))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, -cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (uid, prize, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
            logger.info(f"User {uid} spun wheel: spent {cost}, won {prize}. New balance: {new_balance}")
            
        return web.json_response({
            "success": True,
            "win_amount": prize,
            "new_balance": new_balance
        })
    except Exception as e:
        logger.error(f"Error in api_wheel_spin: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_open_case(request):
    """
    POST /api/open_case - Open a case (paid or free)
    SECURITY:
    - Price is ALWAYS fetched from CASES_PRICES config, NEVER from client
    - Balance is checked BEFORE deducting
    - Balance is DEDUCTED IN DB before response
    - Daily case requires 24h cooldown
    - Promo case requires valid promocode
    """
    try:
        data = await request.json()
        uid = data.get("user_id")
        case_id = data.get("case_id")
        
        if not uid or case_id is None:
            return web.json_response({"error": "invalid_data"}, status=400)
        
        # Validate case_id and get price from CONFIG only
        case_id = int(case_id)
        price = CASES_PRICES.get(case_id)
        
        if price is None:
            return web.json_response({"error": "invalid_case"}, status=400)
        
        # Handle Daily and Promo cases separately
        if case_id == 2:  # Daily Case
            return await _handle_claim_daily(uid)
        
        if case_id == 1:  # Promo Case
            promo_code = data.get("code")
            if not promo_code or not isinstance(promo_code, str):
                return web.json_response({"error": "promo_code_required"}, status=400)
            return await _handle_claim_promo(uid, promo_code)
        
        # Paid cases (3-10)
        if price <= 0:
            return web.json_response({"error": "invalid_case"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            # Check balance first
            user = conn.execute("SELECT stars FROM users WHERE user_id = ?", (int(uid),)).fetchone()
            
            if not user:
                return web.json_response({"error": "user_not_found"}, status=404)
            
            user_balance = user[0]
            
            if user_balance < price:
                logger.warning(f"User {uid} attempted to open case {case_id} with insufficient funds. Balance: {user_balance}, Required: {price}")
                return web.json_response({"error": "insufficient_funds", "required": price, "current": user_balance}, status=403)
            
            # CRITICAL: Deduct balance BEFORE sending response
            conn.execute("UPDATE users SET stars = stars - ? WHERE user_id = ?", (price, uid))
            conn.execute("INSERT INTO payments (user_id, amount, date) VALUES (?, ?, ?)", 
                         (int(uid), -price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
            logger.info(f"User {uid} opened case {case_id}, deducted {price} stars")
        
        return web.json_response({"success": True, "deducted": price})
    
    except ValueError as e:
        logger.error(f"ValueError in api_open_case: {e}")
        return web.json_response({"error": "invalid_data"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_open_case: {e}")
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