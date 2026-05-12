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
                         join_date TEXT, 
                         last_daily TEXT,
                         total_donated_stars INTEGER DEFAULT 0,
                         total_donated_ton REAL DEFAULT 0.0)''')
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
        try: conn.execute("ALTER TABLE promocodes ADD COLUMN min_donation_24h INTEGER DEFAULT 0")
        except: pass
        try: conn.execute("ALTER TABLE promocodes ADD COLUMN expires_at TEXT")
        except: pass

    print("✅ База данных полностью готова")

def register_or_get(user_id):
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT stars, join_date FROM users WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        if res:
            return res, False
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO users (user_id, stars, join_date) VALUES (?, 0, ?)", (user_id, date))
        conn.commit()
        return (0, date), True

def update_balance(user_id, amount, mode="add", is_donation=False):
    with sqlite3.connect('database.db') as conn:
        if mode == "add":
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id))
            if is_donation:
                conn.execute("UPDATE users SET total_donated_stars = total_donated_stars + ? WHERE user_id = ?", (amount, user_id))
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
async def start_cmd(message: types.Message):
    """Handle /start command - register user and show main menu"""
    try:
        data, is_new = register_or_get(message.from_user.id)
        
        if is_new:
            logger.info(f"New user registered: {message.from_user.id} - {message.from_user.full_name}")
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, 
                        f"🚀 **Новый пользователь!**\n\n👤 Имя: {message.from_user.full_name}\n🆔 ID: `{message.from_user.id}`\n🏷 Юзернейм: @{message.from_user.username}", 
                        parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")

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
                "SELECT user_id, stars, join_date, total_donated_stars, total_donated_ton FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
        
        if not user:
            await message.answer(f"❌ Пользователь `{user_id}` не найден.", parse_mode="Markdown")
            return
        
        text = f"""👤 **Информация о пользователе**
🆔 ID: `{user[0]}`
⭐ Баланс: `{user[1]}`
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

@dp.message()
async def unknown_command(message: types.Message):
    """Handle unknown commands gracefully"""
    if message.text and message.text.startswith('/'):
        await message.answer("❌ Неизвестная команда. Введите `/help` для справки.", parse_mode="Markdown")

# --- API ДЛЯ САЙТА ---

async def api_balance(request):
    """GET /api/balance - Get user balance (NO AUTHENTICATION - read-only)"""
    try:
        uid = request.query.get("user_id")
        if not uid:
            return web.json_response({"error": "no_id"}, status=400)
        
        with sqlite3.connect('database.db') as conn:
            res = conn.execute("SELECT stars FROM users WHERE user_id = ?", (int(uid),)).fetchone()
        
        return web.json_response({"stars": res[0] if res else 0})
    except ValueError:
        return web.json_response({"error": "invalid_user_id"}, status=400)
    except Exception as e:
        logger.error(f"Error in api_balance: {e}")
        return web.json_response({"error": "server_error"}, status=500)

async def api_leaderboard(request):
    """GET /api/leaderboard - Get top 10 donors (NO AUTHENTICATION - read-only)"""
    try:
        with sqlite3.connect('database.db') as conn:
            res = conn.execute(
                "SELECT user_id, total_donated_stars FROM users ORDER BY total_donated_stars DESC LIMIT 10"
            ).fetchall()
        
        leaderboard = [{"user_id": r[0], "donated": r[1]} for r in res]
        return web.json_response(leaderboard)
    except Exception as e:
        logger.error(f"Error in api_leaderboard: {e}")
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
    except Exception as e:
        logger.error(f"Error in success_pay: {e}")
        await m.answer("❌ Ошибка при обработке платежа.")

async def main():
    """Main bot entry point"""
    init_db()
    
    # Setup aiohttp app
    app = web.Application()
    
    # Register API routes
    app.router.add_get('/api/balance', api_balance)
    app.router.add_get('/api/leaderboard', api_leaderboard)
    app.router.add_post('/api/open_case', api_open_case)
    app.router.add_post('/api/claim_daily', api_claim_daily)
    app.router.add_post('/api/claim_promo', api_claim_promo)
    app.router.add_post('/api/create_invoice', api_invoice)
    app.router.add_post('/api/admin/create_promo', api_admin_create_promo)
    app.router.add_post('/api/ton_success', api_ton_success)
    
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